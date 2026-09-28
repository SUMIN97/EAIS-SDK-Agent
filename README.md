# EAIS SDK 에이전트

모델 파일(.onnx / .tflite)을 올리면 에이전트가 **Exynos AI Studio SDK 3.0 문서**를 근거로
변환·컴파일·프로파일링에 필요한 파라미터를 하나씩 묻고, 최종 제출 시 **SDK MCP 로 보낼 요청**을 만들어 보여 줍니다.
SDK 를 직접 쓸 수 없는 환경에서 "무엇을 어떤 값으로 요청할지"를 정리하는 도구입니다. **요청을 실제로 보내지는 않습니다.**

```
run.bat                 # 또는: set PYTHONUTF8=1 && python app.py
→ http://127.0.0.1:8780/
```

- 표준 라이브러리만 사용 (pip 설치 없음). `onnx`/`tflite` 패키지 없이 모델 파일을 직접 읽습니다.
- `.env` 에 `OPENAI_API_KEY` 가 있으면 LLM(`gpt-5.6-luna`)이 질문 순서·추천값·추천 이유를 정하고 자연어 입력을 해석합니다.
  키가 없거나 호출이 실패하면 문서 기본값과 규칙으로 계속 진행합니다.

## 화면 흐름

1. **모델 파일** — 끌어 놓기/클릭 업로드. 입력·출력 shape/dtype, opset, 연산자 분포, 양자화 여부를 보여 주고
   SDK 3.0 ModelValidator 규칙으로 미리 점검합니다 (opset 13–21, 동적 차원, Einsum 등).
2. **에이전트 질문** — 질문마다
   - 문서에서 뽑은 **선택지**(추천 표시 + 설명 + 이 모델에서의 주의점)
   - **추천 이유**와 근거 문서 링크
   - **직접 입력 칸**: 원하는 선택지가 없으면 값이나 문장으로 적습니다 ("GPU 없어요", `1x3x224x224` 등).
     형식이 분명하면 바로 값으로, 아니면 LLM 이 선택지로 해석합니다. 문서 선택지 밖의 값은 그대로 보내되 경고합니다.
   - **메모 칸**: 요청의 `user_notes` 로 함께 전달됩니다.
   - [기본값으로 넘어가기], [나머지는 기본값으로], [고급 옵션도 묻기]
3. **단계별 설정** (하단 전체 폭) — 문서 권장 순서로 실행 단계를 나열합니다.
   `init(필수) → generation(필수) → conversion(필수) → debug(선택) → compile(권장) → profiling(선택)`
   - 단계 카드의 체크박스로 실행 여부(`pipeline.steps`)를 켜고 끕니다.
   - 단계를 누르면 명령어·설명·산출물과 함께 그 단계의 **파라미터 키 / 설명 / 기본값 / 설정 값** 표가 나옵니다.
   - 허용값이 정해진 항목은 **드롭다운**(값 — 설명, `(기본)` 표시)으로 바꾸고, 목록에 없으면 `직접 입력…` 을 고릅니다.
     자유 입력 항목(경로·shape·숫자)은 입력칸, `debug.metrics` 같은 다중 선택은 체크박스입니다.
   - 바꾼 값은 에이전트 질문과 같은 답으로 기록됩니다 (표에서 정한 항목은 다시 묻지 않음). `기본값으로` 버튼으로 되돌립니다.
   - 앞의 값 때문에 쓰이지 않는 파라미터(예: precision=FP16 이면 calibration_*)는 조건과 함께 접힌 목록에 흐리게 표시합니다.
4. **설정 요약** — 정한 값과 출처(선택 / 직접 입력 / 입력→선택지 / 문서 밖 값 / 기본값). [수정] 으로 다시 물을 수 있습니다.
5. **최종 제출** — 탭으로 출력합니다.
   | 탭 | 내용 |
   |---|---|
   | MCP 요청 | JSON-RPC `tools/call` 본문 (request.json) |
   | HTTP · curl | Streamable HTTP 헤더, initialize → initialized → tools/call 순서의 curl |
   | YAML 파일 | `<model>.yaml`, `Config/DATA/dbgen_spec.yaml`, `Config/compiler_tuning_mode_config.yaml` 등 |
   | CLI 명령 | 같은 작업을 `eais` CLI 로 직접 할 때의 순서 |
   | 점검 결과 | 워크스페이스명≠모델명(Error 102), 단계 누락, shape 오류, 문서 밖 값 등 |
   | 도구 스키마 | SDK MCP 쪽에 있어야 할 도구 정의 (`tools/list` 형식) |

## 폴더 구조

```
verification_tool/
├── app.py                 # 로컬 서버 (:8780) — 화면 + /api/*
├── run.bat
├── .env.example           # OPENAI_API_KEY, SDK_MCP_URL, SDK_MCP_TOOL
├── tools/fetch_docs.py    # 사이트에서 SDK 3.0 문서를 다시 받는다
├── sdk_docs/
│   ├── raw/               # 원문 markdown 10개 (한국어 ko_*, 영어 en_*)
│   ├── index.json         # 문서 목록 · 원문 URL
│   └── kb.json            # 원문에서 뽑아 구조화한 파라미터 카탈로그 ← 에이전트가 쓰는 지식
├── lab/
│   ├── config.py          # 경로 · 모델 · 포트 · SDK MCP 주소
│   ├── llm.py             # Responses API + JSON 스키마 출력 (urllib)
│   ├── inspect_model.py   # ONNX(protobuf) / TFLite(flatbuffer) 메타정보 읽기
│   ├── kb.py              # kb.json 로드, 입력별 전개, when 조건 평가
│   ├── agent.py           # 세션 · 다음 질문 · 답 해석
│   └── mcp_request.py     # 최종 요청 · yaml · CLI · 점검
├── static/                # index.html · app.js · style.css (빌드 없음)
└── uploads/               # 업로드한 모델 (이 PC 에만 저장)
```

## SDK 문서 데이터화

사이트(`…/ai-studio/document/documentation/sdk-3.0`)는 React SPA 라 HTML 에 본문이 없습니다.
문서 뷰어가 부르는 공개 API 를 그대로 씁니다 — `tools/fetch_docs.py` 참고.

| 문서 | kb.json 에 옮긴 것 |
|---|---|
| EAIS 사용자 가이드 | 파이프라인, 워크스페이스 규칙, dbgen_spec 필드, `<model>.yaml` general/converter/compiler/profiler 전 파라미터, ModelValidator 규칙, 트러블슈팅 |
| SDK 3.0 업데이트 안내 | 2.5→3.0 변경점 (yaml 재초기화, .h5→.npy, MXINT8, --eht/--elt, 기본 device Gen-9) |
| 디버그 가이드 | debug mode/depth/metrics/thresholds, SNR 권장 기준과 개선 순서 |
| 컴파일 가이드 | compiler.mode, debug_str 프리셋(성능/사이즈), compiler_tuning_mode_config 주요 옵션 |
| 프로파일링 가이드 | profiler 섹션, profiler_advanced_config (SSH, core_num, mode, iter, target …) |

`kb.json` 의 `params` 한 항목 = 질문 하나입니다.

```json
{ "id": "converter.precision", "file": "model_yaml", "section": "converter", "key": "precision",
  "type": "enum", "level": "basic", "default": "A8W8",
  "when": [["pipeline.steps", "has", "conversion"], ["converter.skip_quantization", "!=", true]],
  "options": [{"value": "A8W8", "desc": "…"}, …],
  "doc": "eais-user-guide", "section_title": "converter 섹션 › precision" }
```

- `level`: `basic` 기본 질문 / `advanced` 고급 켰을 때만 / `auto` 묻지 않고 모델·기본값으로 채움 (요약에서 수정 가능)
- `per_input: true` 는 모델 입력마다 펼칩니다 (`dbgen.{input}.order` → `dbgen.images.order`).
- 동적 차원이 있는 입력의 shape, 모델에서 읽지 못한 dtype 은 자동으로 기본 질문으로 올라갑니다.
- 문서가 바뀌면 `python tools/fetch_docs.py` 로 원문을 받고 `kb.json` 을 고칩니다.

## SDK MCP 요청 형식

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
 "params": {"name": "eais_run_pipeline", "arguments": {
   "model": {"file_name": "MyNet.onnx", "format": "onnx", "size_bytes": 2000210, "sha256": "…", "uri": "file:///…/uploads/…/MyNet.onnx"},
   "workspace": "/home/user/eais-projects/MyNet",
   "steps": ["init", "generation", "conversion", "compile"],
   "conversion_options": {"stage": "full"},
   "model_yaml": {"general": {"device": "Gen-9"}, "converter": {"precision": "A8W8", …}, "compiler": {…}},
   "config_files": {"Config/DATA/dbgen_spec.yaml": {"images": {"random": false, "path": "./dataset", …}}},
   "custom_values": [ … 문서 선택지 밖 값 … ],
   "user_notes": [ … ] }}}
```

- **도구 이름·주소는 가정값**입니다 (`eais_run_pipeline` @ `http://127.0.0.1:8790/mcp`).
  실제 SDK MCP 사양을 받으면 `.env` 의 `SDK_MCP_URL` · `SDK_MCP_TOOL` 을 바꾸고,
  arguments 구조가 다르면 `lab/mcp_request.py` 의 `build()` / `tool_spec()` 을 맞춥니다.
- 모델 파일 자체는 요청에 싣지 않고 `uri` + `sha256` 으로 가리킵니다. SDK 서버가 파일을 가져갈 경로로 `uri` 를 바꿔야 할 수 있습니다.
- SSH 비밀번호는 묻지 않습니다. `${EAIS_SSH_PASSWD}` 자리표시자로만 들어가며 SDK 쪽에서 채웁니다.

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/status` | LLM 사용 여부, SDK MCP 주소 |
| GET | `/api/kb` · `/api/tool` | 지식베이스 요약 · 도구 스키마 |
| POST | `/api/upload?name=<파일명>` | 본문 = 모델 파일 바이트. 세션 생성 + 첫 질문 |
| POST | `/api/answer` | `{sid, id, choice | custom, note}` → 다음 질문 |
| POST | `/api/set` | `{sid, id, choice 또는 custom}` 단계별 설정 표에서 값 변경 (`choice: "__default__"` 는 기본값으로) |
| POST | `/api/skip` · `/api/edit` | `{sid, id}` 기본값으로 넘기기 · 다시 묻기 |
| POST | `/api/defaults` · `/api/advanced` | 나머지 기본값 채우기 · `{on}` 고급 질문 켜기 |
| POST | `/api/submit` | `{sid}` → `{request, http, files, cli, warnings, tool_spec}` |

오류는 `{"오류": "..."}` 로 돌아오고 서버는 계속 동작합니다. 세션은 메모리에만 있어 재시작하면 사라집니다.
