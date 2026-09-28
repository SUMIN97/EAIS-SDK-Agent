# eais profilng — 사용 가이드

`eais profilng`은 컴파일된(compile) nnc의 성능을 분석하는 커맨드입니다.
세부 설정은 `Config/profiler_advanced_config.yaml` 파일에서 **실행 환경 설정** 및 **Device 연결 설정** 등을 진행할 수 있습니다.

---

## 사전 조건

> [!NOTE]
> eais compile 완료 된 이후 workspace 내에 빌드 결과물인 Compiler_result 폴더가 있어야 하며, nnc를 실행할 수 있는 device가 준비되어 있어야 합니다. 그리고 device 내에 nnc를 실행할 수 있는 Enn test app 설치가 필요합니다.

---

## Docker → SSH → ADB 연결 구조

```
  ┌─────────────────────────────┐
  │         Host PC             │
  │                             │
  │  ┌───────────────────────┐  │
  │  │    Docker Container   │  │
  │  │                       │  │
  │  │  $ ssh user@remote    │  │
  │  └──────────┬────────────┘  │
  └─────────────┼───────────────┘
                │ SSH
                │
                ▼
  ┌─────────────────────────────┐
  │       Remote Server         │
  │                             │
  │  $ adb -s <device> shell    │    Enn f/w install
  └──────────────┬──────────────┘    $ cd <path-to-enn-fw>/output
                 │ ADB connect       $ adb push vendor /
                 │
                 ▼
  ┌─────────────────────────────┐
  │           Device            │
  │        (Android/NPU)        │
  └─────────────────────────────┘
```


---

## 옵션 정리
`Worskapce 내에 있는 최상위 yaml 파일에 있는 profiler 설정`

| 옵션 | 필수 여부 | 설명 |
|---|---|---|
| `device_id` | 필수 (기본: NOT_USE) | 서버에 연결된 device id |
| `ssh_bool` | 필수 (기본: SSH_FALSE) | ssh connection 여부 |
| `profiler_advanced_config` | 필수 (기본: `Config/profiler_advanced_config.yaml`) | ssh 연결 추가 설정 및 nnc 실행 환경을 설정하는 yaml 파일 |

`profiler_advanced_config 옵션에 지정된 yaml 파일 설정`
| 옵션 | 필수 여부 | 설명 |
|---|---|---|
| `npu_only` | 선택 (기본: true) | 모델 내에 모든 operation이 npu에서만 수행되는 경우 true, dsp에서 수행되는 operation이 있는 경우 false |
| `core_num` | 필수 (기본: single) | 모델이 실행되는 NPU core 수 (multiple) |
| `ssh_bool` | 필수 (기본: SSH_FALSE) | Device 연결을 위해 SSH 연결 필요 여부 |
| `ssh_hostname` | 필수 (기본: NOT_USE) | SSH 연결 위한 Remote 서버 IP |
| `ssh_port` | 필수 (기본: NOT_USE) | SSH 연결 위한 SSH port (22) |
| `ssh_username` | 필수 (기본: NOT_USE) | Remote 서버 사용자 ID |
| `ssh_passwd` | 필수 (기본: NOT_USE) | Remote 서버 사용자 Password |
| `ssh_workspace` | 선택 (기본: ./ssh_workspace) | Profiling 결과가 저장되는 위치 |
| `tv_threshold` | 선택 (기본: 0.0001) | EnnTest test app 실행 시 bit matching을 위한 threshold 값 설정 |
| `bitmatch_test` | 선택 (기본: false) | Profiling 결과 생성없이 bit matching 만 확인 |
| `iter` | 선택 (기본: 1) | 모델 수행 횟수 |
| `mode` | 선택 (기본: performance) | Enn test app 수행 모드 (lowpower, balanced, performance, boost, custom) |
| `perfconfig_id` | 선택 (기본: 100001) | Mode 옵션 값이 custom 인 경우, 추가 지정하는 value (GenAI, Benchmark에 주로 사용 됨) |
| `target` | 선택 (기본: model) | model 인 경우 model 내 layer 별 profiling 진행, system 인 경우 enn 실행 로그를 요약해서 보여 줌 (cpu/gpu/npu/kernel 등)
| `test_type` | 선택 (기본: lib) | Enn test app의 type을 지정 함 (lib이 deafult이므로 변경할 필요 없음) |
| `useSNR` | 선택 (기본: true) | 모델의 bit matching 판단 기준 (SNR 또는 threshold) |

---
## 실행 방법
### 명령어
```bash
$ eais profiling
```

### 예시 (#10-10 모델)
```bash
$ vim 10-10_super_sf_tetra_dummy.yaml
... skip ...
profiler:
  device_id: 10.229.116.245:7657                                        #[number]: id of the device connected to the server or PC running the enntools docker
  ssh_bool: SSH_TRUE                                                    #[SSH_FALSE, SSH_TRUE]: Connect to the device through ssh
  profiler_advance_config: Config/profiler_advanced_config.yaml         #[path]: the path of profiler config yaml

$ vim Config/profiler_advanced_config.yaml
npu_only: true                                    #[bool]: true: nnc just contains npu event, false: nnc also contains other event
core_num: single                                  #[single, multiple]: The number of NPU core
ssh_bool: SSH_TRUE                                #[SSH_FALSE, SSH_TRUE]: Connect to the device through ssh
ssh_hostname: 109.144.4.53                        #[str]: host name of the server connected to the device
ssh_port: 22                                      #[str]: the port number of the server connected to the device
ssh_username: changjian.jiang                     #[str]: the user name of the account connected to the device
ssh_passwd: changjian.jiang                       #[str]: the pass word of the account connected to the device
ssh_workspace: ./ssh_workspace                    #[str]: ssh workspace on the server connected to the device, ./ssh_workspace
tv_threshold: 0.0001                              #[number]: The value is used for tolerance threshold of output match verification.
bitmatch_test: false                              #[bool]: true: run nnc on device to check bitmatch status without running visualprofiler function
iter: 1                                           #[number]: This decides how many time the model inference will be processed.
mode: performance                                 #[lowpower, balanced, performance, boost, custom]: 1. Low power mode : Mode for low power consumption and low performance. 2. Balanced mode : Mode for medium power consumption and medium performance. 3. Performance mode : Mode for high power consumption and high performance. 4. Boost mode : Mode for very high power consumption and very high performance. 5. custom mode: Mode for futher tuning of the Perf settings.
perfconfig_id: 100001                             #[number]: used when mode is custom
target: model                                     #[model, system]: profiling target.
test_type: lib                                    #[lib, service]: ENN running mode
useSNR: true                                      #[bool]: true: check nnc ondevice bitmatch status with SNR, false: check nnc ondevice bitmatch status with threshold": False
```

---
## 실행 결과

### 산출물
최종 Profilng 결과는 Perfetto UI에서(Chrome 브라우저) 확인할 수 있습니다. (https://ui.perfetto.dev/ 에서 NPU_STM_summary_perfetto.json 파일 로딩)

```bash
10-10_super_sf_tetra_dummy
├── 10-10_super_sf_tetra_dummy.onnx
├── 10-10_super_sf_tetra_dummy.yaml
├── Compiler_result
├── Converter_result
└── Profiler_result
	└── VisualProfiler
		└── Annotation
		    ├── debug_annotation_20260710_144145.log
		    ├── NPU_STM_summary.json
		    └── NPU_STM_summary_perfetto.json
```
---
#### NPU_STM_summary.json
```bash
{
  "NPU_total": {
    "unit": "us",
    "inference_time_us": 5436.094,
    "actual_execution_time_us": 5245.391,
    "CONSTANT": 25.819,
    "FM_LOAD": 1510.741,
    "SDMA_OP": 677.774,
    "W_LOAD": 111.095,
    "TE": 3583.597,
    "FM_STORE": 1857.387
  },
  "nodes": {
    "270": {
      "node_name": "splitted_down.weight_0_0",
      "node_type": "Convolution",
      "unit": "us",
      "inference_time_us": 108.516,
      "actual_execution_time_us": 18.516,
      "CONSTANT": 2.968,
      "FM_LOAD": 0.0,
      "SDMA_OP": 0.0,
      "W_LOAD": 1.524,
      "TE": 15.274,
      "FM_STORE": 0.0
    },
    "276": {
      "node_name": "splitted_conv_first.weight_1_0",
      "node_type": "Convolution",
      "unit": "us",
      "inference_time_us": 222.656,
      "actual_execution_time_us": 117.734,
      "CONSTANT": 2.929,
      "FM_LOAD": 0.0,
      "SDMA_OP": 0.0,
      "W_LOAD": 13.789,
      "TE": 80.625,
      "FM_STORE": 23.281
    },
... skip ...
  "op_total": {
    "unit": "us",
    "Convolution": {
      "number": 117,
      "sum_time": 6660.125
    },
    "Deconvolution": {
      "number": 11,
      "sum_time": 331.052
    },
    "DataFormat": {
      "number": 15,
      "sum_time": 769.651
    }
  }
}
```
---