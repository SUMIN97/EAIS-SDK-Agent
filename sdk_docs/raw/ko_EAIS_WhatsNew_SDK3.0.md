# Exynos AI Studio (EAIS) SDK 3.0 업데이트 안내

SDK 2.5대비 SDK 3.0에서 업그레이드된 점들을 방법을 안내합니다.
기존에 SDK 2.5를 사용하셨다면, 이 문서를 참고해 작업 환경을 업데이트해 주세요.

---

## 목차

- [워크스페이스(workspace)란?](#워크스페이스workspace란)
1. [SDK2.5 대비 변경사항](#1-sdk25-대비-변경사항)
2. [새로 추가된 기능](#2-새로-추가된-기능)
   - [2-1. eais conversion --help](#2-1-eais-conversion---help에서-설정-가능한-파라미터-목록-확인-가능)
   - [2-2. Converter_result/ 폴더 구조 변경](#2-2-converter_result-폴더-구조-변경)
   - [2-3. ModelValidator 추가](#2-3-변환-단계별-유효성-검사modelvalidator-추가)
   - [2-4. --eht / --elt 옵션 추가](#2-4-변환-구간을-선택할-수-있는---eht----elt-옵션-추가)
   - [2-5. MXINT8 precision 추가](#2-5-mxint8-precision-추가)
   - [2-6. eais debug 추가](#2-6-변환-정확도모델-그래프를-단계별로-확인하는-eais-debug-추가)
3. [기본값 변경](#3-기본값-변경)

---

## 워크스페이스(workspace)란?

EAIS는 **워크스페이스(workspace)** 단위로 동작합니다. 변환할 모델 파일(`.onnx` 또는 `.tflite`)이 들어 있는 폴더로, 폴더 이름과 모델 파일 이름이 반드시 일치해야 합니다. `eais init`을 실행하면 워크스페이스 안에 `<model_name>.yaml`과 `Config/` 폴더가 생성되며, 이후 CLI 명령어는 이 워크스페이스를 기준으로 conversion, compile, profiling 등의 산출물을 저장합니다. 1개의 모델은 1개의 워크스페이스를 가지는 구조이며, 워크스페이스 폴더를 기준으로 각 CLI 명령어에서 실행된 산출물이 저장됩니다.

> 워크스페이스 준비 규칙, `Config/` 하위 yaml 파일 전체 목록과 각 파일 역할은 [EAIS_User_Guide.md → §2 워크스페이스 구조](documentation/sdk-3.0/eais-user-guide#2-워크스페이스-구조)를 참고하세요.

---

## 1. SDK2.5 대비 변경사항

### 1-1. yaml 설정 파일 구조 개편 — 기존 워크스페이스는 반드시 재초기화해야 합니다

> [!CAUTION]
> SDK 3.0은 `<model_name>.yaml` 및 `Config/` 하위 yaml 파일 구성 및 내용이 SDK 2.5와 다릅니다.
> SDK 2.5에서 `eais init`으로 생성된 yaml 파일들이 워크스페이스에 존재시 충돌이 발생할 수 있으므로, **반드시 삭제한 후 `eais init`을 다시 실행해 주세요.**
> SDK 2.5에서 생성된 파일들을 그대로 사용시, 파라미터가 인식되지 않거나 오류가 발생합니다.

특히 `<model_name>.yaml`의 `converter` 섹션 구조가 전면 개편되었습니다.

**SDK 2.5 구조 (더 이상 지원되지 않음)**
```yaml
converter:
  mode: legacy
  quantize:
    precision_weight: 8
    precision_activation: 8
  specify:
    input_dtype: float32
    output_dtype: float32
    graph_opt: common
    tv_input: Config/DATA/database.h5
  optimizer:
    ...
  runtime:
    ...
```

**SDK 3.0 구조**
```yaml
converter:
  precision: A8W8
  input_dtype: float32
  output_dtype: float32
  graph_opt: common
  # 고급 옵션은 Config/conversion_expert.yaml 에서 설정
```

변경 포인트는 다음과 같습니다.

| SDK 2.5 | SDK 3.0 | 설명 |
|---|---|---|
| `mode: legacy` | `mode: pro` | pro 모드를 기본 모드로 사용 |
| `quantize.precision_weight` + `precision_activation` | `precision: A8W8` | 두 값을 하나의 프로파일로 통합 |
| `specify.input_dtype` | `input_dtype` | 중첩 구조 → 플랫 구조로 단순화 |
| `specify.output_dtype` | `output_dtype` | 동일 |
| `specify.graph_opt` | `graph_opt` | 동일 |
| `specify.tv_input` | 자동 설정 | generation 산출물 경로를 자동으로 참조 |
| `optimizer.*`, `runtime.*` | `Config/conversion_expert.yaml`로 이동 | 고급 파라미터 분리 |

> [!IMPORTANT]
> 파라미터는 사용 레벨에 따라 두 파일로 나뉩니다.
>
> - **`<model_name>.yaml`**: 모델 변환 시 일반적으로 조정하는 파라미터 (`precision`, `calibration_method`, `input_dtype` 등)
> - **`Config/conversion_expert.yaml`**: 최적화, 양자화 등과 관련된 고급 파라미터. `eais init` 시 자동 생성되며 특별한 경우에만 수정합니다.
>

---

### 1-2. 캘리브레이션 데이터 형식이 `.h5`에서 `.npy`로 변경되어 데이터를 재생성해야 합니다

SDK 2.5에서는 `eais generation`이 `.h5` 파일을 생성했지만, SDK 3.0부터는 `.npy` 파일로 변경되었습니다.
> [!WARNING]
> 기존 `.h5` 파일은 SDK 3.0의 `eais conversion`에서 사용할 수 없습니다. SDK 3.0 컨테이너에서 `eais generation`을 다시 실행해야 합니다.

**SDK 3.0의 출력 구조**
```
Config/DATA/
├── database.txt
├── database.json
└── input_data/
    ├── input_folder_mapping.json
    └── <입력 이름>/
        ├── database_0000.npy
        ├── database_0001.npy
        └── ...
```

#### `Config/DATA/dbgen_spec.yaml` 변경점

SDK 2.5에서 사용하던 `raw_shape`, `raw_order` 필드가 SDK 3.0에서는 `shape`, `order`로 통합되었습니다.

> `dbgen_spec.yaml` 필드 설명, 다중 입력·랜덤 데이터 예시, path 상대경로 해석 규칙 등 작성법 전반은 [EAIS_User_Guide.md → Step 2 → dbgen_spec.yaml 작성 방법](documentation/sdk-3.0/eais-user-guide#dbgen_specyaml-작성-방법)을 참고하세요.

---

## 2. 새로 추가된 기능



### 2-1. `eais conversion --help`에서 설정 가능한 파라미터 목록 확인 가능

SDK 3.0부터 `eais conversion --help`를 실행하면 `<model_name>.yaml`의 `converter` 섹션에 정의된 파라미터 목록과 설명이 함께 출력됩니다.

```bash
eais conversion --help
```

출력 예시 (일부):
```
[GENERAL]
--mode  <STR>  [Default: 'pro']  {legacy, pro, eht, elt, gen-ai-eht, gen-ai-elt, gen-ai}

[EHT MIXED PRECISION]
--mixed_precision_type    <STR>   [Default: 'manual']  {manual, auto}
--mixed_precision_layers  <DICT>  [Default: '{}']
--mixed_precision_ops     <DICT>  [Default: '{}']

[EHT CALIBRATION]
--calibration_args  <DICT>  [Default: '{"seed": 42, "samples": 1}']

[EHT BLOCKWISE QUANTIZATION]
--enable_blockwise_quantization  <BOOL>  [Default: False]
--blockwise_block_size           <INT>   [Default: 64]
--blockwise_bitwidth             <INT>   [Default: 4]
...
```

전체 출력은 GENERAL / EHT CONVERTER / EHT MIXED PRECISION / EHT CALIBRATION / EHT BLOCKWISE QUANTIZATION / EHT AUTOMATIC MIXED PRECISION / EHT ADVANCED ALGORITHMS / EHT WEIGHT HANDLING / EHT DEBUGGING AND OTHERS / EHT GEN AI OPTIMIZE ARGS / ELT / ELT HWOP SPECIFIER 등 12개 섹션으로 구성됩니다.

yaml 파일을 직접 열지 않고도 `--help`에서 파라미터 이름·허용 값·기본값을 바로 확인할 수 있고, yaml 수정 없이 CLI에서 파라미터를 오버라이드할 수도 있습니다.

```bash
eais conversion --w <workspace> --mode pro --mixed_precision_type auto
```

> `<model_name>.yaml` 각 파라미터의 기본값과 의미(precision, calibration_method, graph_opt 등)는 [EAIS_User_Guide.md → `<model_name>.yaml` 파라미터 가이드](documentation/sdk-3.0/eais-user-guide#model_nameyaml-파라미터-가이드)를 참고하세요.

---

### 2-2. `Converter_result/` 폴더 구조 변경

`eais conversion` 실행 후 워크스페이스에 생성되는 `Converter_result/` 폴더 구조가 변경되었습니다.
SDK 2.5에서는 각 변환 단계 산출물이 개별 폴더(`cnnx/`, `optimized/`, `quantized/`, `quantized_mp/`)에 흩어져 있었지만, SDK 3.0에서는 파이프라인 순서에 맞춰 `0_onnx_to_cnnx/` → `1_optimize/` → `2_mixed_precision_quantization/` 로 번호가 붙은 폴더로 통합되어 단계 흐름이 명확해졌습니다.

**SDK 2.5 구조**
```
Converter_result/
├── cnnx/                    ← Converter 산출물
│   ├── output.onnx
│   └── output.encodings
├── optimized/               ← Optimizer 산출물
│   ├── output.onnx
│   ├── output.encodings
│   └── 4dim/
├── quantized/               ← Quantizer 산출물
│   ├── <model>.onnx
│   └── <model>.encodings
├── quantized_mp/            ← Mixed-precision quantizer 산출물
│   ├── output.onnx
│   └── output.encodings
├── convert/
├── log/
├── processed_cnnx/
├── quantizer_input_data_npy/
├── recipe/
├── simulator_input_data_npy/
├── HW_<model>_new_snc_<version>.snc
├── HWQuant_<model>_new_snc.snc
├── OutportReshape_<model>_new_snc.snc
├── QAT_<model>_new_snc.snc
├── ennpartitioner_cmd.txt
├── ennquantizer_cmd.txt
└── org_vs_hwsnc_snr.txt
```

**SDK 3.0 구조**
```
Converter_result/
├── 0_onnx_to_cnnx/                   ← Converter 산출물
│   ├── output.onnx
│   ├── output.encodings
│   └── validation/                   ← ModelValidator 결과 (2-3 참고)
├── 1_optimize/                       ← Optimizer 산출물
│   ├── output.onnx
│   ├── output.encodings
│   ├── output_mapping_table.json
│   ├── 4dim/
│   └── validation/
├── 2_mixed_precision_quantization/   ← Mixed-precision quantizer 산출물
│   ├── output.onnx
│   ├── output.encodings
│   └── validation/
├── convert/
├── NPU_<model>/
├── recipe/
├── HW_output_new_snc_<version>.snc
├── HWQuant_output_new_snc.snc
├── OutportReshape_output_new_snc.snc
├── QAT_output_new_snc.snc
├── ennpartitioner_cmd.txt
├── ennquantizer_cmd.txt
└── org_vs_hwsnc_snr.txt
```

주요 변경점:

| SDK 2.5 | SDK 3.0 | 설명 |
|---|---|---|
| `cnnx/` | `0_onnx_to_cnnx/` | 파이프라인 순서를 반영해 번호 접두어 부여 |
| `optimized/` | `1_optimize/` | 동일 |
| `quantized_mp/` | `2_mixed_precision_quantization/` | 동일 |
| `quantized/` | 제거 | SDK 3.0에서는 mixed-precision quantizer로 통합 |
| `log/`, `.log/`, `processed_cnnx/`, `quantizer_input_data_npy/`, `simulator_input_data_npy/` | 제거 | 내부 임시 산출물 정리 |

---

### 2-3. 변환 단계별 유효성 검사(ModelValidator) 추가

`eais conversion` 파이프라인의 각 단계(Converter, Optimizer, Quantizer) 완료 직후 자동으로 ModelValidator가 수행됩니다. 검사 결과(`report.html`, `validation_report.json`)는 각 단계 결과 폴더 하위 `validation/model_validation_results/`에 저장됩니다.

- **Converter / Optimizer 이후**: ONNX 검사 4종 (동적 차원, ONNX Runtime 실행 가능성, opset 버전, `Einsum` 포함 여부)
- **Quantizer 이후**: 위 ONNX 4종 + CNNX 양자화 encodings 검사 14종 = 총 18종

모두 통과 시 `validation_report.json`의 `results`는 빈 객체 `{}`이며, 실패 시 해당 validator 이름과 `fail_list`(노드명, 오류 코드, 원인)가 기록됩니다.

> Validator별 검사 내용 전체 목록, `validation_report.json` 구조와 실패 예시, `report.html` 사용법은 [EAIS_User_Guide.md → ModelValidator](documentation/sdk-3.0/eais-user-guide#modelvalidator--변환된-모델-유효성-검사)를 참고하세요.

---

### 2-4. 변환 구간을 선택할 수 있는 `--eht` / `--elt` 옵션 추가

`eais conversion`에 `--eht`, `--elt` 옵션이 추가되어 변환 파이프라인의 일부 구간만 실행할 수 있습니다. 옵션을 지정하지 않으면 전체 파이프라인이 실행됩니다.

```bash
eais conversion --w <workspace>         # 전체 실행 (권장)
eais conversion --w <workspace> --eht   # 하드웨어 비종속 단계만 (CNNX 생성)
eais conversion --w <workspace> --elt   # 하드웨어 종속 단계만 (Specifier)
```

- `--eht`: EHT 결과인 quantized CNNX(`.onnx` + `.encodings`)까지만 생성.
- `--elt`: 이미 완료된 EHT 결과를 재활용해 device-specific SNC만 생성 (다른 SoC 타겟으로 재변환 등).

> 각 옵션의 실행 구간, 사용 시점, 자주 발생하는 오류(`--elt` 단독 실행 시 `IndexError` 등)는 [EAIS_User_Guide.md → Step 3 conversion](documentation/sdk-3.0/eais-user-guide#step-3-conversion--모델-변환)을 참고하세요.

---

### 2-5. MXINT8 precision 추가

`<model_name>.yaml`의 `converter.precision`에 `MXINT8`을 새로 지정할 수 있습니다.


```yaml
converter:
  precision: MXINT8
```

---

### 2-6. 변환 정확도·모델 그래프를 단계별로 확인하는 `eais debug` 추가

`eais debug`는 `eais conversion` 결과물을 분석하는 새로운 커맨드입니다. 변환 과정의 정확도 손실을 단계별로 확인하고, 모델 그래프를 브라우저에서 시각화하며, 두 모델 간 diff까지 하나의 명령으로 수행할 수 있습니다.

`--mode` 옵션으로 실행 내용을 선택합니다.

| `--mode` | 설명 |
|---|---|
| `accuracy` (기본) | conversion 각 모듈 산출물 간 정확도 지표(SNR, PSNR, COSSIM 등)를 계산해 `accuracy_comparison.xlsx` / CSV로 저장 |
| `visualize` | 브라우저에서 모델 그래프, 노드/tensor 속성, activation 분포, accuracy 결과 확인. 두 모델 diff 비교, accuracy 결과 preload 지원 |
| `all` | `--mode accuracy` 완료 후 `--mode visualize`를 순서대로 실행 |

```bash
# 정확도 검증 (기본)
eais debug --w ./hrnet_pose

# 최종 SNC 모델 시각화
eais debug --w ./hrnet_pose --mode visualize \
  --base_model_path ./Converter_result/HW_output_new_snc_9.7.9.30.snc
```

`--mode visualize` / `--mode all` 실행 시 브라우저(기본 `http://127.0.0.1:40090`)에서 다음을 확인할 수 있습니다.

- **Graph 뷰** — 모델 토폴로지, 노드/엣지/tensor 속성 및 activation 분포(히스토그램)
- **Accuracy 뷰** — Pipeline Flow / Dashboard / Layer-wise Analysis / Summary Report
- **Diff 모드** — 두 모델을 좌·우 pane으로 나란히 비교
- **SNC 편집 & Export** — SNC 속성/양자화 metadata 편집 후 SNC 재출력

![image](https://soc-developer.semiconductor.samsung.com/ai1/8628648b-f6df-417b-8304-c955a9b5c7d7?response-content-type=image%2Fpng&Expires=1796581127&Signature=IJGLFNnK7bIqekrQbf2s8swy4gIT8D8xENH6LzzAtXshz23ci1OcAvXJzem2t4JnfDNQwVkbpfaPyVhnu2dQS~oaiTlW-MhYQDojLkJrsV2LLoYuDd~JMyfNygYlhewqMc1QbhvNej9-A6IkXYgivQfxWpGFRh38XaEgL2MaghJmYn1qwITdPedbFatr9vXwZx6lNkcqld~jPydmZbS15GCtpsWhSngwKgijRx3RFUVLZmQzU3J554Q8B5u5OOK9FgyATmjv038EoAbBtBf3Pumqtl4Dc94hRidoC-MRkLcNCaWH5NWkeJSzbsurjfrabGskTA3yf9aWZPEZEDVYPw__&Key-Pair-Id=K3Q589AYB0FA7R)

> CLI 옵션 전체, `Config/debug.yaml` 파라미터, accuracy 지표 해석 기준, `accuracy_comparison_csv` 컬럼 설명, 트러블슈팅 등 상세 사용법은 [`eais debug 사용 가이드`](documentation/sdk-3.0/debug-guide)를 참고하세요. 요약 사용법은 [EAIS_User_Guide.md → Option: debug](documentation/sdk-3.0/eais-user-guide#option-debug--conversion-모듈-산출물-정확도-비교-및-모델-시각화)에서도 확인할 수 있습니다.

---


## 3. 기본값 변경

---

### 3-1. 기본 타겟 디바이스가 Gen-9로 변경됨

`eais init` 후 생성되는 `<model_name>.yaml`의 기본 타겟 디바이스가 `Gen-8`에서 `Gen-9`로 변경되었습니다.

```yaml
general:
  device: Gen-9   # SDK 2.5에서는 Gen-8이 기본값이었습니다
```

> [!NOTE]
> **Gen-8 타겟으로 작업하는 경우:** `eais init` 후 `device: Gen-8`로 직접 수정해 주세요. Gen-2~Gen-9별 지원 SoC 매핑은 [EAIS_User_Guide.md → general 섹션](documentation/sdk-3.0/eais-user-guide#general-섹션)을 참고하세요.

---

### 3-2. `<model_name>.yaml`에서 simulator 섹션 제거됨

SDK 2.5에서 `<model_name>.yaml`에 포함되어 있던 `simulator` 섹션이 제거되었습니다.
simulator 관련 파라미터가 필요한 경우 `Config/conversion_expert.yaml`을 참고해 주세요.
