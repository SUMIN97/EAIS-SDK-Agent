# -*- coding: utf-8 -*-
"""EAIS SDK 파라미터 에이전트 — 로컬 서버.

run.bat 이 이 파일을 실행한다. 브라우저 화면과 /api/* 를 제공한다 (표준 라이브러리만 사용).

흐름: 모델 업로드 → 에이전트가 하나씩 질문 → 사용자는 선택지를 고르거나 직접 입력 → 최종 제출 → SDK MCP 요청 출력
"""

import hashlib
import json
import os
import re
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lab import agent, config, kb, mcp_request      # noqa: E402

STATIC = os.path.join(config.ROOT, "static")
MAX_JSON = 1024 * 1024
CHUNK = 1024 * 1024
MIME = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8", ".svg": "image/svg+xml"}
SESSION_LOCKS = {}


def _lock(sid):
    return SESSION_LOCKS.setdefault(sid, threading.Lock())


def safe_name(name):
    """업로드 파일명에서 경로를 떼고 워크스페이스 이름으로 쓸 수 있는 글자만 남긴다."""
    name = os.path.basename(name.replace("\\", "/")).strip()
    name = re.sub(r"[^\w.\-]", "_", name)
    return name or "model.onnx"


def save_upload(rfile, length, name):
    """본문을 디스크로 흘려 쓰면서 sha256 을 구한다. 메모리에 통째로 올리지 않는다."""
    folder = os.path.join(config.UPLOAD_DIR, os.urandom(6).hex())
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    h = hashlib.sha256()
    left = length
    with open(path, "wb") as f:
        while left > 0:
            chunk = rfile.read(min(CHUNK, left))
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
            left -= len(chunk)
    if left:
        raise ValueError("업로드가 중간에 끊겼습니다")
    return path, h.hexdigest()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):         # 콘솔을 조용하게. 오류만 출력한다
        if args and str(args[1]).startswith(("4", "5")):
            sys.stderr.write("%s %s\n" % (self.command, fmt % args))

    def _send(self, code, body, content_type):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, payload, code=200):
        self._send(code, json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8")

    def _error(self, msg, code=400):
        self._json({"오류": msg}, code)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_JSON:
            raise ValueError("요청이 너무 큽니다")
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    # ── GET ──
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/status":
            return self._json({"llm": config.has_api_key(), "model": config.GEN_MODEL,
                               "mcp_url": config.sdk_mcp_url(), "mcp_tool": config.sdk_mcp_tool(),
                               "sdk": kb.load()["meta"]["sdk"]})
        if path == "/api/stages":                     # 업로드 전 미리보기
            return self._json({"stages": agent.preview_stages()})
        if path == "/api/tool":
            return self._json(mcp_request.tool_spec())
        if path == "/api/kb":
            data = kb.load()
            return self._json({"meta": data["meta"], "params": len(data["params"]),
                               "hints": data["hints"], "docs": kb._CACHE.get("index", [])})
        if path == "/":
            path = "/index.html"
        file = os.path.normpath(os.path.join(STATIC, path.lstrip("/")))
        if not file.startswith(STATIC) or not os.path.isfile(file):
            return self._send(404, "not found", "text/plain; charset=utf-8")
        with open(file, "rb") as f:
            self._send(200, f.read(), MIME.get(os.path.splitext(file)[1], "application/octet-stream"))

    # ── POST ──
    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        try:
            if url.path == "/api/upload":
                return self._upload(url)
            body = self._body()
            sid = body.get("sid", "")
            s = agent.get(sid)
            with _lock(sid):
                return self._route(url.path, s, body)
        except KeyError as exc:
            self._error(str(exc.args[0]) if exc.args else "잘못된 요청", 404)
        except ValueError as exc:
            self._error(str(exc))
        except Exception as exc:                # 서버는 죽지 않고 오류만 돌려준다
            self._error("처리 중 오류: %s" % exc.__class__.__name__, 500)
            raise

    def _upload(self, url):
        name = safe_name(urllib.parse.parse_qs(url.query).get("name", ["model.onnx"])[0])
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            raise ValueError("빈 파일입니다")
        if length > config.MAX_UPLOAD:
            raise ValueError("파일이 너무 큽니다 (최대 %d GB)" % (config.MAX_UPLOAD // 1024 ** 3))
        path, sha = save_upload(self.rfile, length, name)
        from lab import inspect_model
        info = inspect_model.inspect(path, name, sha)
        s = agent.create(info, path)
        with _lock(s["id"]):
            agent.next_question(s)
        self._json(agent.public(s))

    def _route(self, path, s, body):
        pid = body.get("id", "")
        if path == "/api/next":
            if not s["current"]:
                agent.next_question(s)
        elif path == "/api/answer":
            agent.answer(s, pid, body.get("choice"), body.get("custom"), body.get("note") or "")
            agent.next_question(s)
        elif path == "/api/skip":
            agent.skip(s, pid)
            agent.next_question(s)
        elif path == "/api/set":                      # 단계별 설정 표에서 값 변경
            agent.set_value(s, pid, body.get("choice"), body.get("custom"))
            if not s["current"]:
                agent.next_question(s)
        elif path == "/api/defaults":
            agent.fill_defaults(s)
        elif path == "/api/edit":
            agent.ask(s, pid)
        elif path == "/api/advanced":
            s["advanced"] = bool(body.get("on"))
            if not s["current"]:
                agent.next_question(s)
        elif path == "/api/submit":
            return self._json(mcp_request.build(s))
        else:
            return self._error("없는 경로입니다", 404)
        self._json(agent.public(s))


def main():
    try:
        kb.load()
    except (OSError, ValueError):
        print("[오류] sdk_docs/kb.json 을 읽지 못했습니다. python tools/fetch_docs.py 후 kb.json 을 확인하세요.")
        sys.exit(1)
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    if not config.has_api_key():
        print("[안내] OPENAI_API_KEY 가 없어 LLM 없이 규칙 기반으로 질문합니다. (.env.example → .env)")
    server = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
    url = "http://%s:%d/" % (config.HOST, config.PORT)
    print("EAIS SDK 에이전트: %s  (종료: Ctrl+C)" % url)
    if os.environ.get("NO_BROWSER") != "1":
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
