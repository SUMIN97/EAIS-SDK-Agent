# -*- coding: utf-8 -*-
"""파라미터 수집 에이전트.

한 세션 = 업로드한 모델 하나. 세션은 메모리에만 있다 (재시작하면 사라진다).

역할 나눔
  · 코드(kb.py)  : 무엇을 물을 수 있는지 — 후보 파라미터, 선택지, 조건, 기본값
  · LLM         : 후보 중 다음에 물을 것 고르기, 질문 문장, 추천값과 그 이유,
                  사용자가 '직접 입력'에 쓴 자연어를 값으로 해석
LLM 이 없거나 실패하면 kb 순서와 규칙 기반 추천으로 그대로 진행한다 (오류로 멈추지 않는다).
LLM 이 후보 밖의 id 나 선택지 밖의 값을 내면 버리고 규칙 기반 값을 쓴다.
"""

import json
import re
import threading
import time
import uuid

from . import config, kb, llm

SESSIONS = {}
LOCK = threading.Lock()


# ── 값 표현 ───────────────────────────────────────────────────────────

def key_of(value):
    """선택지 값 → 화면과 주고받는 문자열 키 (JSON)."""
    return json.dumps(value, ensure_ascii=False)


def show(value):
    if value is None:
        return "null (미적용)"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(str(v) for v in value) + "]"
    return str(value)


# ── 세션 ──────────────────────────────────────────────────────────────

def create(model, path):
    sid = uuid.uuid4().hex[:12]
    s = {"id": sid, "created": time.time(), "model": model, "path": path,
         "params": kb.expand(model), "answers": {}, "advanced": False,
         "log": [], "current": None, "llm_error": None}
    with LOCK:
        SESSIONS[sid] = s
    _say(s, "agent", _greeting(model))
    return s


def get(sid):
    s = SESSIONS.get(sid)
    if not s:
        raise KeyError("세션이 없습니다. 모델 파일을 다시 올려 주세요.")
    return s


def _say(s, role, text):
    s["log"].append({"role": role, "text": text})


def _greeting(m):
    if m.get("parse_error"):
        return ("'%s' 를 받았습니다. %s. 입력 정보는 질문으로 채우겠습니다."
                % (m["file_name"], m["parse_error"]))
    ins = ", ".join("%s %s %s" % (i["name"], i["shape"], i["dtype"]) for i in m["inputs"]) or "없음"
    return ("'%s' (%s, 연산자 %d개) 를 분석했습니다. 입력: %s. "
            "SDK 3.0 문서 기준으로 필요한 설정을 하나씩 여쭙겠습니다."
            % (m["file_name"], m["format"].upper(), m.get("op_count", 0), ins))


def params_by_id(s):
    return {p["id"]: p for p in s["params"]}


def public(s):
    """화면에 보낼 세션 요약."""
    by_id = params_by_id(s)
    answers = []
    for pid, a in s["answers"].items():
        p = by_id.get(pid, {})
        answers.append({"id": pid, "label": p.get("label", pid), "value": show(a["value"]),
                        "source": a["source"], "comment": a.get("comment", ""),
                        "note": a.get("note", "")})
    remaining = len(kb.candidates(s["params"], s["answers"], s["advanced"]))
    return {"id": s["id"], "model": s["model"], "answers": answers, "advanced": s["advanced"],
            "log": s["log"], "current": s["current"], "remaining": remaining,
            "llm": config.has_api_key(), "llm_error": s["llm_error"], "stages": stages(s)}


# ── 다음 질문 ─────────────────────────────────────────────────────────

def _model_brief(m):
    return {"file": m["file_name"], "format": m["format"], "producer": m.get("producer"),
            "opset": m.get("opset"), "inputs": m["inputs"], "outputs": m["outputs"][:8],
            "op_count": m.get("op_count"), "top_ops": dict(list(m["op_types"].items())[:25]),
            "quantized": m.get("quantized"), "findings": [f["msg"] for f in m.get("findings", [])],
            "parse_error": m.get("parse_error")}


def _cand_brief(p):
    return {"id": p["id"], "label": p["label"], "type": p["type"], "desc": p["desc"],
            "default": p.get("default"), "rule_recommend": p.get("recommend", p.get("default")),
            "options": [{"value": key_of(o["value"]), "desc": o["desc"]} for o in p["options"]],
            "doc": "%s › %s" % (p["doc"], p["section_title"])}


PICK_SYSTEM = """당신은 Exynos AI Studio(EAIS) SDK 3.0 변환 설정을 도와주는 에이전트입니다.
사용자가 올린 모델을 SDK MCP 로 변환·컴파일하기 위해 필요한 파라미터를 한 번에 하나씩 묻습니다.

규칙
- question_id 는 반드시 candidates 의 id 중 하나. 보통 candidates 순서대로 묻되, 앞의 답에 따라 더 중요한 것을 먼저 물어도 됩니다.
- question 은 한국어 1~2문장. 전문용어는 짧게 풀어 씁니다.
- recommended 는 그 후보 options 의 value 문자열을 그대로 복사합니다 (multi 타입은 여러 개 가능). options 가 비어 있으면 권장 값을 JSON 문자열로 씁니다.
- reason 은 모델 정보(입력 shape, dtype, 연산자, findings)와 문서 근거(doc, hints)를 들어 2~3문장으로 추천 이유를 설명합니다. 근거 없는 추측은 '확인 필요'라고 밝힙니다.
- option_notes 에는 이 모델에서 특히 주의할 선택지만 짧게 적습니다. 없으면 빈 배열.
- 문서에 없는 값을 지어내지 않습니다."""

PICK_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["question_id", "question", "recommended", "reason", "option_notes"],
    "properties": {
        "question_id": {"type": "string"},
        "question": {"type": "string"},
        "recommended": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
        "option_notes": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["value", "note"],
            "properties": {"value": {"type": "string"}, "note": {"type": "string"}}}},
    },
}


def _answers_brief(s):
    return {pid: a["value"] for pid, a in s["answers"].items()}


def _llm_pick(s, cands):
    if not config.has_api_key():
        return None
    user = json.dumps({"model": _model_brief(s["model"]), "answers": _answers_brief(s),
                       "candidates": [_cand_brief(p) for p in cands[:12]],
                       "hints": kb.hints()}, ensure_ascii=False)
    try:
        out = llm.call_json(PICK_SYSTEM, user, "next_question", PICK_SCHEMA)
        s["llm_error"] = None
        return out
    except (llm.LLMError, llm.QuotaExceeded, RuntimeError) as exc:
        s["llm_error"] = "LLM 호출 실패 — 규칙 기반으로 진행합니다 (%s)" % str(exc)[:160]
        return None


def _question(p, pick=None):
    """파라미터 + (선택) LLM 결과 → 화면용 질문."""
    keys = [key_of(o["value"]) for o in p["options"]]
    rule = p.get("recommend", p.get("default"))
    rec = [key_of(v) for v in rule] if p["type"] == "multi" and isinstance(rule, list) else [key_of(rule)]
    reason = "문서 기본값/권장값입니다."
    text = "%s 을(를) 정해 주세요." % p["label"]
    notes = {}
    source = "rule"
    extra = []
    if pick:
        source = "llm"
        text = pick.get("question") or text
        reason = pick.get("reason") or reason
        notes = {n["value"]: n["note"] for n in pick.get("option_notes") or [] if n.get("value") in keys}
        got = [r for r in pick.get("recommended") or [] if r in keys]
        if not keys and pick.get("recommended"):
            got = pick["recommended"][:1]
            extra = got                      # 선택지가 없는 항목은 LLM 제안을 선택지로 보여 준다
        if got:
            rec = got
    options = [{"key": k, "label": show(o["value"]), "desc": o["desc"], "note": notes.get(k, ""),
                "recommended": k in rec} for k, o in zip(keys, p["options"])]
    for k in extra:
        try:
            v = json.loads(k)
        except ValueError:
            v, k = k, key_of(k)
        options.append({"key": k, "label": show(v), "desc": "에이전트 제안", "note": "", "recommended": True})
    if not options and p.get("default") is not None:
        options.append({"key": key_of(p["default"]), "label": show(p["default"]), "desc": "기본값",
                        "note": "", "recommended": True})
    return {"id": p["id"], "label": p["label"], "type": p["type"], "question": text,
            "options": options, "reason": reason, "desc": p["desc"],
            "default": show(p.get("default")), "multi": p["type"] == "multi",
            "doc": {"title": kb.load()["meta"]["docs"].get(p["doc"], p["doc"]),
                    "section": p["section_title"], "url": kb.doc_url(p["doc"])},
            "placeholder": _placeholder(p), "source": source}


def _placeholder(p):
    return {"bool": "예) 예 / 아니오, GPU 없어요",
            "int": "정수", "float": "숫자",
            "list": "예) [0.485, 0.456, 0.406] 또는 0.5",
            "shape": "예) (1, 3, 224, 224)",
            "multi": "예) conversion, compile — 또는 원하는 것을 문장으로",
            "enum": "목록에 없으면 값이나 원하는 바를 문장으로 적어 주세요",
            }.get(p["type"], "값을 직접 입력")


def next_question(s):
    cands = kb.candidates(s["params"], s["answers"], s["advanced"])
    if not cands:
        s["current"] = None
        return None
    pick = _llm_pick(s, cands)
    by_id = {p["id"]: p for p in cands}
    p = by_id.get((pick or {}).get("question_id")) or cands[0]
    if pick and pick.get("question_id") not in by_id:
        pick = None                          # 후보 밖 id → LLM 결과 전체를 버린다
    q = _question(p, pick)
    s["current"] = q
    _say(s, "agent", q["question"])
    return q


def ask(s, pid):
    """요약에서 [수정] 을 누른 항목을 바로 다시 묻는다."""
    s["answers"].pop(pid, None)
    p = params_by_id(s).get(pid)
    if not p:
        raise KeyError("알 수 없는 항목: %s" % pid)
    q = _question(p, None)
    q["question"] = "%s 을(를) 다시 정해 주세요." % p["label"]
    s["current"] = q
    return q


# ── 답 기록 ───────────────────────────────────────────────────────────

INTERPRET_SYSTEM = """사용자가 EAIS SDK 파라미터 질문에 선택지 대신 직접 입력한 문장을 값으로 바꿉니다.
- 선택지 중 뜻이 맞는 것이 있으면 matched=true, value 에 그 선택지 value 문자열을 그대로 씁니다 (multi 는 JSON 배열 문자열).
- 선택지로 옮길 수 없고 사용자가 구체적인 값을 적었다면 matched=false, value 에 그 값을 JSON 문자열로 씁니다.
- comment 는 한국어 한두 문장: 어떻게 해석했는지, 문서상 주의점. 문서에 없는 값이면 그렇다고 알립니다."""

INTERPRET_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["matched", "value", "comment"],
    "properties": {"matched": {"type": "boolean"}, "value": {"type": "string"},
                   "comment": {"type": "string"}},
}

_TRUE = {"true", "yes", "y", "1", "예", "네", "응", "사용", "켜기", "on"}
_FALSE = {"false", "no", "n", "0", "아니오", "아니요", "아니", "미사용", "끄기", "off"}


def _numbers(text):
    return [float(x) if "." in x or "e" in x.lower() else int(x)
            for x in re.findall(r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?", text)]


def _parse_direct(p, text):
    """형식이 분명한 입력은 LLM 없이 바로 값으로. 못 하면 (None, False)."""
    t = text.strip()
    low = t.lower()
    opts = [o["value"] for o in p["options"]]
    typ = p["type"]
    if typ == "bool":
        if low in _TRUE:
            return True, True
        if low in _FALSE:
            return False, True
    elif typ in ("int", "float"):
        nums = _numbers(t)
        if len(nums) == 1 and re.fullmatch(r"[-\d.eE+\s]+", t):
            return (int(nums[0]) if typ == "int" else float(nums[0])), True
    elif typ == "list":
        if re.fullmatch(r"[\[\(]?\s*-?[\d.eE\-+,\s]+[\]\)]?", t):
            nums = _numbers(t)
            if nums:
                return nums, True
    elif typ == "shape":
        nums = _numbers(t)
        if nums and all(isinstance(n, int) and n > 0 for n in nums) and \
                re.fullmatch(r"[\[\(]?\s*[\d\s,x×*]+[\]\)]?", t):
            return "(%s)" % ", ".join(str(n) for n in nums), True
    elif typ == "enum":
        for v in opts:
            if v is not None and str(v).lower() == low:
                return v, True
        if low in ("null", "none", "없음") and None in opts:
            return None, True
    elif typ == "multi":
        parts = [x.strip() for x in re.split(r"[,\s]+", t) if x.strip()]
        lookup = {str(v).lower(): v for v in opts}
        if parts and all(x.lower() in lookup for x in parts):
            return [lookup[x.lower()] for x in parts], True
    elif typ == "str":
        return t, True
    return None, False


def _interpret(s, p, text):
    """자연어 입력 → (값, 문서 선택지와 맞았는지, 설명)."""
    if config.has_api_key():
        user = json.dumps({"parameter": _cand_brief(p), "user_text": text,
                           "model": _model_brief(s["model"])}, ensure_ascii=False)
        try:
            out = llm.call_json(INTERPRET_SYSTEM, user, "interpret", INTERPRET_SCHEMA)
            try:
                value = json.loads(out["value"])
            except ValueError:
                value = out["value"]
            return value, bool(out["matched"]), out.get("comment", "")
        except (llm.LLMError, llm.QuotaExceeded, RuntimeError) as exc:
            s["llm_error"] = "입력 해석 실패 — 적은 그대로 씁니다 (%s)" % str(exc)[:160]
    return text.strip(), False, "적은 값을 그대로 사용합니다."


CLOSED_TYPES = ("enum", "bool", "multi")     # 문서가 허용값을 정해 둔 타입


def _custom_source(p, value):
    """직접 입력한 값의 출처 구분.
    custom→option : 적은 것이 문서 선택지와 같다
    input         : 경로·shape·숫자처럼 원래 자유 입력인 항목
    custom        : 허용값이 정해진 항목인데 문서 선택지 밖의 값 → 점검 결과에 경고
    """
    if p["type"] not in CLOSED_TYPES:
        return "input"
    known = [o["value"] for o in p["options"]] or ([True, False] if p["type"] == "bool" else [])
    if p["type"] == "multi":
        ok = isinstance(value, list) and all(v in known for v in value)
    else:
        ok = value in known
    return "custom→option" if ok else "custom"


def answer(s, pid, choice=None, custom=None, note=""):
    p = params_by_id(s).get(pid)
    if not p:
        raise KeyError("알 수 없는 항목: %s" % pid)
    keys = {key_of(o["value"]): o["value"] for o in p["options"]}
    cur = s.get("current") or {}
    for o in cur.get("options", []) if cur.get("id") == pid else []:
        keys.setdefault(o["key"], json.loads(o["key"]))     # 에이전트 제안 선택지 포함
    comment, source = "", "option"

    if custom and custom.strip():
        value, ok = _parse_direct(p, custom)
        if not ok:
            value, _, comment = _interpret(s, p, custom)
        source = _custom_source(p, value)
        if source == "custom" and not comment:
            comment = "문서 선택지에 없는 값입니다. SDK 에서 거부될 수 있습니다."
        shown = custom.strip()
    else:
        if p["type"] == "multi":
            choices = choice if isinstance(choice, list) else [choice]
            value = [keys[c] for c in choices if c in keys]
            if not value:
                raise ValueError("하나 이상 선택해 주세요.")
        else:
            if choice not in keys:
                raise ValueError("선택지를 고르거나 직접 입력해 주세요.")
            value = keys[choice]
        shown = show(value)

    if p["type"] == "shape" and not re.fullmatch(r"\(\d+(, \d+)*\)", str(value)):
        comment = (comment + " " if comment else "") + "shape 는 (1, 3, 224, 224) 처럼 양의 정수여야 합니다."
    s["answers"][pid] = {"value": value, "source": source, "note": note.strip(),
                         "comment": comment, "custom_text": custom.strip() if custom else ""}
    _say(s, "user", "%s → %s%s" % (p["label"], shown, (" (메모: %s)" % note.strip()) if note.strip() else ""))
    if comment:
        _say(s, "agent", comment)
    _clear_current(s, pid)


def _clear_current(s, pid):
    """단계별 설정 표에서 다른 항목을 바꿔도 진행 중인 질문은 그대로 둔다."""
    if (s.get("current") or {}).get("id") == pid:
        s["current"] = None


def skip(s, pid):
    """기본값으로 넘어간다."""
    p = params_by_id(s).get(pid)
    if not p:
        raise KeyError("알 수 없는 항목: %s" % pid)
    value = kb.value_of(pid, {}, params_by_id(s))
    s["answers"][pid] = {"value": value, "source": "default", "note": "", "comment": ""}
    _say(s, "user", "%s → 기본값 (%s)" % (p["label"], show(value)))
    _clear_current(s, pid)


def fill_defaults(s):
    """남은 질문을 모두 기본값(또는 규칙 추천값)으로 채운다. 고급 항목은 답하지 않은 채 두어 기본값이 쓰인다."""
    n = 0
    while True:
        cands = kb.candidates(s["params"], s["answers"], s["advanced"])
        if not cands:
            break
        p = cands[0]
        # 모델에서 읽어 낸 추천(order, skip_quantization)만 기본값보다 앞세운다.
        # random 의 추천(False)을 따르면 있지도 않은 ./dataset 을 가리키게 되므로 기본값(True)을 쓴다
        if p["key"] in ("order", "skip_quantization") and "recommend" in p:
            value = p["recommend"]
        else:
            value = kb.value_of(p["id"], {}, params_by_id(s))
        s["answers"][p["id"]] = {"value": value, "source": "default", "note": "", "comment": ""}
        n += 1
    s["current"] = None
    _say(s, "agent", "남은 %d개 항목을 기본값/권장값으로 채웠습니다. 요약을 확인하고 최종 제출하세요." % n)


# ── 단계별 설정 표 ─────────────────────────────────────────────────────

FILE_LABEL = {"model_yaml": "{model}.yaml", "dbgen_spec": "Config/DATA/dbgen_spec.yaml",
              "compiler_tuning": "Config/compiler_tuning_mode_config.yaml",
              "profiler_advanced": "Config/profiler_advanced_config.yaml",
              "debug_yaml": "Config/debug.yaml", "pipeline": "CLI 옵션"}
OP_TEXT = {"==": "=", "!=": "≠", "has": "포함", "in": "∈"}


def _yaml_key(p):
    if p["file"] == "model_yaml":
        return "%s.%s" % (p["section"], p["key"])
    if p["file"] == "dbgen_spec":
        return "%s.%s" % (p["input"], p["key"])
    if p["id"] == "conversion.stage":
        return "--eht / --elt"
    if p["id"] == "workspace.path":
        return "--w"
    return p["key"]


def _condition_text(p, by_id):
    parts = []
    for target, op, want in p.get("when") or []:
        if target == "pipeline.steps":
            continue                                  # 단계 자체가 조건이므로 표에서는 생략
        label = by_id.get(target, {}).get("label", target)
        parts.append("%s %s %s" % (label, OP_TEXT.get(op, op), show(want)))
    return " 이고 ".join(parts)


def _stage_of(p, stages):
    for st in stages:
        if any(p["id"].startswith(pre) for pre in st["prefixes"]):
            return st["id"]
    return None


def stages(s):
    """문서 권장 순서의 실행 단계와, 단계마다 설정할 파라미터 행."""
    meta = kb.load().get("stages") or []
    by_id = params_by_id(s)
    steps = kb.value_of("pipeline.steps", s["answers"], by_id) or []
    model = s["model"]["model_name"]
    rows = {st["id"]: [] for st in meta}
    for p in s["params"]:
        sid = _stage_of(p, meta)
        if not sid:
            continue
        value = kb.value_of(p["id"], s["answers"], by_id)
        default = kb.value_of(p["id"], {}, by_id)
        opts = [{"key": key_of(o["value"]), "label": show(o["value"]), "desc": o["desc"]} for o in p["options"]]
        if p["type"] == "bool" and not opts:
            opts = [{"key": "true", "label": "true", "desc": ""}, {"key": "false", "label": "false", "desc": ""}]
        a = s["answers"].get(p["id"])
        rows[sid].append({
            "id": p["id"], "label": p["label"], "key": _yaml_key(p),
            "file": FILE_LABEL[p["file"]].replace("{model}", model),
            "type": p["type"], "level": p["level"], "desc": p["desc"],
            "value_key": key_of(value), "value": show(value),
            "values": [key_of(v) for v in value] if isinstance(value, list) and p["type"] == "multi" else None,
            "default": show(default), "default_key": key_of(default),
            "source": a["source"] if a else "default",
            "active": kb.active(p, s["answers"], by_id),
            "condition": _condition_text(p, by_id),
            "options": opts, "editable": p["type"] != "secret",
            "doc": {"url": kb.doc_url(p["doc"]), "section": p["section_title"]},
        })
    out = []
    for st in meta:
        r = rows[st["id"]]
        out.append(dict({k: st[k] for k in ("id", "title", "cmd", "need", "desc", "outputs", "section_title")},
                        doc_url=kb.doc_url(st["doc"]), enabled=st["id"] in steps, params=r,
                        active_count=sum(1 for x in r if x["active"]),
                        changed=sum(1 for x in r if x["active"] and x["source"] not in ("default",))))
    return out


def set_value(s, pid, choice=None, custom=None):
    """단계별 설정 표에서 값을 바꾼다. choice == '__default__' 면 기본값으로 되돌린다."""
    if choice == "__default__":
        skip(s, pid)                          # 답을 지우면 에이전트가 다시 묻는다. 기본값을 '정한 값'으로 기록한다
    else:
        answer(s, pid, choice, custom)
    cur = s.get("current")
    if cur and cur["id"] not in {p["id"] for p in kb.candidates(s["params"], s["answers"], s["advanced"])}:
        s["current"] = None                   # 표에서 답했거나 조건이 바뀌어 더는 물을 필요 없는 질문


def preview_stages():
    """모델을 올리기 전에 보여 줄 단계별 파라미터 (문서 기본값, 입력 이름은 <input>)."""
    model = {"model_name": "<model_name>", "format": "onnx", "quantized": False,
             "inputs": [{"name": "<input>", "shape": ["N", "C", "H", "W"], "dtype": "float32",
                         "dynamic": False, "layout_guess": "nchw"}]}
    params = kb.expand(model)
    for p in params:                               # 업로드 전에는 모델에서 읽은 값이 없다
        if p.get("input") and p["key"] == "shape":
            p["default"], p["level"] = "(모델에서 읽음)", "auto"
    return stages({"params": params, "answers": {}, "model": model})
