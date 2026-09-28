# -*- coding: utf-8 -*-
"""수집한 답 → SDK MCP 요청.

최종 제출 시 만드는 것
  · request  : MCP JSON-RPC `tools/call` 본문 (Streamable HTTP 로 SDK MCP 에 보낼 것)
  · curl     : initialize → notifications/initialized → tools/call 순서의 예시 명령
  · files    : SDK 워크스페이스에 들어갈 yaml 들 (<model>.yaml, Config/DATA/dbgen_spec.yaml …)
  · cli      : 같은 작업을 eais CLI 로 직접 할 때의 명령 순서
  · warnings : 문서 규칙으로 미리 걸러 낸 문제
이 앱은 요청을 만들어 보여 주기만 하고 보내지 않는다.
비밀번호 같은 비밀값은 ${VAR} 자리표시자로만 넣는다.
"""

import json
import os
import posixpath
import re

from . import agent, config, kb

DBGEN_ORDER = ["random", "path", "ext", "shape", "order", "dtype", "mean", "scale"]
SECTION_ORDER = ["general", "database_gen", "converter", "compiler", "profiler"]
FILE_PATHS = {"dbgen_spec": "Config/DATA/dbgen_spec.yaml",
              "compiler_tuning": "Config/compiler_tuning_mode_config.yaml",
              "profiler_advanced": "Config/profiler_advanced_config.yaml",
              "debug_yaml": "Config/debug.yaml"}
PROTOCOL_VERSION = "2025-06-18"


def tool_spec():
    """SDK MCP 쪽에 있어야 할 도구 정의 (tools/list 형식). 요청 arguments 가 이 스키마를 따른다."""
    obj = {"type": "object"}
    return {
        "name": config.sdk_mcp_tool(),
        "description": "EAIS SDK 3.0 파이프라인(init → generation → conversion → debug → compile → profiling)을 "
                       "주어진 모델과 설정으로 실행한다. model_yaml 은 <model_name>.yaml 의 섹션, "
                       "config_files 는 워크스페이스 기준 경로별 yaml 내용이다.",
        "inputSchema": {
            "type": "object",
            "required": ["model", "workspace", "steps", "model_yaml"],
            "properties": {
                "model": {"type": "object", "required": ["file_name", "format", "sha256"], "properties": {
                    "file_name": {"type": "string"}, "format": {"type": "string", "enum": ["onnx", "tflite"]},
                    "size_bytes": {"type": "integer"}, "sha256": {"type": "string"},
                    "uri": {"type": "string", "description": "SDK 가 모델 파일을 가져갈 위치"}}},
                "workspace": {"type": "string", "description": "폴더명 = 모델 파일명(확장자 제외)"},
                "steps": {"type": "array", "items": {"type": "string", "enum": [
                    "init", "generation", "conversion", "debug", "compile", "profiling"]}},
                "conversion_options": {"type": "object", "properties": {
                    "stage": {"type": "string", "enum": ["full", "eht", "elt"]}}},
                "model_yaml": dict(obj, description="general / database_gen / converter / compiler / profiler"),
                "config_files": dict(obj, description="{'Config/DATA/dbgen_spec.yaml': {...}, ...}"),
                "custom_values": {"type": "array", "description": "문서 선택지 밖에서 사용자가 직접 입력한 값"},
                "user_notes": {"type": "array"},
            },
        },
    }


# ── yaml ──────────────────────────────────────────────────────────────

def _scalar(v, py_bool=False):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return ("True" if v else "False") if py_bool else ("true" if v else "false")
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, list):
        return "[" + ", ".join(_scalar(x, py_bool) for x in v) + "]"
    s = str(v)
    if re.fullmatch(r"\([\d, ]+\)", s):                      # dbgen shape 는 문서처럼 괄호 그대로
        return s
    if s == "" or re.search(r"[:#{}\[\]&*!|>'\"%@`$]", s) or s[0] in "-?" or s.strip() != s:
        return "'" + s.replace("'", "''") + "'"
    return s


def dump_yaml(d, py_bool=False, indent=0):
    lines = []
    pad = " " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            lines.append("%s%s:" % (pad, k))
            lines.append(dump_yaml(v, py_bool, indent + 2))
        else:
            lines.append("%s%s: %s" % (pad, k, _scalar(v, py_bool)))
    return "\n".join(x for x in lines if x != "")


# ── 조립 ──────────────────────────────────────────────────────────────

def _collect(s):
    params = s["params"]
    values = kb.resolved(params, s["answers"])
    by_id = {p["id"]: p for p in params}
    model_yaml, dbgen, files, pipeline = {}, {}, {}, {}
    for pid, v in values.items():
        p = by_id[pid]
        f = p["file"]
        if f == "model_yaml":
            model_yaml.setdefault(p["section"], {})[p["key"]] = v
        elif f == "dbgen_spec":
            dbgen.setdefault(p["input"], {})[p["key"]] = v
        elif f == "pipeline":
            pipeline[p["key"]] = v
        else:
            files.setdefault(f, {})[p["key"]] = v
    if "generation" in pipeline.get("steps", []) or dbgen:
        model_yaml["database_gen"] = {"database_spec": FILE_PATHS["dbgen_spec"]}
    model_yaml = {k: model_yaml[k] for k in SECTION_ORDER if k in model_yaml}
    for name, entry in dbgen.items():
        if entry.get("random") is True:          # 랜덤이면 path/ext/mean/scale 은 문서 예시처럼 뺀다
            for k in ("path", "ext"):
                entry.pop(k, None)
        dbgen[name] = {k: entry[k] for k in DBGEN_ORDER if k in entry}
    if dbgen:
        files["dbgen_spec"] = dbgen
    return values, model_yaml, files, pipeline


def _warnings(s, values, pipeline, files):
    m = s["model"]
    w = [{"level": f["level"], "msg": f["msg"]} for f in m.get("findings", []) if f["level"] in ("warn", "error")]
    steps = pipeline.get("steps") or []
    ws = pipeline.get("workspace") or ""
    if posixpath.basename(ws.rstrip("/")) != m["model_name"]:
        w.append({"level": "error", "msg": "워크스페이스 폴더명(%s)이 모델 파일명(%s)과 다릅니다 — Error code 102"
                  % (posixpath.basename(ws.rstrip("/")), m["model_name"])})
    if "conversion" in steps and "generation" not in steps and values.get("converter.skip_quantization") is not True:
        w.append({"level": "warn", "msg": "generation 없이 conversion 을 실행합니다 — Config/DATA 에 npy 캘리브레이션 데이터가 이미 있어야 합니다"})
    if "compile" in steps and "conversion" not in steps:
        w.append({"level": "warn", "msg": "conversion 없이 compile 합니다 — Converter_result/HW_*.snc 가 이미 있어야 합니다"})
    if "profiling" in steps and "compile" not in steps:
        w.append({"level": "warn", "msg": "compile 없이 profiling 합니다 — Compiler_result 가 이미 있어야 합니다"})
    if "profiling" in steps and values.get("profiler.device_id") in (None, "", "NOT_USE"):
        w.append({"level": "warn", "msg": "profiling 에 기기 ID 가 NOT_USE 입니다 — adb devices 로 확인한 ID 가 필요합니다"})
    if pipeline.get("conversion_stage") == "elt":
        w.append({"level": "warn", "msg": "--elt 는 기존 EHT 결과(Converter_result/0_·1_·2_)가 있어야 합니다"})
    if values.get("profiler_adv.core_num") == "multiple" and values.get("compiler.mode") not in ("multicore", "tuning_mode"):
        w.append({"level": "warn", "msg": "profiling core_num=multiple 인데 compiler.mode 가 multicore 가 아닙니다"})
    for name, entry in (files.get("dbgen_spec") or {}).items():
        if entry.get("random") is True:
            w.append({"level": "info", "msg": "[%s] 랜덤 캘리브레이션 데이터 — 빠른 테스트용이며 변환 품질이 떨어질 수 있습니다" % name})
        if not re.fullmatch(r"\(\d+(, \d+)*\)", str(entry.get("shape") or "")):
            w.append({"level": "error", "msg": "[%s] shape 가 양의 정수 튜플이 아닙니다: %s" % (name, entry.get("shape"))})
    for pid, a in s["answers"].items():
        if a["source"] == "custom":
            w.append({"level": "warn", "msg": "%s: 문서 선택지에 없는 값 '%s' 을(를) 그대로 보냅니다" % (pid, agent.show(a["value"]))})
    return w


def build(s):
    values, model_yaml, files, pipeline = _collect(s)
    m = s["model"]
    steps = pipeline.get("steps") or []
    ws = pipeline.get("workspace") or "/home/user/eais-projects/%s" % m["model_name"]
    ext = os.path.splitext(m["file_name"])[1]

    config_files = {FILE_PATHS[k]: v for k, v in files.items()}
    custom = [{"param": pid, "value": a["value"], "text": a.get("custom_text", "")}
              for pid, a in s["answers"].items() if a["source"] == "custom"]
    notes = [{"param": pid, "note": a["note"]} for pid, a in s["answers"].items() if a.get("note")]
    arguments = {
        "model": {"file_name": m["file_name"], "format": m["format"], "size_bytes": m["size_bytes"],
                  "sha256": m["sha256"], "uri": "file:///" + s["path"].replace("\\", "/").lstrip("/")},
        "workspace": ws,
        "steps": steps,
        "conversion_options": {"stage": pipeline.get("conversion_stage", "full")},
        "model_yaml": model_yaml,
        "config_files": config_files,
    }
    if custom:
        arguments["custom_values"] = custom
    if notes:
        arguments["user_notes"] = notes
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": config.sdk_mcp_tool(), "arguments": arguments}}

    yaml_files = {"%s.yaml" % m["model_name"]: dump_yaml(model_yaml) + "\n"}
    for key, body in files.items():
        yaml_files[FILE_PATHS[key]] = dump_yaml(body, py_bool=(key == "dbgen_spec")) + "\n"

    cli = ["mkdir -p %s && cp %s %s/%s%s" % (ws, m["file_name"], ws, m["model_name"], ext)]
    stage = pipeline.get("conversion_stage", "full")
    for step in steps:
        cmd = "eais %s --w %s" % (step, ws)
        if step == "conversion" and stage in ("eht", "elt"):
            cmd += " --" + stage
        if step == "debug":
            cmd += " --mode %s" % values.get("debug.mode", "accuracy")
        cli.append(cmd)
        if step == "init":
            cli.append("# 위 yaml 파일들로 %s.yaml 과 Config/ 아래 파일을 덮어씁니다" % m["model_name"])

    return {"request": request, "http": _http(request), "files": yaml_files, "cli": cli,
            "warnings": _warnings(s, values, pipeline, files), "tool_spec": tool_spec()}


def _http(request):
    url = config.sdk_mcp_url()
    hdr = ('-H "Content-Type: application/json" '
           '-H "Accept: application/json, text/event-stream"')
    init = {"jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                       "clientInfo": {"name": "eais-sdk-agent", "version": "1.0"}}}
    curl = "\n".join([
        "# 0) 아래 [MCP 요청] 본문을 request.json 으로 저장합니다",
        "# 1) 세션 초기화 — 응답 헤더의 Mcp-Session-Id 를 확인합니다",
        "curl -si -X POST %s %s \\\n  -d '%s'" % (url, hdr, json.dumps(init, ensure_ascii=False)),
        "",
        "# 2) 초기화 완료 알림",
        "curl -s -X POST %s %s \\\n  -H \"Mcp-Session-Id: <세션ID>\" -H \"MCP-Protocol-Version: %s\" \\\n"
        "  -d '{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}'" % (url, hdr, PROTOCOL_VERSION),
        "",
        "# 3) 도구 호출 (%s)" % request["params"]["name"],
        "curl -s -X POST %s %s \\\n  -H \"Mcp-Session-Id: <세션ID>\" -H \"MCP-Protocol-Version: %s\" \\\n"
        "  --data-binary @request.json" % (url, hdr, PROTOCOL_VERSION),
    ])
    return {"url": url, "method": "POST", "headers": {
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
        "Mcp-Session-Id": "<initialize 응답에서 받은 값>", "MCP-Protocol-Version": PROTOCOL_VERSION},
        "curl": curl}
