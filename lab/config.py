# -*- coding: utf-8 -*-
"""앱 전역 설정과 경로.

.env 에서 OPENAI_API_KEY 를 읽는다. 키 값은 화면·로그·오류 메시지 어디에도 쓰지 않는다.
"""

import os

# ── 경로 ──────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DOCS_DIR = os.path.join(ROOT, "sdk_docs")
KB_PATH = os.path.join(DOCS_DIR, "kb.json")
DOC_INDEX_PATH = os.path.join(DOCS_DIR, "index.json")
RAW_DOCS_DIR = os.path.join(DOCS_DIR, "raw")
UPLOAD_DIR = os.path.join(ROOT, "uploads")      # 업로드한 모델 파일. 이 PC 밖으로 나가지 않는다

# ── OpenAI ────────────────────────────────────────────────────────────
GEN_MODEL = "gpt-5.6-luna"
REASONING_EFFORT = "none"
TEMPERATURE = 0.0

# ── 서버 ──────────────────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 8780                              # rag-lab(8765/8766) · agents-lab(8770~8772) 과 겹치지 않게
MAX_UPLOAD = 4 * 1024 * 1024 * 1024      # 4 GB. 디스크로 바로 흘려 쓰므로 메모리는 쓰지 않는다

# ── SDK MCP ───────────────────────────────────────────────────────────
# 실제 SDK MCP 서버 주소·도구 이름을 받으면 .env 에서 바꾼다. 요청 본문을 만드는 데만 쓰고,
# 이 앱이 직접 보내지는 않는다.
DEFAULT_SDK_MCP_URL = "http://127.0.0.1:8790/mcp"
DEFAULT_SDK_MCP_TOOL = "eais_run_pipeline"


def load_env():
    """앱 폴더의 .env 를 읽어 os.environ 에 넣는다 (이미 있는 값은 유지)."""
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def api_key():
    """OPENAI_API_KEY 를 반환한다. 없으면 예외. 값은 절대 밖으로 내보내지 않는다."""
    load_env()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key or "여기에" in key:
        raise RuntimeError("NO_API_KEY")
    return key


def has_api_key():
    try:
        api_key()
        return True
    except RuntimeError:
        return False


def sdk_mcp_url():
    load_env()
    return os.environ.get("SDK_MCP_URL", "").strip() or DEFAULT_SDK_MCP_URL


def sdk_mcp_tool():
    load_env()
    return os.environ.get("SDK_MCP_TOOL", "").strip() or DEFAULT_SDK_MCP_TOOL
