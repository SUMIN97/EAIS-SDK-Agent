# eais debug — 사용 가이드

`eais debug`는 변환(conversion) 결과물을 분석하는 커맨드입니다.
`--mode` 옵션으로 **정확도 검증(accuracy)**, **브라우저 시각화(visualize)**, 또는 **둘 다(all)** 실행할 수 있습니다.

---

## 목차

- [명령어](#명령어)
- [옵션 및 파라미터](#옵션-및-파라미터)
- [사전 조건](#사전-조건)
- [--mode 요약](#--mode-요약)
- [--mode 별 설명](#--mode-별-설명)
  - [--mode accuracy (기본)](#--mode-accuracy-기본)
  - [--mode visualize](#--mode-visualize)
  - [--mode all](#--mode-all)
- [accuracy 검증 결과 해석](#accuracy-검증-결과-해석)
- [accuracy_comparison_csv 해석 가이드](#accuracy_comparison_csv-해석-가이드)
- [Reference](#reference)
- [트러블슈팅](#트러블슈팅)

---

## 명령어

```bash
eais debug --w <workspace_path> [--mode accuracy|visualize|all] [옵션...]
```

## 옵션 및 파라미터

CLI 옵션(`--<key>`)과 `Config/debug.yaml` 파라미터는 동일한 키 이름을 공유하며, CLI로 전달한 값이 yaml 값보다 우선 적용됩니다.

| Key | 기본값 | 적용 모드 | 설명 |
|---|---|---|---|
| `--w` | 현재 작업 디렉토리 | 전체 | 워크스페이스 경로. CLI 전용. |
| `mode` | `accuracy` | 전체 | 실행 모드. `accuracy` / `visualize` / `all`. |
| `host` | `None` | `visualize`, `all` | 브라우저 URL에 사용할 IP 주소 또는 호스트명. 주로 `127.0.0.1` 사용. 필수. |
| `port` | `None` | `visualize`, `all` | 브라우저 URL에 사용할 포트. 주로 `40090` 사용. 필수. |
| `base_model_path` | `None` | `visualize`, `all` | 브라우저에서 열 기본 모델 파일 경로 (`.snc` / `.onnx`). `accuracy_result_path`를 지정하지 않은 경우 필수. |
| `base_encodings_path` | `None` | `visualize`, `all` | 기본 모델의 양자화 encodings 파일 경로 (`.encodings`). 선택. |
| `base_external_data_path` | `None` | `visualize`, `all` | 기본 모델의 ONNX external data 파일 경로 (2 GB 초과 모델용). 선택. |
| `base_activation_path` | `None` | `visualize`, `all` | 모드 `accuracy`로 생성된 기본 모델의 testvector `tvs` 폴더 경로. 선택. |
| `compare_model_path` | `None` | `visualize`, `all` | `base_model_path`와 diff 비교할 모델 파일 경로. 선택. |
| `compare_encodings_path` | `None` | `visualize`, `all` | 비교 모델의 양자화 encodings 파일 경로. 선택. |
| `compare_external_data_path` | `None` | `visualize`, `all` | 비교 모델의 ONNX external data 파일 경로. 선택. |
| `compare_activation_path` | `None` | `visualize`, `all` | 모드 `accuracy`로 생성된 비교 모델의 testvector `tvs` 폴더 경로. 선택. |
| `accuracy_result_path` | `None` | `visualize`, `all` | 브라우저에 함께 로드할 accuracy 결과 파일 경로 (`.xlsx` / `.csv`). 선택. |
| `pipeline_artifacts` | `Debug_result/pipeline_artifacts.json` | `accuracy`, `all` | `eais conversion` 실행 후 생성되는 `pipeline_artifacts.json` 경로. 필수. |
| `depth` | `full` | `accuracy`, `all` | 검증 범위. `endpoints`: 최종 산출물만 검증. `full`: 기록된 모든 변환 단계 산출물 검증. |
| `metrics` | `[SNR, PSNR, COSSIM]` | `accuracy`, `all` | 사용할 정확도 지표 목록. 기본값은 `SNR`, `PSNR`, `COSSIM` 세 가지. 사용 가능한 지표는 [지표 (Metrics)](#지표-metrics) 참고. |
| `thresholds` | `[10.0, 10.0, 0.5]` | `accuracy`, `all` | `metrics`와 1:1로 대응하는 PASS/FAIL 임계값. SNR·PSNR·COSSIM은 값 ≥ threshold이면 PASS, MAX_ABS_DIFF·MSE는 값 ≤ threshold이면 PASS. |
| `snc_input_name_mapping` | `exactly` | `accuracy`, `all` | 입력 데이터 폴더명과 SNC 모델 입력 이름을 매핑하는 방식. `exactly`: 이름이 완전히 동일한 경우에만 매칭. `postfix`: 먼저 완전 일치 이름을 대응시킨 뒤, 나머지는 한쪽 이름이 다른 쪽의 접두사인 쌍(`b.startswith(a)` 또는 `a.startswith(b)`) 중 길이 차이가 가장 작은 후보를 선택. |
| `testvector_name_mapping` | `exactly` | `accuracy`, `all` | 모델 간 testvector 이름을 매핑하는 방식. `exactly`: 이름이 완전히 동일한 경우에만 매칭. `postfix`: 먼저 완전 일치 이름을 대응시킨 뒤, 나머지는 한쪽 이름이 다른 쪽의 접두사인 쌍(`b.startswith(a)` 또는 `a.startswith(b)`) 중 길이 차이가 가장 작은 후보를 선택. |
| `save_layerwise_output` | `true` | `accuracy`, `all` | `true`로 설정 시 레이어별 출력값을 `Debug_result/accuracy_validation_results/<단계>/tvs/` 하위에 `.npy`로 저장. |

### `mode` 값

| 값 | 설명 |
|---|---|
| `accuracy` | `conversion`의 각 단계 산출물을 원본 모델(`0_INPUT`)과 비교해 정확도 지표(SNR, PSNR, COSSIM 등)를 측정합니다. 추론 입력 데이터로 `eais generation`이 생성한 `Config/DATA/input_data/`의 npy 파일을 사용합니다. |
| `visualize` | 브라우저에서 모델 그래프/레이어 구조 또는 accuracy 결과를 시각화합니다. |
| `all` | `accuracy` 실행 후 `visualize`를 순서대로 실행합니다. |

---

## 사전 조건

> [!WARNING]
> `--mode accuracy` / `--mode all` 사용 시: `eais conversion`이 완료되어 `<workspace>/Debug_result/pipeline_artifacts.json`이 존재해야 합니다.

> [!NOTE]
> `--mode visualize` / `--mode all` 사용 시: `--host`, `--port`는  각각 `127.0.0.1`, `40090`로 설정해 사용해주세요. 디버그 백엔드는 기본적으로 `40090` 포트에서 실행됩니다. 해당 포트가 다른 프로세스(Jupyter 등)에 의해 점유된 경우 `[ERROR] backend did not become ready in time` 오류가 발생할 수 있습니다.

---

## `--mode` 요약

| `--mode` | 설명 | 필수 옵션 |
|---|---|---|
| `accuracy` (기본) | conversion 각 모듈 산출물 간 정확도 지표(SNR, PSNR, COSSIM 등)를 계산. 결과는 `accuracy_comparison.xlsx` 및 `accuracy_comparison_csv/`에 저장 | (없음) |
| `visualize` | 브라우저 기반 시각화. 세 가지 기능을 단독 또는 조합해서 사용 가능:<br>① **단일 모델 시각화** — `--base_model_path` (`.snc` / `.onnx`), 선택적으로 `--base_encodings_path`, `--base_external_data_path` 지정 가능<br>② **두 모델 diff 비교** — `--compare_model_path` 추가 시 base/compare 모델의 노드 단위 diff 확인. 선택적으로 `--compare_encodings_path`, `--compare_external_data_path` 지정 가능<br>③ **accuracy 결과 시각화** — `--accuracy_result_path`로 `.xlsx` / `.csv` 결과를 브라우저에서 preload. 모델 없이 단독 사용도 가능 | `--base_model_path` 또는 `--accuracy_result_path` 중 하나 이상 필수 |
| `all` | `--mode accuracy` 완료 후 `--mode visualize`를 순서대로 실행 | `--base_model_path` 또는 `--accuracy_result_path` 중 하나 이상 필수 |

---

## `--mode` 별 설명

### `--mode accuracy` (기본)

#### 기능

`eais conversion`이 남긴 `pipeline_artifacts.json`을 기반으로 각 변환 단계 산출물을 pair로 비교해 **정확도 지표(SNR, PSNR, COSSIM 등)를 계산**합니다.
`depth=full`(기본값)일 때 아래 5개 단계의 모든 조합이 비교됩니다.

```
0_INPUT → 1_converter → 2_optimizer → 3_quantizer → 4_specifier
(원본)     (CNNX변환)    (최적화)       (양자화)       (HW최적화)
```

지표별 threshold를 만족하지 못한 레이어는 **FAIL**로 표시됩니다. 지표·threshold 상세는 [accuracy 검증 결과 해석](#accuracy-검증-결과-해석) 참고.

#### CLI 예시

**기본 실행 — `Config/debug.yaml`의 파라미터가 그대로 사용됩니다.**
```bash
eais debug --w ./hrnet_pose
```

**`--mode`를 명시적으로 지정 (기본과 동일).**
```bash
eais debug --w ./hrnet_pose --mode accuracy
```

**최종 단계(`0_INPUT VS 4_specifier`)만 검증 — CSV 1개만 생성됩니다.**
```bash
eais debug --w ./hrnet_pose --depth endpoints
```

**지표 및 threshold를 커스터마이즈 (metrics와 thresholds는 순서대로 1:1 대응).**
```bash
eais debug --w ./hrnet_pose \
  --metrics '["SNR","PSNR","COSSIM","MAX_ABS_DIFF"]' \
  --thresholds '[20.0, 30.0, 0.9, 0.01]'
```

**단계별 `.npy` feature map 저장 비활성화 (디스크 사용량 절약).**
```bash
eais debug --w ./hrnet_pose --save_layerwise_output false
```

> [!WARNING]
> `--mode accuracy` 실행에는 `<workspace>/Debug_result/pipeline_artifacts.json`이 필요합니다. 없다면 먼저 `eais conversion`을 완료하세요.

#### 산출물

| 파일 | 내용 |
|---|---|
| `Debug_result/debug_report.json` | 검증 전체 성공 여부 (`"valid": true/false`) — 가장 간단한 PASS/FAIL 확인 |
| `Debug_result/accuracy_validation_results/validation_report.json` | 레이어별 상세 PASS/FAIL, 지표 값, FAIL 원인 목록 (`fail_list`) |
| `Debug_result/accuracy_validation_results/accuracy_comparison.xlsx` | 모든 비교 pair의 지표를 하나의 Excel에 통합 (시트별로 pair 구분) |
| `Debug_result/accuracy_validation_results/accuracy_comparison_csv/` | 동일 내용을 pair별 CSV로 분리 (`0_INPUT VS 4_specifier.csv` 등) |
| `Debug_result/accuracy_validation_results/<step>/tvs/*.npy` | `save_layerwise_output: true` 일 때 저장되는 단계별 feature map |

전체 파일 트리는 [출력 파일 구조](#출력-파일-구조) 참고.

#### 결과 해석

| 확인 대상 | 어디를 봐야 하나 |
|---|---|
| 전체 PASS/FAIL | `debug_report.json` 의 `"valid"` 필드 (true = 전 레이어 통과) |
| FAIL이 발생한 레이어 목록 | `validation_report.json` 의 `results.AccuracyValidator.fail_list` — 각 레이어별 SNR/PSNR/COSSIM 값과 어떤 지표가 FAIL인지 |
| 지표 값을 상세히 비교 | `accuracy_comparison.xlsx` (전체) 또는 `accuracy_comparison_csv/<pair>.csv` (pair별) |
| 특정 단계의 실제 텐서 데이터 | `accuracy_validation_results/<step>/tvs/*.npy` (`save_layerwise_output: true`) |

- 지표·threshold·SNR 권장 기준 상세는 [accuracy 검증 결과 해석](#accuracy-검증-결과-해석) 참고.
- CSV 컬럼 의미와 `shape` vs `reshape` 규칙은 [accuracy_comparison_csv 해석 가이드](#accuracy_comparison_csv-해석-가이드) 참고.
- 브라우저에서 지표를 그래프로 확인하려면 아래 [accuracy 결과 단독 시각화](#accuracy-결과-단독-시각화-모델-없이)를 참고하세요.

---

### `--mode visualize`

#### 기능

디버그 백엔드를 띄우고, 지정한 리소스를 브라우저 그래프로 렌더링합니다.
아래 6가지 사용 케이스를 조합할 수 있으며, `--base_model_path`와 `--accuracy_result_path` 중 **하나 이상**은 반드시 지정해야 합니다.

| 케이스 | Key | 결과 URL |
|---|---|---|
| 단일 모델 시각화 | `--base_model_path` (+ 필요시 `--base_encodings_path`) | `?model=<uuid>` |
| accuracy 결과 단독 시각화 (모델 없이) | `--accuracy_result_path` | `?validator=<uuid>` |
| 모델 + accuracy 결과 함께 시각화 | `--base_model_path` + `--accuracy_result_path` | `?model=<uuid>&validator=<uuid>` |
| 두 모델 비교 (compare diff) | `--base_model_path` + `--compare_model_path` | `?model=<uuid>&compare=<uuid>` |
| 단일 모델 + activation tensor 시각화 | `--base_model_path` + `--base_activation_path` | `?model=<uuid>` |
| 두 모델 비교 + activation tensor 시각화 | `--base_model_path` + `--compare_model_path` + `--base_activation_path` + `--compare_activation_path` | `?model=<uuid>&compare=<uuid>` |

---

#### 단일 모델 시각화

**SNC 모델 시각화 — 최종 변환 결과를 확인하는 가장 기본적인 방법.**
```bash
eais debug --w ./hrnet_pose \
  --mode visualize \
  --base_model_path ./Converter_result/HW_output_new_snc_9.6.26.30.snc \
  --host 127.0.0.1 \
  --port 40090
```

**ONNX + encodings 모델 시각화 — 양자화 encodings를 함께 로드해 각 노드의 scale/offset 정보를 그래프에서 확인할 수 있습니다.**
```bash
eais debug --w ./hrnet_pose \
  --mode visualize \
  --base_model_path ./Converter_result/2_mixed_precision_quantization/output.onnx \
  --base_encodings_path ./Converter_result/2_mixed_precision_quantization/output.encodings \
  --host 127.0.0.1 \
  --port 40090
```

**2GB 초과 ONNX 모델 시각화 — external data 파일을 함께 지정 (LLM 등 대형 모델).**
```bash
eais debug --w ./llama_workspace \
  --mode visualize \
  --base_model_path ./Converter_result/llama.onnx \
  --base_external_data_path ./Converter_result/llama.onnx.data \
  --host 127.0.0.1 \
  --port 40090
```

- 정확도 검증 없이 기준 모델을 브라우저에서 바로 엽니다.
- ONNX 모델을 로드할 때 `--base_encodings_path`로 `.encodings` 파일을 함께 지정하면 양자화 정보를 반영한 그래프를 확인할 수 있습니다.

- 출력 예시:
  ```
  [INFO] backend already running on http://127.0.0.1:40090
  [INFO] Uploading base: HW_output_new_snc_9.7.9.30.snc ...
  [INFO] base model UUID: 562fd416-28cb-4016-aed1-ffae8967c3e9
  [URL] http://127.0.0.1:40090/?model=562fd416-28cb-4016-aed1-ffae8967c3e9
  ```

아래는 CNNX 모델을 로드했을 때의 그래프 화면 예시입니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/cad2d95a-bb63-467d-bed4-aa24f739178a?response-content-type=image%2Fpng&Expires=1796581128&Signature=UooXBMejn4w-naHJkRVD-hMPCAVBvYri2~ySshAqUhnUDoYM~VZ4Yk7kB08XMAbcZF4PZpnIZpTAh~QNzcSTPjcAs23-K0yvoSIkTjZJFLBhbwIk3dF7ZCmiOJMp-R9razlH8u8hmcs8ii9w1kl2RZC5FL1qHsbCvtvlV-jj6V2wv2mlqCh~NVYpOgiRzPg6kVlqh6YgD4E04GsqwbauxbzKllKWjNiDo5FXBl0max0CCyD11o7N7HPuavhp3ax9B-Wku1CPoDjTf~a6iMS5M3bUpCNDLk8iQvkG9d5Z1COZwEX8HmHtclKb6S4WjbJLKqqQxpap36Zr01THiCYlHw__&Key-Pair-Id=K3Q589AYB0FA7R)

---

#### accuracy 결과 단독 시각화 (모델 없이)

> [!NOTE]
> `--accuracy_result_path`로 지정할 파일은 사전에 `eais debug --mode accuracy` (또는 `--mode all`)를 실행해 미리 생성해 두어야 합니다. 해당 파일이 없으면 시각화가 실패합니다.

**xlsx 결과 시각화 — 모든 비교 pair가 통합된 결과 (권장).**
```bash
eais debug --w ./hrnet_pose \
  --mode visualize \
  --accuracy_result_path ./Debug_result/accuracy_validation_results/accuracy_comparison.xlsx
```

**특정 pair CSV만 시각화 — 원본 vs 최종 결과만 확인하고 싶을 때.**
```bash
eais debug --w ./hrnet_pose \
  --mode visualize \
  --accuracy_result_path "./Debug_result/accuracy_validation_results/accuracy_comparison_csv/0_INPUT VS 4_specifier.csv"
```

- 모델 파일 없이 `eais debug --mode accuracy`가 생성한 산출물(`accuracy_comparison.xlsx` / `.csv`)을 브라우저에서 확인합니다.
- `accuracy_comparison.xlsx`에는 모든 변환 단계 간 비교 쌍의 지표가 담겨 있으므로 이 파일 사용을 권장합니다.
- 출력 예시:
  ```
  [INFO] Uploading validator ...
  [INFO] Validator UUID: c97d946b3ff04ac4969ef59445f4bf37
  [URL] http://127.0.0.1:40090/?validator=c97d946b3ff04ac4969ef59445f4bf37
  ```

accuracy 결과를 로드하면 아래와 같이 **Accuracy 탭**에서 파이프라인 단계별 SNR/PSNR 지표와 레이어별 통과율을 확인할 수 있습니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/66b9047f-6b8d-4a40-9f5a-e73049ae94aa?response-content-type=image%2Fpng&Expires=1796581128&Signature=GGK5ityO~JtEuS4CZYz6BAAFLNLpARQYa611v5cA49vsxqXCuO8HHjJbZRr8PZxWpYqPvsPA2UWw2V46U7nYrnzVRjD9V8HXBUNrjKSPbWMhTkRo~9y-Pi64z4lK5vLjfpjUM7ppcbLxnMsAiqieY66bqMCH9uX-0jB24VGw3Yy1-XAz8tW1exc5U5DOhlqLZXoi7MANJzQVE9gjmMxaILYiKA-gvI5L2Q87sSWCCn42tYtbVghaHHoHOGgkvIxLNMQRbp9o0kPOHnq~S6LXemcsgmMSFJ7F55lI003rJv21PyqOIWLYBkTwH1TKsI53L3aKplP7MZCoBfrCaZtcsw__&Key-Pair-Id=K3Q589AYB0FA7R)

---

#### 모델 + accuracy 결과 함께 시각화

**SNC 모델 + xlsx 결과 — 그래프에서 각 레이어를 클릭하면 정확도 지표가 함께 표시됩니다.**
```bash
eais debug --w ./hrnet_pose \
  --mode visualize \
  --base_model_path ./Converter_result/HW_output_new_snc_9.6.26.30.snc \
  --accuracy_result_path ./Debug_result/accuracy_validation_results/accuracy_comparison.xlsx
```

**ONNX (양자화 이후) + xlsx — 원본 그래프에 최종 정확도를 매핑해 어떤 노드에서 정확도 손실이 큰지 시각적으로 확인.**
```bash
eais debug --w ./hrnet_pose \
  --mode visualize \
  --base_model_path ./Converter_result/2_mixed_precision_quantization/output.onnx \
  --base_encodings_path ./Converter_result/2_mixed_precision_quantization/output.encodings \
  --accuracy_result_path ./Debug_result/accuracy_validation_results/accuracy_comparison.xlsx
```

- 브라우저에서 모델 그래프와 accuracy 결과를 함께 볼 수 있습니다.
- `accuracy_comparison.xlsx`에는 모든 변환 단계 간 비교 쌍의 지표가 담겨 있으므로 이 파일 사용을 권장합니다.
- 출력 예시:
  ```
  [URL] http://127.0.0.1:40090/?model=a0c97814-...&validator=8f3c1e2b-...
  ```

---

#### 두 모델 비교 (compare diff)

**양자화 이후 ONNX(base) vs 최종 SNC(compare) — 양자화·컴파일 파이프라인에서 노드가 어떻게 삽입/변형되었는지 확인 (가장 자주 쓰는 조합).**
```bash
eais debug --w ./hrnet_pose \
  --mode visualize \
  --base_model_path ./Converter_result/2_mixed_precision_quantization/output.onnx \
  --base_encodings_path ./Converter_result/2_mixed_precision_quantization/output.encodings \
  --compare_model_path ./Converter_result/HW_output_new_snc_9.7.3.30.snc
```

**SNC(base) vs SNC(compare) — SDK 버전 업그레이드 전후, 옵션 변경 전후의 최종 SNC를 나란히 비교.**
```bash
eais debug --w ./hrnet_pose \
  --mode visualize \
  --base_model_path ./Converter_result_v9.7.3/HW_output_new_snc_9.7.3.30.snc \
  --compare_model_path ./Converter_result/HW_output_new_snc_9.7.9.30.snc
```

**base·compare 모두 encodings 지정 — 두 ONNX 모델을 양자화 정보와 함께 비교.**
```bash
eais debug --w ./hrnet_pose \
  --mode visualize \
  --base_model_path ./old/output.onnx \
  --base_encodings_path ./old/output.encodings \
  --compare_model_path ./new/output.onnx \
  --compare_encodings_path ./new/output.encodings
```

- 기준(base) 모델과 비교(compare) 모델을 함께 브라우저에 로드해 그래프/노드 단위로 diff를 볼 수 있습니다.
- 자주 쓰는 조합: **양자화 이후 ONNX(+encodings)** vs **최종 SNC** → 양자화·컴파일 과정에서 어떤 노드가 어떻게 변했는지 확인.
- 출력 예시:
  ```
  [INFO] Uploading base: output.onnx, output.encodings ...
  [INFO] base model UUID: bd44b8f6-a6d2-434c-ac0e-70070bcc3966
  [INFO] Uploading compare: HW_output_new_snc_9.7.9.30.snc ...
  [INFO] compare model UUID: 691c1ae1-05c0-4e15-8d2d-d8847260b59c
  [URL] http://127.0.0.1:40090/?model=bd44b8f6-...&compare=691c1ae1-...
  ```

> [!NOTE]
> `--compare_model_path`를 지정하려면 `--base_model_path`도 반드시 함께 지정해야 합니다. 비교 모델도 encodings/external data가 있으면 각각 `--compare_encodings_path`, `--compare_external_data_path`로 지정합니다.

##### Diff 색상 가이드

`name`값 기준으로 왼쪽(base) 모델과 오른쪽(compare) 모델의 비교를 시각화한 부분입니다.

| 색상 | 위치 | 의미 |
|---|---|---|
| 🔴 빨간색 테두리 | 왼쪽(base) | 오른쪽 모델에는 없는 레이어 — base에서 삭제된 레이어 |
| 🟢 초록색 테두리 | 오른쪽(compare) | 왼쪽 모델에는 없는 레이어 — compare에서 추가된 레이어 |
| 🟡 노란색 테두리 | 양쪽 | 동일한 name의 레이어지만 속성값(attribute) 등이 변경된 레이어 |

아래 예시에서 오른쪽에 초록색 `QuantizeLinear` 레이어가 추가되었고, 양쪽의 `Conv` 레이어는 노란색으로 속성 변경이 있음을 나타냅니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/78cf835c-1cea-48bd-aabb-774502735c3a?response-content-type=image%2Fpng&Expires=1796581128&Signature=WdTfjAmMg6mFOYwrL5sjz8~kilgZcqRJHdJX3fv-quJgpFb~LrYxGMYXrcdikuqZKGLri1cOHWKaju7AIQl9qLfUph4pY5NCEYa9Vo~vxpPQjFO4ozGFGrpUud0XKGgNiYKsQbQAeqJt7cBnDMxPa6NLDQHSmo-TJKTN3jY7-sMtB7-xE84vSRHhbsNL1SruYFSX2wYDdzD3jhZIVSioSCxEZQW9HzkWikrybzxNCbo8TcPVB~n-VI0VPU8ZDlEIZjs-7Ns1dBzsex08WlCQ6UQ9IOPzOBGnw2kmOyBdL0wdmmrSpF~CeOUJ~cAnb-dLSM8fESi2JlLDEFVfjPrc8Q__&Key-Pair-Id=K3Q589AYB0FA7R)

노란색 테두리 레이어를 클릭하면 양쪽 모델의 속성값을 나란히 비교할 수 있습니다. 초록색 불릿(●)은 변경된 속성을 표시합니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/c4eddb44-f927-447c-a453-c8d30857aa1b?response-content-type=image%2Fpng&Expires=1796581128&Signature=EuNGdw1aCB8Elcfo~jnDEJ3pxOTPtBXG1KTc93rC028ka5uCFH~va72uWgwSq8lWsYtfBZXA9erQnEzuqmvG5AkeZMb1QuipzDIcI-fq04MGAsH3iARjZT4KO4PH70t5oIeaFxc79LCn~g8CHRPc8GzHy4ymFkwoh~6WRIlJjmM7AOjJzTW8dOvJw3tK2HT1uGTfJZoyD2PCBiQGMt6YSVYSC48eSPoiQwQV5-6HBEgB7Ke1cTPs1JCIbPK-vgb74EOQrJcEuDP9APnoSc3dUAk6PdwiDECCPdqpEdHwnG5Suble3hSOiGmIZbmOH-9naSmjtWvScvhXqjeAzMVVwQ__&Key-Pair-Id=K3Q589AYB0FA7R)

---

#### activation tensor 시각화 (`--base_activation_path` / `--compare_activation_path`)

`--mode accuracy`(또는 `--mode all`)를 `save_layerwise_output: true`로 실행하면 각 변환 단계의 레이어별 출력값이 `.npy` 파일로 저장됩니다. `--base_activation_path`/`--compare_activation_path`로 해당 디렉토리를 지정하면 브라우저 UI에서 **노드를 클릭할 때 activation tensor 분포(히스토그램)**를 바로 확인할 수 있습니다.

> [!NOTE]
> `--base_activation_path`로 지정할 디렉토리는 사전에 `eais debug --mode accuracy`를 `save_layerwise_output: true`(기본값)로 실행해 미리 생성해 두어야 합니다. 위치는 `Debug_result/accuracy_validation_results/<단계>/tvs/` 입니다.

**단일 모델 + base activation 시각화 — SNC 그래프를 보면서 레이어별 activation 분포 확인.**
```bash
eais debug --w ./hrnet_pose \
  --mode visualize \
  --base_model_path ./Converter_result/HW_output_new_snc_9.7.9.30.snc \
  --base_activation_path ./Debug_result/accuracy_validation_results/0_INPUT/tvs
```

엣지를 클릭하면 우측 inspector의 **ACTIVATION DISTRIBUTION** 섹션에 히스토그램이 표시되며, 클릭 시 확대된 activation 분포 창이 열립니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/54c8654b-62f9-4083-a387-8d9b212fbb52?response-content-type=image%2Fpng&Expires=1796581128&Signature=GyWz-jpnD8LXCbbGyHqlU4a4hS-a6ujwP9N07IhyhB5Zwnh4z2yPJujsQ2Ongx3bp67uTBqnsyxs0SPKbBInts9IVzFiJhy-lPICdxB0QAAA8fVHKG5SwLgWmfYmgcwuLz4MycdALl0pMRPxCZWd3SbU~K6WvDVTatVD1OJovuTVb0e7m3BSp6cNNO8ndOlppaEvzaZ5m52LwEiuPQx43zFU5CHWiL9dtNZPQnz63Cty~ad1eZF5gGz7L4yPFT8llwhSAmRo~7wUbXDLWinIbwUXoNbcmOreY11hCpK0YjPMtfoqX6jJPuQ9jlKu9l6LcFATEa9cHd~EbjEspMJ4Jw__&Key-Pair-Id=K3Q589AYB0FA7R)

**ONNX+encodings + activation — 양자화 이후 레이어별 activation 분포를 확인할 때.**
```bash
eais debug --w ./hrnet_pose \
  --mode visualize \
  --base_model_path ./Converter_result/2_mixed_precision_quantization/output.onnx \
  --base_encodings_path ./Converter_result/2_mixed_precision_quantization/output.encodings \
  --base_activation_path ./Debug_result/accuracy_validation_results/0_INPUT/tvs
```

**두 모델 diff + 양쪽 activation — base/compare 모델을 diff하면서 양쪽의 activation 분포를 나란히 비교.**
```bash
eais debug --w ./hrnet_pose \
  --mode visualize \
  --base_model_path ./Converter_result/2_mixed_precision_quantization/output.onnx \
  --base_encodings_path ./Converter_result/2_mixed_precision_quantization/output.encodings \
  --compare_model_path ./Converter_result/HW_output_new_snc_9.7.9.30.snc \
  --base_activation_path ./Debug_result/accuracy_validation_results/0_INPUT/tvs \
  --compare_activation_path ./Debug_result/accuracy_validation_results/4_specifier/tvs
```

두 모델을 diff하면서 양쪽의 activation 분포를 나란히 확인한 예시입니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/9c806155-4d3e-4ee0-8a61-9290fed9cbbc?response-content-type=image%2Fpng&Expires=1796581128&Signature=BOu46Phw2pjT7548kidLJYBr9PAdsAuyskJn5ialqkrx7skFC3bsTd1U-rBvdVhi1KkGe-HAvcAQkqxFgu8PyzL8mBzywJFPWtXUXF4N5Iy6~-W8qSqGxf5OMbjBP3hd3eyTvNQ9rIBMLbnqET8UwSl1buMkOqWt7CdVYlvF6eyv6ZPAuJbe3sUDTe52cnKzEQauzzfycfOvkdiybjrX~fIocvo4lPB0LbRUCxUQKXK4My0k173Ymh4F2uUZbw~8sGTjB5xU9aDJkfVvYnTpwu9KK-rN272r36KlB-Be0FwJv8wSSOsDcwEtEjTDpxyjlGLf2x048-xUD5b6PmbmYg__&Key-Pair-Id=K3Q589AYB0FA7R)

- activation `.npy` 파일명은 엣지 이름에서 `/`를 `_`로 치환한 값과 일치해야 합니다.
- 로드된 activation 데이터는 노드 클릭 시 우측 inspector **VALUE** 섹션에 히스토그램으로 표시됩니다.
- `--compare_activation_path`는 `--compare_model_path`가 함께 지정된 경우에만 의미가 있습니다.

> [!NOTE]
> `--host`/`--port`는 각각 `127.0.0.1`, `40090`를 사용해 주세요.

---

#### 브라우저에서 열린 후 사용법

브라우저에 로드된 웹 UI를 이용해 모델을 탐색·검사·편집·비교하고, accuracy 결과를 확인할 수 있습니다.

##### 뷰 전환 — Graph / Accuracy

컨텐츠 영역 좌상단의 **view switcher**로 두 뷰를 전환합니다.

- **Graph** — 네트워크 토폴로지 (기본)
- **Accuracy** — 레이어별 정확도 분석 (accuracy 결과가 로드된 경우)

두 뷰는 함께 마운트되어 있어 전환할 때 모델이 다시 로드되지 않습니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/2667e129-1ca2-4735-869f-0574fda99dfa?response-content-type=image%2Fpng&Expires=1796581128&Signature=hQgzTiXRajKHAPRgplBnkTdEgoVKcIjtwkIaLSqdxaEqitafhZJy0wIHltdw8E~4GkzHJpCjqnqBhwUdiBfteNYoWWRMxcrA2~ZgOuiQCTyY03u0A1-kAa8o~2hU-9mBGWELNrziG6HeRTvWCcD63CgoXrg1MxklW9P1pdTPU5-8ifJBm~6VAcPFT8NyKPDBDYDEfEbVWYSd4s51rhxhIstE8ajgu6slfurN6lWWsNFIwjZxCLXjekZof-A4vEL5DpmJ2qFURXA~ZDx-cvdIulmo2-g1o9YxWfp1Hyaq3J29iA~4YPs-jmdC0Ov1zquwtV62pelllZ2UtmyVG~Lq0w__&Key-Pair-Id=K3Q589AYB0FA7R)

##### Graph 뷰 — 캔버스 조작

- **Pan** — 빈 캔버스 드래그 또는 스크롤
- **Zoom** — 스크롤·핀치 또는 −/+ 버튼 (한 번 클릭 시 1.5×)
- 캔버스 좌하단 **screen controller**에는 다음이 포함됩니다.
  - **미니맵 (120 × 160)** — 전체 그래프 위에 현재 뷰포트 박스를 표시
  - **Fit to screen** — 전체 그래프를 화면에 맞춤
  - **Zoom out (−) / Zoom in (+)**

![image](https://soc-developer.semiconductor.samsung.com/ai1/aa529c4f-555e-4f2a-8b0e-684556bc8804?response-content-type=image%2Fpng&Expires=1796581128&Signature=aJddoaCvDO17b4QIHGFvr82wNKaUbCsI9uEtdBKKsAd7ymg4J1SidCcKf~icFYd-uQZx3n3-IjEmMBM1HOwcF-iXh7cx7PjxKGTzFbaotKDxSao5ztLxzvSRIx3hnjI~3zAC0gth69GRYkw5-qWlLTY6C74E2aAKNbkuv5Jxah9BKYqAIkWW9sc7QpRPk5jPHBrgo-2UVWXt~Ldlm-qb3KN3qAAbycEI2Xc-gT7ypI~G-4DMMzdIvPNPy-0BSWGjeZkU44yzrHUH5KuaVVl0J1Gw10r9R7DII1ZjnrFudESn6HZAInY3UIonsX795-RGTrmaEYZTkfVdjvdOwoiMog__&Key-Pair-Id=K3Q589AYB0FA7R)

##### 노드·엣지 선택

- **노드**는 연산자/레이어, **엣지**는 그 사이를 흐르는 tensor입니다.
- 노드/엣지/tensor를 클릭하면 강조 링이 표시되고 우측 **inspector**에 상세 정보가 열립니다.
- 빈 캔버스 클릭 시 선택 해제. 라이트/다크 테마는 좌측 사이드바 하단 토글로 전환.

##### 노드 라벨 설정 (⚙️ General)

좌측 그래프 사이드바 ⚙️ 아이콘에서 다음을 지정한 뒤 **Apply Changes**를 눌러 반영합니다.

- **Node Label Type** (택 1)
  - `Operator` — op 타입으로 라벨 (예: `Conv2D`, `Add`)
  - `Name` — 전체 노드 이름 (ONNX-style 경로)
- **Show Mode** (조합 가능)
  - `Attributes` — 각 노드에 연산자 속성 행 표시
  - `Weights` — 각 노드에 kernel/bias 정보 표시

`Attributes`/`Weights`를 켜면 노드가 커지고 정보가 풍부해지며, 끄면 토폴로지만 깔끔하게 볼 수 있습니다.

---

##### 그래프 사이드바 아이콘

| 아이콘 | 패널 | 용도 |
|---|---|---|
| ℹ️ | **Model Info** | 모델 메타데이터·입력/출력 포트 요약 |
| 🔍 | **Search** | 노드·엣지·tensor 검색 |
| ⚙️ | **General** | 노드 라벨 & Show Mode |
| 🎨 | **Color** | 연산자별·metadata 기반 컬러 규칙 |
| 🔻 | **Filter** | metadata 기반 필터링 |

##### Model Info (ℹ️)

- **MODEL PROPERTIES** — `format`, `name`, `version`, `graph`, `nodes`·`edges`·`tensors` 개수
- **INPUTS / OUTPUTS** — 각 포트의 `name`, `tensor (dtype[shape])`, 양자화 metadata (`scale`, `zero_point` 등), `location` 인덱스
- 모델이 로드되지 않았다면 *"No model loaded. Upload a model to see its properties."* 문구가 표시됩니다.
- diff 모드에서는 A vs B 비교로 확장되며 상단에 **Diff Summary** (format / nodes / edges / tensors delta, added / deleted / modified 개수)가 표시됩니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/b7619ffe-3a85-4007-a109-4ba5d530ccde?response-content-type=image%2Fpng&Expires=1796581128&Signature=Fr4f2tSodX4bcQ2K5U~6DhpBJX2JzoCj044K-5QTxvhuRc4PEv4TyMyAOqOe8h3L~5oUZz6fR7pXCVA296a0l2qgZ-GXbupOEWGSrMRfRXb~FFwSCkciWjmZuPOkYtGV9~3JQ8Plqqw8OF8jawp9IejDGippSi4~zjdaXslpi7RQoCSQxIj-DSmousiChKz4k52DaOeTCutodbffGiaBqlxDHP75J2eLlL3hreoQ9Az8TvMDzPXPnqX7Fr1xFqMF1WEkvndBT1sS22ilVZPMbfqCSI9X7SPenFkrnQYBYTJS8Td069fJ5XfRmaiIapVnZg3b2-e56UKwxDaUuWb2sg__&Key-Pair-Id=K3Q589AYB0FA7R)

##### Search (🔍)

이름으로 요소를 찾습니다. 결과는 실시간 반영되며 대형 모델에서도 반응이 빠릅니다.

- **Nodes** — 이름 / op 타입
- **Edges** — tensor 이름 / 연결 관계
- **Tensors** — 이름 / 소유 노드

결과를 클릭하면 캔버스에서 선택되고 inspector가 열립니다. diff 모드에서는 A | B 두 열로 나뉘고 **Changes** 필터(Added / Modified / Deleted)로 변경된 항목만 볼 수 있습니다.

diff 모드의 Search 패널 예시입니다. **SEARCH IN**으로 Node/Edge/Tensor 타입을 선택하고, **CHANGE STATUS**로 Added / Removed / Changed / Unchanged 상태별 개수를 확인하며 필터링할 수 있습니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/36e9e170-7f7f-475b-876f-7382e82d8afa?response-content-type=image%2Fpng&Expires=1796581128&Signature=DGGJiG9zScIA~tI8J-ZMI4NncFynJXW9lTaD0Ff5vPNW6vv2yEmuPSlaMuwL0yM5kYX0lfWV~ttTmdvf5XLm6Jdb9UQ0j7Z6pZPoG-BwrTaIByuAcY9HB2Cn8L-DF04PsjsdhhBi6cdN-pNHGVjYQXkxCSPKWyXMwmmeEO~V2v4qp2fAJ6-nGyw8S3HG5ne1sbu8rRQCEpu-mrdSL6ZN~Ddho7WY3YsP9-S66iQmpxhhffVg9odh~Akw8ZRT5t~3SpbS4luPyJWN2lPQRaZQDjwgxvPoI6sLTE0PhxASeTXTJi-6XDyr-0UQJnEO2Raaa4~OFJDiRS2ywV2ie59puQ__&Key-Pair-Id=K3Q589AYB0FA7R)

![image](https://soc-developer.semiconductor.samsung.com/ai1/3a348c70-83de-477e-ac60-b7e9c5d13a21?response-content-type=image%2Fpng&Expires=1796581128&Signature=boIKWCYgGpa94Y807~c06ToDZfOWZiJ9YhyqaIP~r4wMbegBv8z4M38eBSBeHeyClT81quzRAM3JowQR6P0b-L-CSWjaSONandbxPnrqo3byaGgqbLREj3HSZZbw0XXW03fLs1Ee9gmy7XcpZtCPevaoSgcKGucDQo~nVHnmbEfiNGqI2RbNwnXPT01GjnRFvOYpPyP1JuHYacFAHhKMuBIzE5TM6VfYVGn9WzxYo6wryTJM6IPaGg3~WFB7SAw7ym84lMBZi09devKwvZhAyodI5FxFamalrUGnIMgKGm1x9ExxWgQxcKINn8RYNAcUf~2HASa4O70C-dltnDSz6w__&Key-Pair-Id=K3Q589AYB0FA7R)

##### 선택 inspector (Data Drawer)

노드·엣지·tensor를 선택하면 우측에 상세 패널이 열립니다.

- **Node** — 이름, op 타입, 속성, 연결된 입력/출력 tensor
- **Edge** — source → target 노드와 흐르는 tensor
- **Tensor** — shape, dtype, 양자화 metadata. **Min / Max / Mean** 통계와 raw **VALUE**(요청 시 로드)

Inspector 툴바:
- **Center on selected element** — 선택 요소를 캔버스 중심에 배치
- **Clear selection** — 선택 해제
- **Collapse info panel** — 드로어 접기/펼치기

###### Tensor 분포 (히스토그램)

Tensor 선택 시 **VALUE** 섹션에 값 분포 히스토그램이 표시됩니다. `Elements / Mean / Min / Max`와 스크롤 가능한 raw 값 리스트도 함께 확인할 수 있습니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/fdbf7dba-042d-44db-9c5e-0f74b646ef76?response-content-type=image%2Fpng&Expires=1796581128&Signature=WFABNKMEcUcwWWznqQnmqNRoNzwxiRqdOpdtAGYuGH5sS~zfV0c9UWccKBH~f270Gco9lw1mbyDuQsKWPFZ2or5nubgZh~H1M3wRDfUE9swRIcqPMejFucm9E4PmebqPZyID69zEd58Baj96013q5bfXLrh2LtWSeU3DeWzVqofdnMJzqEV7yIzKG5nQZTqVB77FBddcfCOSJ9MMEjbi8kdYpsrkLtip0d7gV7S05c-8UFf0PwV-ZIaV8cfwyTDxSL3lUUP~Ag5qHbyXnyvSlRYpvul~yIzK5zALfvBhS73gsqGR8XEJQmcoHAQsFbFSB6MM2n6Psjjw3blR~G8IVw__&Key-Pair-Id=K3Q589AYB0FA7R)

히스토그램을 클릭하면 확대된 **Tensor distribution** 화면이 열리며 (`n / min / max / mean / std` 표기), **Download PNG**로 차트를 저장할 수 있습니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/c103b6c3-d752-4011-8e6e-1c8d0285a631?response-content-type=image%2Fpng&Expires=1796581128&Signature=a3A-0QZj5W~Mn4r9eyV3QOWALs9Hl4y3hdP7Q6QYESzd-NbFyq2WAzLZTgyHTp09uMSPTdBdIaHB2lYN-fnjZngnG~fYGlNpF-Jh8Y10vj9zc9UTsKx7Ovz8MXnq5NXxvL~rZBxPXg~~hZAqyMwetMrh36DLWyeZ32osstfqzZzudAuJgrtgDuAaVisbEQxpeCut2Yg8OvjjOTPQKy7pWWURtP-2V4iCU5vq3jPudpYgGiNfY9wNJA9weOw8gV1KN1toLrHSEyVvfKCuf39IUBZ1FEEI5soc0SgF226FJuEPVZN4W0lxUSlN9dLNzUZE1sGTualDdeu-ADrVmCws9w__&Key-Pair-Id=K3Q589AYB0FA7R)

> SNC 모델의 경우 노드 속성과 tensor metadata는 이 드로어에서 **편집 가능**합니다. 아래 [편집 및 SNC 재출력](#편집-및-snc-재출력) 참고.

---

##### 컬러 & 필터 (🎨 / 🔻)

설정은 **모델 인스턴스별**로 저장되며, diff 모드에서는 A/B 양쪽에 동시 적용됩니다. 변경 후 **Apply Changes**(반영) 또는 **Reset**(취소)을 눌러 확정합니다.

**Operator colors (🎨)** — 연산자 타입별 컬러 지정 (예: 모든 `Conv2D`를 특정 색). 프리뷰 박스로 확인 가능하며, 기본값으로 초기화 가능.

![image](https://soc-developer.semiconductor.samsung.com/ai1/bc4788e5-ecdd-422a-9c27-1c5729425acf?response-content-type=image%2Fpng&Expires=1796581128&Signature=CUrR4qiZaoeY9lmW29mFNLc4KcOMSUdSWUmMLU0KD9Qnn7AQfj0uuAuWuxWQ5qYO58ehIqFwqRx67WvPgMjYzJNymrsQZgvYOExF6LoM9-jrgs5B~13rx2oLmNKTvF5vVfnIzon4uWG8AaA3Wn82R~VL4yGpfOkcrx9pHz~X-D~431p9s639jISMvVuepLfa-YfkerAUA9O0yayCRAS8vSvjjMEnPkTx4dWxibt8IhtqHXBgbMnW14xcsiCMIM4EhZNqHM8og9BURAc1KnKJZUj-qaTHU9VlpJWIELXRfMhHwxEpHSlUKLLmK5mHsLOH3iTeTbFXhNSrKXIXAsOEnA__&Key-Pair-Id=K3Q589AYB0FA7R)

**Metadata color rules (🎨)** — metadata 조건(key = value 등)에 매칭되는 노드에 컬러를 부여. 규칙 생성/편집/삭제 가능.

![image](https://soc-developer.semiconductor.samsung.com/ai1/3188fea7-8247-4acd-ba09-470188f2c983?response-content-type=image%2Fpng&Expires=1796581128&Signature=S~-BkzzD0oRt4zLXJ2Dnw6IT3DGXhIWbp5b0nE1xp9FUaQIS7CzTDhydsfEbindbEXUj-RVQmhyPn~X5VUejbuXBGyLexHoT3ZlCvTPSYnDmHiVgfwtDtefDuBriWItR7mdT31q1mIqEVY9tJ72acOT4UmgnrPwHvRD4sQ7WM3Lgyug09loPQNTU45mAOuS-w8B9M0WlIxHuDOsamkQ6m4i7IAIsJBvAp88xocvFqiVd~aU0XDR5dbip1UqRmjVS1TgL9SUyFZ4CP5AF6ZH8zLE~JdSEr-nvUf~kLy4pWStx5vfmu1hilleZSDG7rIla~A5Q92iZwnsX5xBvl8dy3g__&Key-Pair-Id=K3Q589AYB0FA7R)

**Metadata Filter (🔻)** — metadata 조건으로 노드/엣지를 숨기거나 표시. 관심 있는 요소만 그래프에 남길 때 유용 (예: 양자화 타입별).

![image](https://soc-developer.semiconductor.samsung.com/ai1/d61a347b-5c28-4fad-be4f-ca04ffb1f2b1?response-content-type=image%2Fpng&Expires=1796581128&Signature=P6dJ4fUhtGVkwIDgJ9JlM4aaGld3x-ZQL07EpnGRFVLZn5Cp0qiv7uxxq4XQ~ksvrcDZUo-RufktAqMPiSrwVD6eDZkf3CG~CG8SgkBNNSaXkkVTFYkpB5F9Kew3ea~KS3UmyA3E9beApuwHbmP3bNN5ppFGG9ZRfD5riRB4Qq7r9QHajBN9fzOsqjY0VUGOe1zFPKoO2YPsjUGY3YYhFDOKMqG9Yc16NY6ODDpnGFO63~QDvtSnId-DIGwFZ61kW8HNLRC6sUyPcDaA~XRuoggyFFemmBmoUlana3Iw1pKtYFFYmuQJAC8Xj-iiozZrR~aPi4PnpJi2s6LL8dMiMQ__&Key-Pair-Id=K3Q589AYB0FA7R)

> **Import / Export settings** — 설정 드로어에서 컬러·필터 구성을 파일로 내보내거나 불러와 세션 간 재사용할 수 있습니다.

---

##### 편집 및 SNC 재출력

**편집 가능한 대상 (SNC 모델)**
- **Node attributes** — 연산자 속성 값
- **Tensor / edge metadata** — 양자화 annotation (`scale`, `zero_point` 등)

우측 inspector에서 필드를 직접 편집하면 변경 사항이 즉시 기록됩니다. 변환 진행 중에는 편집·다운로드 버튼이 잠깁니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/482678b8-02fb-4be4-a838-a8e45ce937f4?response-content-type=image%2Fpng&Expires=1796581128&Signature=IjuAA4-U3Z1IvTU~INU7PgIrWSiXxlxxmyhpPVPK5mztYifwluVwnu7FXC-x9czZTOadZPvBNeAq-RAgjowpQgzOASlG4AYg~PCxqxhNXtaAfvpaqzre9r9mtpXTjRFDaCCGD89jNceCot9kpZvePbyZsEHzcXrSqyN8qXF1dci1SGlZ0ZsJw-rTZQF-~Mse~gI-FJ5ukbsW3Hr1O8tO9FHXsTYstL9T9FWNejQlUEmFhIjNlnHRLQ74qkitTBpxF4LtHRDcn2i1yc5F70H1-0rcp3XZ71-s5vzTGp-M0kh-8mILjPK2lejMAhDIX3Tp1KWLaX1k8tmU8bA2e73vTQ__&Key-Pair-Id=K3Q589AYB0FA7R)

**Export to SNC** — Graph 뷰 툴바 우상단 **download** 버튼으로 두 단계 흐름을 시작합니다.

1. **Convert & Export to SNC** 다이얼로그 — 내보낼 변경 목록이 red `−` (이전 값) / green `+` (이후 값)로 표시됩니다. 변경이 없으면 *"No changes recorded — convert and save as SNC?"* 문구가 나옵니다. **Convert** 클릭.
2. 백그라운드 변환 진행.
3. **Conversion complete** 다이얼로그 — **Download**로 저장 위치 선택, 또는 **Close**.

변환 결과는 캐시되어 재편집이 없으면 재변환 없이 다시 다운로드할 수 있습니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/a55bfc8a-eaaa-41fb-85d7-38618aa24a85?response-content-type=image%2Fpng&Expires=1796581128&Signature=hrxaq2Emh8851ClL4HFr-mQDPoYi2sBdvzOQC9xcGyXW8ZFMbczA7H-o1qLGzy3m-5ekNRVPFtx5U9KeR9Q-77x7wUiCKvZQaUATcy96KITxFzWRhrJmFGX8Kopq4OXXdOqoDGq8wObdoPlE9MjdTX1FLtr9LA0f-~UiUX9ewKgLtDrnDTFwUgBhWajrXYB~b2ZqGX8i6w04Ry28wzIfdVholEUsy3kOqmJ5JAH1JBpuXQcEfUofyYmBED4~UksNkg014D6qfq3pt0DjMIxYtNYag8JAFs0CClhoECOHcz66TnfI60sT4~63uL2du4cjQFU2-T77LuwAY1LGAwNYLg__&Key-Pair-Id=K3Q589AYB0FA7R)

**Download 버튼 툴팁 의미**

| 툴팁 | 의미 |
|---|---|
| **Convert & download as SNC** | 내보낼 준비 완료 |
| **Converting to SNC…** | 변환 진행 중 |
| **No changes to export** | SNC 모델인데 편집이 없는 상태 |
| **No model available for download** | 모델이 로드되지 않음 |

> ONNX/CNNX 모델은 편집이 없어도 언제나 export 가능 (SNC로의 포맷 변환이 목적). SNC 모델은 편집이 있어야 export 대상이 됩니다.
> diff 모드에서는 각 pane(A/B)이 헤더에 자체 다운로드 버튼을 갖습니다.

---

##### Diff 모드 조작 (compare 시각화 후 UI)

**진입 방법**
- CLI: `eais debug --mode visualize --base_model_path <A> --compare_model_path <B>` — 왼쪽이 base(A), 오른쪽이 compare(B)
- UI: 단일 모델이 열린 상태에서 캔버스 상단 중앙의 **Diff On** 버튼을 클릭 → compare 모델 선택

**Diff Off** 버튼으로 종료합니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/d9079553-f4d1-4d37-bb33-a3530f057cfa?response-content-type=image%2Fpng&Expires=1796581128&Signature=N8XboxtHgr09EIxZ1lj2-qBRsAXuliuZGoZMsXRpth7aoIKIuoJK90Uow7sj1Du~Izb-JCWQmavc3B4Y0BsmV-Bpjoz0CD34OkCMVJrBbqd~g7wenh5H-2fL-EB86O1jx7QOT4zkF79R0q4v8IwRf1fdbzSSEsTmnwqlzO0qKaAm7jiJQJ7BISiX27POHDltTcQu8bnKcOdh3x-Ym-4LK6xe0b9vUsSjO6Q5eTO6Z-OP8YJT7NgjQsUJKbfQ6lCLKXjZRdFAS4-I9N-C18SdBE0Y0dLqHm8iu8xjqeOJxFXc2L1BTkNkwPQDHgNUh9hAHtkSoY5GyPUsWL9Nz-i36A__&Key-Pair-Id=K3Q589AYB0FA7R)

**Split 레이아웃** — 캔버스가 두 개의 리사이즈 가능한 pane으로 나뉩니다.

- 왼쪽: **A (baseline, 파란색)** / 오른쪽: **B (compare, 보라색)**
- divider를 드래그해 비율 조정
- 각 pane 헤더에는 파일명(및 `.encodings` / `.data` 동반 파일), 자체 download 버튼이 있음
- 각 pane마다 독립적인 selection inspector 존재
- Model Info 패널이 A vs B 비교로 확장되며 상단에 **Diff Summary** 표시

**노드 diff 하이라이트 링**

| 변경 | 색상 |
|---|---|
| Added | 초록 |
| Deleted | 빨강 |
| Modified | 주황 |

![image](https://soc-developer.semiconductor.samsung.com/ai1/ba381d91-3e82-4086-8eed-228b9b68660f?response-content-type=image%2Fpng&Expires=1796581128&Signature=P4~LwCHDPpyquveJ0Q2tvoHdqxfUxsAjXd9gicC3y5F553yee5pSFVAWU6NlRLtvckLOiwz7USmbMX3c9SdoJIEgogMbjkwLHCoSB7RgrGSHdyT87RoyH8KC8UYBrKEn8tqHNSDeRRG0fl1OY1E9wRkhGTtx1odRHDc1KtdWkIs1HQPznsx7TgZCYW4~kHRX6uCNCDklgPuBbY9L2EmLjZr0gDXTePYnta2gLqo5IHA4lC1O550kKP-SQ37TwFy40qyNPR1Y17-7XrMN-pyrh2vIWJj9j~mrcRHQ~CJHlPVgJxzWutEcb0qbCFmcbJENMfGSmmx15beqTRcDA1TWzA__&Key-Pair-Id=K3Q589AYB0FA7R)

**Floating diff 툴바** — diff 모드에서 캔버스 위에 떠 있는 작은 툴바. **⋮⋮ handle**을 잡고 위치 이동 가능.

- **Sync** — A/B 팬/줌 동기화 토글 (*"Sync ON — click to disable"* / *"Sync OFF — click to enable"*)
- **A → B** — A에서 선택한 노드와 매칭되는 B 노드로 점프해 양쪽 중앙 정렬. 매칭이 있을 때만 활성화
- **A ← B** — 그 반대 방향
- **Diff Off** — diff 모드 종료

> 노드는 **name**을 기준으로 매칭됩니다. 색상 규칙과 예시 스크린샷은 [위의 Diff 색상 가이드](#diff-색상-가이드) 참고.

---

##### Accuracy 뷰 (validator 결과)

view switcher에서 **Accuracy**로 전환하면 layer-by-layer 정확도 분석을 볼 수 있습니다. validator 파일이 없으면 아래 empty 화면이 표시됩니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/c1741e92-4e44-4db6-9613-6006f3ea8ccf?response-content-type=image%2Fpng&Expires=1796581128&Signature=LrRLpNKpKk-AG-a70iKiOsoaKhDgmX1Q8MC80CTdhDnOWERLeX230J3o9wL12BSwnurJxKP0uk584u78tWf0IG4ggZoKJWq5r8j04BzvZyz0HCyH2EEKYcdVgPqbgH1m3jNmJjpunCSqFQ~THVi0prcgTw9kjyU8M6a5OkaYEQWeYuiEbtBs1McE4TYKVWLfXA5s69sXW8ajfRDyKMD-GBb-hwS4SeZiX6r2sUCjgt0AWdiik6yIcVdeTiNw6ZYjYzZtGhktoZaGtc0PAJza7Z39R7~G8LslUyJUvIacxJQMTZ77BObEJ-m86J2mxm5weG~0uNFlSdseMsmNWySzow__&Key-Pair-Id=K3Q589AYB0FA7R)

**validator 파일 로딩**
- UI: 드래그앤드롭 또는 파일 선택으로 **`.xlsx`** / **`.csv`** 로드 (다른 확장자는 *"Unsupported file format …"* 로 거부됨)
- CLI: `--accuracy_result_path`로 preload (모델 없이 단독, 모델과 함께, diff 모드와 함께 모두 지원). 로딩 중 *"Loading accuracy data…"* 표시.

로드되면 상단 **file meta bar**에 dataset 정보와 **Replace**(파일 교체) 버튼이 표시됩니다.

**네 개의 하위 탭**

| 탭 | 내용 |
|---|---|
| **Pipeline Flow** | 파이프라인 단계별·연산별 정확도 |
| **Dashboard** | op 타입별 평균 SNR, op 타입별 실패율, 레이어별 SNR 라인 차트. 다중 pair 데이터셋의 경우 pair별 하위 탭 제공 |
| **Layer-wise Analysis** | 레이어 단위 상세 분석 (tensor 단위 metric 포함) |
| **Summary Report** | 전체 tensor에 대한 통계 요약 |

![image](https://soc-developer.semiconductor.samsung.com/ai1/e0e64be4-a397-4e30-919a-71e3e636f6e7?response-content-type=image%2Fpng&Expires=1796581128&Signature=RxK~ngl-F~Wgu2xm1nn~SiP8Eq7XpHO53Fs61vgcLb5H1tqn9naQ633UX~40Th4hDN0ajxHIngndkberhVjGNSRP~C7SKlPMKuTomoapiCc2UYfHHCkTN8qpnHU9cJcJMSr7VuR44LJvS-MTrfuTMVj1jf~~hYP0gfEswSdsyd1UoLq96YKX37uZRz31Um4bsOj50QZB46IGnAka9yad4h1CIJ9Y-LGcgT7yalHc4dxwOvMuMGuFMcp-TwiCEgAHj-146vvPi21kAt5eA8lHhjwvqAwhyiXT1Yz5c9rzD2yUCPYI6X0vVVW715V7XTJeiyflHpsqkywwa5QHsu4LNQ__&Key-Pair-Id=K3Q589AYB0FA7R)

###### Pipeline Flow 탭

파이프라인 단계 간 정확도 흐름을 노드/화살표로 시각화합니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/c4459454-9b8b-4d6e-b878-0c571da8a832?response-content-type=image%2Fpng&Expires=1796581128&Signature=Kt-5SbvyMEEH0dwT1d-9FokE-zSUryrjbtQgjYFfZ5Z0cOOwkBP4NWttwOUSHPO~1tXTu0~KVuVh990c5nDiSBfDRGIvkpI4MNZLPdwCF9yvsdT6pKfKjmHes-tRqMADcP0lGgmNaW2y1v2yYas2hSmR~YepntMJ9TH-Z7F6VtQ5pSBd8~nYd4D8nh6BZVK6-kn2jjXYtaRrhGbgwN4xXHoEbXQckA91HPY893-WnQvW-9pG8MD-1IdlkDLb8vK1UpQts2Cr~UsMFYjszGxo-OTp4J~0dHIjlUz9vG8vXzDSAOCTnenDvmlwE0dY-FLO~KcsGpY4UIWRRPAhkkDk1g__&Key-Pair-Id=K3Q589AYB0FA7R)

![image](https://soc-developer.semiconductor.samsung.com/ai1/1a328420-9592-4e28-87e8-f446f302c142?response-content-type=image%2Fpng&Expires=1796581128&Signature=XzA-MvUI6X-7DgkP94dQ5EVzx61vDgWLnph194SUWlYPXa263u5lkIzA8KDisk-XY4wYkqRrCBwYoa7T6eeYvQx19oeIZOWhOENoM2PbfB3mZLp-P-6KMxUjDLprBSm47WvRwIqgHB1nhy5e7OHhNBRrrU45srsxh0kkVhn8P-4BCo~oddi0d9Ly6ifluErFDHk4GvUccwLorY6hN2ioqJgEZq5ljUKs06b8luHC08zUFOrPVz8rP5mQrHVFecGdHPYMW6EpVg55J03-jrdIgltglcpvpGjz7zcrirfzuR35Hre-RNXHbVt3gO7V5v-DwgYjPljh5Q-L4BgvFbAJBw__&Key-Pair-Id=K3Q589AYB0FA7R)

###### Dashboard 탭

op 타입별 평균 SNR, 실패율, 레이어별 SNR 라인 차트를 통해 전체 정확도 현황을 한눈에 확인합니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/483cd587-5467-44cb-877a-4575dff3ca32?response-content-type=image%2Fpng&Expires=1796581128&Signature=DjSP-gF2EWm8gd-e709Yt9Pdsz0YoEcYFmXc4IiThmh8yTGZsIF0dR2i1jPL1EeiRlzLL3ZqrpE3oeN0u3jNY-sVZJ-se4WwnTA7LWascCeTc8u1L5Ff53anEI~Ie~hNFU-tTmOO8Y9BlPQrOP~KXkFvzERc6UR4rJgUgf3UX9HEzT7~VvkY2Kh7G1s~QLn4eQg8qVvsHKEHreIY~R2ypPAn0bW7oxT-qUv1eGs0RDr7ExaYaCCLuKJ5e7H-LLAzjazZMiSfeT320SUUp4DyaqrclGx9YHfZfhlX2M9LrT1jzLHNs61WJha7R2-Az8S7oA~FSVCVA9GJeusjy6kt3Q__&Key-Pair-Id=K3Q589AYB0FA7R)

![image](https://soc-developer.semiconductor.samsung.com/ai1/2ef0bff6-a948-43f5-bd30-d045040492fa?response-content-type=image%2Fpng&Expires=1796581128&Signature=bh8DQK6BY3jNkH1GRiujI5PiWY3jL7K-hh8ah68rpF3WzreDdvgnHen7whW3JlgnypGL4JtLsESp8KPeQPpOMvxBKjvdt1O~ID9EKlMispL2uI81REmKXmofZCJ~6NF5w9Gy9mO5VhfMzpbXC5-ztuaCsIZUKJwyUcRu1vDnYWc94Ko3EFcz4sE0P61nQdGUU8IN-4pXlEv4R8s9Q7yu7jMB5LUJQUGvLJAcVfH7s7psgrQ5jGFg5jmSRMXqcreSNCOVn3CLHnARZuHp5k65MOZzT9g2bwzZKrB05RczS7Kx8FXTL7Ev6BAdqm-~zhSn3oyxPJj8DOOryK2HO~C~7w__&Key-Pair-Id=K3Q589AYB0FA7R)

###### Layer-wise Analysis 탭

레이어 단위로 tensor metric을 정렬·필터링하며 상세 분석할 수 있습니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/eafdab66-e730-44c8-8d34-798646b1b491?response-content-type=image%2Fpng&Expires=1796581128&Signature=R8nRw1dBVd04Dh2EtVl0e7Wr-Bs5ZP9XhLH-v0R7fd4z0u2cTjEHBcn3lUxIXm7QSBVdRl3yn-zi~w4ypjF8iuXAns~eraLIj~nRSVEArQuPz9rUA2QZZ6CWcj8JINu29DKnK0zI4eaQ9iw3MYEa0Ws7OB~S1tL3VJbfQaeVcx4pio2Ovxw3r7-fcOPfli5A2JfKbTWPnOwPc41HzMyvtZVc2jHpKKBVRBfxRehAZry4xLcNGwUSETTIADeYDchEeXdWg6I4XrOPd9tgDgIi6U0ouw0ECgI-WxQm3ES-DH1ymWCwcmtoCi8nOg98bzB1lwYfaBklBG-IHFQMHkI2mw__&Key-Pair-Id=K3Q589AYB0FA7R)

###### Summary Report 탭

전체 tensor에 대한 통계 요약을 제공합니다.

![image](https://soc-developer.semiconductor.samsung.com/ai1/0985fbb9-f9dc-41e0-8095-f2340a12ffbd?response-content-type=image%2Fpng&Expires=1796581128&Signature=EOpNeG2SeAIGHMMG~CrXDzHo5kdRYp3QMKN0RR~NvvC8jKSxbFEM6zAVOc7KqwwjLtJ3qru3x3jGW9-kmOeKD7ob7XS3Kg4rOK96qFYdrXZSp0QlvmGLThH2MPiulodRe9oVsooEg1NUhdEv4pN-mVeBiVtgJSxdFtlx0836Etnyj9HHPupbgiyE-qZ3HEGTFCgcz~Tv-PIUr5-ARY6AvJ9aup2jDAwp6RCOTWkFq0dzKHLtv2N9z3iWYMLZA1WpE~k2t9xgLyDVmiqWzRSdzuXrmckZZTcwj~E5SqAB1vA1AtsoUvBOgscmti-5VrpBLYMJpJvfXvyGYakCaJPT6A__&Key-Pair-Id=K3Q589AYB0FA7R)

**SNR 지표** — 정확도는 레이어별 **SNR (dB)** 로 측정됩니다. 값이 높을수록 양자화·컴파일 후 결과가 기준 모델에 가깝습니다. 각 레이어의 reference/target 출력이 매칭되어 SNR이 계산되며, 위 차트들의 소스가 됩니다.

> Tensor 값 분포는 Graph 뷰의 [Tensor 분포 (히스토그램)](#tensor-분포-히스토그램) 항목에서도 확인할 수 있어, 양자화 오차의 원인을 눈으로 짚어볼 수 있습니다.

---

### `--mode all`

#### 기능

`--mode accuracy`를 먼저 실행한 뒤, 완료되면 `--mode visualize`를 이어서 실행합니다.
한 번의 명령으로 정확도 검증과 브라우저 시각화를 순서대로 수행할 수 있습니다.

#### CLI 예시

**accuracy 검증 + SNC 모델 시각화 — 정확도 결과와 그래프를 한 번에.**
```bash
eais debug --w ./hrnet_pose \
  --mode all \
  --base_model_path ./Converter_result/HW_output_new_snc_9.6.26.30.snc
```

**accuracy 검증 + 모델 + 결과 preload — 시각화 URL에 `?model=&validator=` 파라미터가 모두 포함.**
```bash
eais debug --w ./hrnet_pose \
  --mode all \
  --base_model_path ./Converter_result/HW_output_new_snc_9.6.26.30.snc \
  --accuracy_result_path ./Debug_result/accuracy_validation_results/accuracy_comparison.xlsx
```

**accuracy 검증 + compare diff — 정확도 결과를 확인하면서 두 모델을 비교.**
```bash
eais debug --w ./hrnet_pose \
  --mode all \
  --base_model_path ./Converter_result/2_mixed_precision_quantization/output.onnx \
  --base_encodings_path ./Converter_result/2_mixed_precision_quantization/output.encodings \
  --compare_model_path ./Converter_result/HW_output_new_snc_9.7.9.30.snc
```

- `--mode visualize`와 동일하게 `--base_model_path`와 `--accuracy_result_path` 중 하나 이상은 반드시 지정해야 합니다.
- 산출물·결과 해석·시각화 케이스는 각각 [`--mode accuracy`](#--mode-accuracy-기본), [`--mode visualize`](#--mode-visualize) 섹션을 참고하세요.

---

## accuracy 검증 결과 해석

### testvector란?

**testvector**는 `eais conversion`의 각 변환 단계에서 저장되는 출력 텐서 데이터(`.npy` 파일)입니다.
변환 완료 후 `0_INPUT`(원본 모델 출력), `1_converter`, `2_optimizer`, `3_quantizer`, `4_specifier` 각 단계의 출력이 testvector로 저장되며, `eais debug`는 이를 불러와 단계 간 정확도 지표를 계산합니다.

---

### 검증 방식

변환 파이프라인의 각 단계 출력을 원본 모델(`0_INPUT`) 및 인접 단계와 pair로 비교합니다.
`depth=full`(기본값) 일 때 모든 단계 간 조합이 비교됩니다.

| pair 예시 | 의미 |
|---|---|
| `0_INPUT VS 1_converter` | 원본 ONNX vs CNNX 변환 후 |
| `0_INPUT VS 4_specifier` | 원본 ONNX vs 최종 SNC |
| `3_quantizer VS 4_specifier` | 양자화 후 vs SNC 변환 후 |

---

### 지표 (Metrics)

| 지표 | 의미 | PASS 조건 |
|---|---|---|
| **SNR** | 신호 대비 오차의 비율 (dB). 높을수록 원본과 유사 | 값 ≥ threshold |
| **PSNR** | 최대 신호값 기준 오차 비율 (dB). 높을수록 정밀 | 값 ≥ threshold |
| **COSSIM** | 두 벡터 간의 cosine 유사도. 1에 가까울수록 방향이 동일 | 값 ≥ threshold |
| **MAX_ABS_DIFF** | 두 텐서 간 최대 절대 오차. 작을수록 수치 오차가 적음 | 값 ≤ threshold |
| **MSE** | 두 텐서 간 평균 제곱 오차. 작을수록 전반적인 오차가 적음 | 값 ≤ threshold |

> [!NOTE]
> 지표별 threshold는 `Config/debug.yaml`의 `thresholds`에서 `metrics`와 1:1로 설정합니다.
> 모든 지표가 threshold를 만족하면 **PASS**, 하나라도 미달이면 **FAIL**.

---

### PASS/FAIL 판정

`validation_report.json`의 `status` 필드로 전체 결과를 확인할 수 있습니다.

```json
{
  "results": {
    "AccuracyValidator": {
      "status": "FAILED",
      "fail_list": [
        {
          "name": "(base_edge_name: /layer1/0/conv3/Conv_output_0, ...)",
          "code": "UnderMetricThreshold",
          "info": {
            "SNR": [26.29, "MetricStatus.FAIL"],
            "PSNR": [59.38, "MetricStatus.PASS"]
          }
        }
      ]
    }
  }
}
```

- `status: PASSED` — 모든 레이어가 threshold를 통과
- `status: FAILED` — 하나 이상의 레이어에서 threshold 미달
- `fail_list` — FAIL이 발생한 레이어 목록과 각 지표 값

---

### SNR 결과 해석 기준

precision별 통과 기준은 상대적이며, 아래는 권장 기준입니다. `debug.yaml` 기본 threshold는 SNR·PSNR 모두 **10dB**, COSSIM **0.5**입니다.

| `precision` | 권장 통과 기준 (SNR) |
|---|---|
| `FP16` | 35 dB 이상 |
| `A16W8` | 30 dB 이상 |
| `A8W8` | 20 dB 이상 |

**SNR이 낮을 경우 시도할 수 있는 조치:**

1. `calibration_method`를 `minmax` → `percentile` → `histogram_enhanced` 순으로 변경
2. `precision`을 `A8W8` → `A16W8` → `FP16` 순으로 상향
3. 실제 대표 데이터셋으로 `dbgen_spec.yaml` 재작성 후 `generation` → `conversion` 재실행
4. `advanced_quantization_algorithm: smoothquant` 적용 검토

---

### Warning 메시지 해석

| Warning | 의미 | PASS/FAIL 영향 |
|---|---|---|
| `Unmatched tensors` | 두 단계 간 tensor 이름이 일치하지 않아 비교에서 제외된 레이어 존재 (optimizer가 레이어 구조 변경 시 발생) | 없음 |
| `Shape mismatch ... ReshapeRule` | 출력 shape이 달라 자동으로 permutation을 탐색해 매칭 시도 (SNC의 배치 차원 제거 등) | 없음 (매칭 성공 시) |

---

## accuracy_comparison_csv 해석 가이드

`accuracy_comparison_csv/` 디렉토리 안에는 비교 pair별 CSV 파일이 생성됩니다.
예: `0_INPUT VS 4_specifier.csv` — 원본 모델(base)과 최종 SNC(target)의 레이어별 정확도 비교 결과.

---

### 파일명 읽는 법: base VS target

```
0_INPUT VS 4_specifier.csv
  └── base ──┘  └── target ──┘
```

- **VS 왼쪽** = **base** (기준 단계, 비교의 참조값)
- **VS 오른쪽** = **target** (비교 대상 단계)
- `0_INPUT VS 4_specifier` 는 "원본 ONNX를 기준으로 최종 SNC 결과를 비교한다"는 의미입니다.

---

### 행(Row) 순서

CSV의 행은 다음 순서로 정렬됩니다:

1. **output** — 모델의 최종 출력 tensor
2. **input** — 모델의 입력 tensor
3. **중간 레이어** — 그래프 노드 순서(topological order)대로 나열

즉, output → input → graph 순서로 나타납니다.

---

### 컬럼 설명

| 컬럼 | 설명 |
|---|---|
| `match_status` | 두 단계 간 tensor 매칭 결과. `matched`: 양쪽 단계 모두에 대응하는 tensor가 존재. `unmatched_base`: base 단계에만 존재(target 없음). `unmatched_target`: target 단계에만 존재(base 없음) |
| `base_name` | base 단계 tensor 이름 (매칭에 사용된 key) |
| `target_name` | target 단계 tensor 이름 (`unmatched_base`이면 빈 값) |
| `SNR` | 신호 대 잡음비 (dB). 값이 높을수록 원본과 유사. `(값, 'PASS'/'FAIL')` 형식으로 저장 |
| `PSNR` | 최대 신호값 기준 오차 비율 (dB). 높을수록 정밀. `(값, 'PASS'/'FAIL')` 형식 |
| `COSSIM` | cosine 유사도. 1에 가까울수록 두 벡터의 방향이 동일. `(값, 'PASS'/'FAIL')` 형식 |
| `base_shape` | base tensor의 **원본 shape** (저장된 `.npy` 파일 그대로의 shape) |
| `target_shape` | target tensor의 **원본 shape** |
| `base_reshape` | 정확도 비교에 **실제 사용된** base tensor의 shape (reshape rule 적용 후) |
| `target_reshape` | 정확도 비교에 **실제 사용된** target tensor의 shape (reshape rule 적용 후) |
| `best_perm` | reshape rule이 target tensor에 적용한 **축 순열(permutation)**. `(0, 1, 2)`는 순열 없이 그대로 사용했음을 의미 |
| `base_min` / `base_max` | base tensor의 최솟값 / 최댓값 |
| `target_min` / `target_max` | target tensor의 최솟값 / 최댓값 |
| `base_path` | base tensor `.npy` 파일 경로 |
| `target_path` | target tensor `.npy` 파일 경로 |
| `base_layer_name` | base 단계에서 해당 tensor를 출력하는 레이어 이름 |
| `target_layer_name` | target 단계에서 해당 tensor를 출력하는 레이어 이름 |
| `base_layer_optype` | base 레이어의 연산 타입 (예: `Conv`, `Relu`, `Input`, `Output`) |
| `target_layer_optype` | target 레이어의 연산 타입 |

---

### `shape` vs `reshape` 차이

| 컬럼 | 의미 |
|---|---|
| `base_shape` / `target_shape` | `.npy` 파일에 저장된 **원본 shape** |
| `base_reshape` / `target_reshape` | reshape rule 적용 후 **실제 비교에 사용된 shape** |

두 tensor를 비교하기 전에 **reshape rule**이 다음 처리를 수행합니다:

1. **크기 1인 차원 제거(squeeze)**: 양쪽 tensor에서 불필요한 배치 차원을 제거합니다.
   예) `base_shape=(1, 17, 64, 48)` → `base_reshape=(17, 64, 48)`
2. **축 순열 탐색**: target tensor의 모든 축 조합을 시도하여 base와 SNR이 최대가 되는 배열을 선택합니다. 이 결과가 `best_perm`에 기록됩니다.
3. **shape 맞추기**: 선택된 순열로 target을 base의 shape에 맞게 재배열합니다.

결과적으로 `shape != reshape`인 경우는 배치 차원(`1`)이 제거된 것이고,
`best_perm`이 `(0, 1, 2)`가 아닌 경우는 축 순열이 추가로 적용된 것입니다.

---

## Reference

### debug.yaml — eais debug 파라미터 통합 관리

`<workspace>/Config/debug.yaml` 하나에서 `eais debug`의 모든 파라미터(실행 모드, 시각화, 비교, accuracy 검증)를 관리합니다. CLI 옵션이 지정되면 yaml 값을 덮어씁니다.

```yaml
debug:
    # Execution mode
    mode: accuracy                                     # ['accuracy', 'visualize', 'all']

    # Browser server (visualize / all)
    host: None                                         # [str]: [visualize/all, required] 브라우저 URL에 표시될 IP/hostname (예: 127.0.0.1)
    port: None                                         # [int]: [visualize/all, required] 브라우저 URL에 표시될 포트 (예: 40090)

    # Base model (visualize / all)
    base_model_path: None                              # [path]: [visualize/all] 브라우저에서 열 기준 모델 (.snc / .onnx). accuracy_result_path 없으면 필수
    base_encodings_path: None                          # [path]: [visualize/all, optional] 기준 모델 양자화 encodings (.encodings)
    base_external_data_path: None                      # [path]: [visualize/all, optional] 2GB 초과 ONNX 기준 모델의 external data
    base_activation_path: None                         # [path]: [visualize/all, optional] base 모델의 레이어별 activation .npy 디렉토리 (eais debug --mode accuracy 결과의 <단계>/tvs/)

    # Compare model (visualize / all, optional diff)
    compare_model_path: None                           # [path]: [visualize/all, optional] base와 diff 비교할 대상 모델
    compare_encodings_path: None                       # [path]: [visualize/all, optional] 비교 모델 encodings
    compare_external_data_path: None                   # [path]: [visualize/all, optional] 비교 모델 external data
    compare_activation_path: None                      # [path]: [visualize/all, optional] compare 모델의 레이어별 activation .npy 디렉토리

    # Accuracy artifacts
    accuracy_result_path: None                         # [path]: [visualize/all, optional] 브라우저에 함께 로드할 accuracy 결과 (.xlsx / .csv)
    pipeline_artifacts: Debug_result/pipeline_artifacts.json  # [path]: eais conversion 산출물 경로

    # Accuracy validation parameters (accuracy / all)
    depth: full                                        # [endpoints, full]: endpoints=최종 단계만 검증; full=모든 단계 간 조합
    metrics:                                           # [list[str]]: SNR, PSNR, COSSIM, MAX_ABS_DIFF, MSE
        - SNR
        - PSNR
        - COSSIM
    thresholds:                                        # [list[number]]: metrics 와 1:1 대응하는 PASS 기준값
        - 10.0
        - 10.0
        - 0.5
    snc_input_name_mapping: exactly                    # [exactly, postfix]: input data 폴더명과 SNC 입력 이름 매칭 방식
    testvector_name_mapping: exactly                   # [exactly, postfix]: 단계 간 testvector 이름 매칭 방식
    save_layerwise_output: true                        # [bool]: 레이어별 출력값을 .npy로 저장
```

---

### 출력 파일 구조

```
Debug_result/
├── pipeline_artifacts.json          # conversion 단계 정보 (conversion 시 생성)
├── debug_report.json                # accuracy 검증 요약
└── accuracy_validation_results/
    ├── accuracy_comparison.xlsx     # 모든 모듈 산출물 간 비교 결과를 하나의 Excel 파일에 통합 (시트별로 비교 pair 구분)
    ├── accuracy_comparison_csv/     # xlsx와 동일한 내용을 비교 pair별로 분리한 CSV 파일 모음
    │   ├── 0_INPUT VS 1_converter.csv
    │   ├── 0_INPUT VS 2_optimizer.csv
    │   └── ...
    ├── parameters.txt               # 검증에 사용된 파라미터 정보
    ├── validation_report.json       # 레이어별 상세 결과 (PASS/FAIL, 지표 값)
    ├── 0_INPUT/
    │   ├── test_vector.json
    │   └── tvs/                     # save_layerwise_output: true 일 때 저장되는 단계별 feature map (.npy)
    ├── 1_converter/
    │   ├── test_vector.json
    │   └── tvs/
    ├── 2_optimizer/
    │   ├── test_vector.json
    │   └── tvs/
    ├── 3_quantizer/
    │   ├── test_vector.json
    │   └── tvs/
    └── 4_specifier/
        ├── test_vector.json
        └── tvs/
```

---

## 트러블슈팅

### 1. `FileNotFoundError: pipeline_artifacts.json not found`

`--mode accuracy` / `--mode all` 실행 시 `Debug_result/pipeline_artifacts.json`이 없으면 발생합니다.

```
FileNotFoundError: pipeline_artifacts.json not found:
  /home/user/eais-projects/01-5_model/Debug_result/pipeline_artifacts.json.
To generate it, run 'eais conversion' again in the workspace directory.
  e.g.) eais conversion --w <workspace_path>
```

**원인:** `eais conversion`이 실행되지 않았거나 중간에 실패한 경우 생성되지 않습니다.

**해결:** `eais conversion`을 정상 완료한 뒤 `eais debug`를 다시 실행합니다.
```bash
eais conversion --w <workspace_path>
eais debug --w <workspace_path>
```

---

### 2. `[ERROR] base model file not found: <path>`

`--mode visualize`에서 `--base_model_path`로 지정한 파일이 존재하지 않을 때 발생합니다.

**해결:** 실제 존재하는 모델 파일 경로를 지정합니다.
```bash
ls Converter_result/HW_*.snc      # 실제 파일명 확인
eais debug --w <workspace> --mode visualize \
  --base_model_path ./Converter_result/HW_<model>_<version>.snc \
  --host 127.0.0.1 --port 40090
```

---

### 3. `Error: Invalid value for '--mode'`

`--mode`에 허용되지 않는 값을 전달했을 때 발생합니다.

**해결:** `accuracy`, `visualize`, `all` 중 하나를 사용합니다.

---

### 4. `--mode visualize` / `--mode all` 필수 옵션 누락

`--mode visualize` 또는 `--mode all` 실행 시 `--base_model_path`와 `--accuracy_result_path` 중 어느 것도 지정하지 않으면 발생합니다.

```bash
eais debug --w ./hrnet_pose \
  --mode visualize
# Error: --mode visualize requires at least one of: --base_model_path, --accuracy_result_path
```

**해결:** `--base_model_path`와 `--accuracy_result_path` 중 하나 이상은 반드시 지정합니다. `--compare_model_path`를 사용할 경우 `--base_model_path`도 함께 지정해야 합니다.

```bash
eais debug --w ./hrnet_pose \
  --mode visualize \
  --base_model_path ./Converter_result/HW_output_new_snc_9.6.26.30.snc
```
