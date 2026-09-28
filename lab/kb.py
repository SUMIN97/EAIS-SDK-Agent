# -*- coding: utf-8 -*-
"""SDK 3.0 지식베이스(sdk_docs/kb.json) 읽기와 파라미터 목록 전개.

kb.json 의 params 는 문서에서 뽑은 '사용자가 골라야 하는 값' 목록이다.
  · per_input 항목은 모델 입력마다 하나씩 펼친다 (dbgen.{input}.order → dbgen.data.order)
  · when 조건은 [대상 id, 연산자, 값] 의 AND 목록이다. 조건이 거짓이면 묻지도, 출력하지도 않는다
  · level: basic(기본 질문) / advanced(고급 질문 켰을 때만) / auto(묻지 않고 모델·기본값으로 채움)
"""

import copy
import json
import os

from . import config

_CACHE = {}


def load():
    if "kb" not in _CACHE:
        with open(config.KB_PATH, "r", encoding="utf-8") as f:
            _CACHE["kb"] = json.load(f)
        try:
            with open(config.DOC_INDEX_PATH, "r", encoding="utf-8") as f:
                _CACHE["index"] = json.load(f)
        except (OSError, ValueError):
            _CACHE["index"] = []
    return _CACHE["kb"]


def doc_url(doc_key):
    """kb 의 doc 키(eais-user-guide 등) → 한국어 문서 페이지 URL."""
    load()
    for d in _CACHE["index"]:
        if d["lang"] == "ko" and d["slug"].endswith("/" + doc_key):
            return d["url"]
    return load()["meta"]["source"]


def _fill(obj, name, model_name):
    """문자열 안의 {input} · {model_name} 을 바꾼다 (중첩 구조 전체)."""
    if isinstance(obj, str):
        return obj.replace("{input}", name).replace("{model_name}", model_name)
    if isinstance(obj, list):
        return [_fill(x, name, model_name) for x in obj]
    if isinstance(obj, dict):
        return {k: _fill(v, name, model_name) for k, v in obj.items()}
    return obj


def expand(model):
    """모델 정보에 맞춰 파라미터 목록을 펼치고, 모델에서 알 수 있는 기본값을 채운다."""
    kb = load()
    inputs = model.get("inputs") or [{"name": "data", "shape": [], "dtype": "float32",
                                      "dynamic": True, "layout_guess": "nchw"}]
    model_name = model.get("model_name") or "model"
    out = []
    for p in kb["params"]:
        if p.get("per_input"):
            for inp in inputs:
                q = _fill(copy.deepcopy(p), inp["name"], model_name)
                q["input"] = inp["name"]
                _model_default(q, inp, model)
                out.append(q)
        else:
            q = _fill(copy.deepcopy(p), "", model_name)
            if q["id"] == "converter.skip_quantization" and model.get("quantized"):
                q["recommend"] = True
            out.append(q)
    return out


def _model_default(q, inp, model):
    key = q["key"]
    if key == "shape":
        if inp["shape"] and not inp.get("dynamic"):
            q["default"] = "(%s)" % ", ".join(str(d) for d in inp["shape"])
        else:
            # 동적 차원이 있으면 반드시 사람이 정수로 정해야 한다 → 기본 질문으로 올린다
            q["level"] = "basic"
            q["default"] = "(%s)" % ", ".join(str(d) if isinstance(d, int) and d > 0 else "1"
                                              for d in inp["shape"]) if inp["shape"] else None
            q["desc"] += " 모델 shape: %s — 동적 차원을 정수로 바꿔 주세요." % (inp["shape"] or "읽지 못함")
    elif key == "dtype":
        allowed = [o["value"] for o in q["options"]]
        if inp.get("dtype") in allowed:
            q["default"] = inp["dtype"]
        else:
            q["level"] = "basic"
    elif key == "order":
        q["recommend"] = inp.get("layout_guess") or ("nhwc" if model.get("format") == "tflite" else "nchw")
    elif key == "random":
        q["recommend"] = False                 # 문서 권장: 실제 데이터셋


# ── 조건 평가 ─────────────────────────────────────────────────────────

def value_of(pid, answers, params_by_id):
    """답이 있으면 답, 없으면 기본값. '=다른id' 기본값은 그 값을 따라간다."""
    if pid in answers:
        return answers[pid]["value"]
    p = params_by_id.get(pid)
    if not p:
        return None
    d = p.get("default")
    if isinstance(d, str) and d.startswith("="):
        return value_of(d[1:], answers, params_by_id)
    return d


def active(p, answers, params_by_id):
    for target, op, want in p.get("when") or []:
        got = value_of(target, answers, params_by_id)
        if op == "has":
            ok = isinstance(got, list) and want in got
        elif op == "==":
            ok = got == want
        elif op == "!=":
            ok = got != want
        elif op == "in":
            ok = got in want
        else:
            ok = True
        if not ok:
            return False
    return True


def candidates(params, answers, advanced):
    """아직 답하지 않았고, 조건이 맞고, 물어볼 레벨인 파라미터들 (kb 순서 유지)."""
    by_id = {p["id"]: p for p in params}
    levels = ("basic", "advanced") if advanced else ("basic",)
    return [p for p in params
            if p["id"] not in answers and p["level"] in levels and p["type"] != "secret"
            and active(p, answers, by_id)]


def resolved(params, answers):
    """조건이 맞는 모든 파라미터의 최종 값 {id: value}. 제출 직전에 쓴다."""
    by_id = {p["id"]: p for p in params}
    return {p["id"]: value_of(p["id"], answers, by_id)
            for p in params if active(p, answers, by_id)}


def hints():
    return load().get("hints") or []
