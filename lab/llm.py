# -*- coding: utf-8 -*-
"""OpenAI API 호출 (파이썬 표준 라이브러리만 사용).

Responses API(`POST /v1/responses`)에 JSON 스키마 출력(text.format = json_schema)을 걸어
에이전트의 결정을 구조화된 JSON 으로 받는다. 도구 루프는 없다 — 질문 후보와 선택지는
코드(kb.py)가 정하고, 모델은 그 안에서 고르고 설명만 한다.

API 키는 URL 이 아니라 Authorization 헤더로 보낸다. URL 은 오류 메시지에 찍힐 수 있다.
업로드한 모델 파일은 보내지 않는다. 보내는 것은 모델에서 읽은 메타정보(입력 이름·shape·연산자 수 등)뿐이다.
"""

import json
import time
import urllib.error
import urllib.request

from . import config

BASE = "https://api.openai.com/v1"


class QuotaExceeded(Exception):
    """분당 호출 한도 또는 잔액 초과 (HTTP 429)."""


class LLMError(Exception):
    """그 밖의 API 오류. 메시지에 키를 담지 않는다."""


_STATE = {"temperature_ok": True}


def _message(detail):
    try:
        return json.loads(detail)["error"]["message"]
    except (ValueError, KeyError, TypeError):
        return detail


def _post(path, payload, timeout=90, retries=1):
    url = "%s/%s" % (BASE, path)
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json",
               "Authorization": "Bearer %s" % config.api_key()}
    last = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = _message(e.read().decode("utf-8", "replace"))[:300]
            if e.code == 429:
                raise QuotaExceeded(detail)
            if e.code in (500, 502, 503, 504) and attempt < retries:
                last = LLMError("HTTP %d" % e.code)
                time.sleep(2.0)
                continue
            raise LLMError("HTTP %d %s" % (e.code, detail))
        except (urllib.error.URLError, OSError) as e:
            if attempt < retries:
                last = LLMError("network")
                time.sleep(2.0)
                continue
            raise LLMError("network: %s" % (getattr(e, "reason", None) or e.__class__.__name__,))
    raise last or LLMError("unknown")


def call_json(system_prompt, user_text, schema_name, schema):
    """지시문 + 사용자 입력 한 건으로 호출하고, 스키마에 맞는 dict 를 돌려준다."""
    payload = {
        "model": config.GEN_MODEL,
        "instructions": system_prompt,
        "input": [{"role": "user", "content": user_text}],
        "store": False,
        "reasoning": {"effort": config.REASONING_EFFORT},
        "text": {"format": {"type": "json_schema", "name": schema_name,
                            "schema": schema, "strict": True}},
    }
    if config.REASONING_EFFORT == "none" and _STATE["temperature_ok"]:
        payload["temperature"] = config.TEMPERATURE
    try:
        data = _post("responses", payload)
    except LLMError as exc:
        if "temperature" in payload and "temperature" in str(exc):
            _STATE["temperature_ok"] = False
            payload.pop("temperature", None)
            data = _post("responses", payload)
        else:
            raise

    texts = []
    for item in data.get("output") or []:
        if item.get("type") == "message":
            for part in item.get("content") or []:
                if part.get("type") == "output_text" and part.get("text"):
                    texts.append(part["text"])
    text = "".join(texts).strip()
    if not text:
        reason = (data.get("incomplete_details") or {}).get("reason", "")
        raise LLMError("빈 응답 (%s)" % reason)
    try:
        return json.loads(text)
    except ValueError:
        raise LLMError("JSON 이 아닌 응답")
