# eais profiling — User Guide

`eais profiling` is a command for analyzing the performance of a compiled nnc.
Detailed settings such as **execution environment configuration** and **Device connection settings** can be configured in the `Config/profiler_advanced_config.yaml` file.

---

## Prerequisites

> [!NOTE]
> After `eais compile` completes, the `Compiler_result` folder (the build output) must exist inside the workspace, and a device capable of running nnc must be ready. Additionally, the Enn test app must be installed on the device to run nnc.

---

## Docker → SSH → ADB Connection Structure

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

## Option Summary
`Profiler settings in the top-level yaml file inside the Workspace`

| Option | Required | Description |
|---|---|---|
| `device_id` | Required (default: NOT_USE) | Device ID connected to the server |
| `ssh_bool` | Required (default: SSH_FALSE) | Whether to use an SSH connection |
| `profiler_advanced_config` | Required (default: `Config/profiler_advanced_config.yaml`) | yaml file for configuring additional SSH connection settings and the nnc execution environment |

`Settings for the yaml file specified in the profiler_advanced_config option`
| Option | Required | Description |
|---|---|---|
| `npu_only` | Optional (default: true) | true if all operations in the model are performed only on the NPU; false if there are operations performed on the DSP |
| `core_num` | Required (default: single) | Number of NPU cores on which the model runs (multiple) |
| `ssh_bool` | Required (default: SSH_FALSE) | Whether an SSH connection is needed to connect to the device |
| `ssh_hostname` | Required (default: NOT_USE) | Remote server IP for SSH connection |
| `ssh_port` | Required (default: NOT_USE) | SSH port for SSH connection (22) |
| `ssh_username` | Required (default: NOT_USE) | Remote server user ID |
| `ssh_passwd` | Required (default: NOT_USE) | Remote server user password |
| `ssh_workspace` | Optional (default: ./ssh_workspace) | Location where profiling results are saved |
| `tv_threshold` | Optional (default: 0.0001) | Threshold value for bit matching when running the EnnTest test app |
| `bitmatch_test` | Optional (default: false) | Check bit matching only without generating profiling results |
| `iter` | Optional (default: 1) | Number of times the model inference is executed |
| `mode` | Optional (default: performance) | Enn test app execution mode (lowpower, balanced, performance, boost, custom) |
| `perfconfig_id` | Optional (default: 100001) | Additional value specified when the mode option is custom (mainly used for GenAI, Benchmark) |
| `target` | Optional (default: model) | If model, performs per-layer profiling within the model; if system, summarizes the enn execution log (cpu/gpu/npu/kernel, etc.) |
| `test_type` | Optional (default: lib) | Specifies the type of the Enn test app (lib is the default, so no change is needed) |
| `useSNR` | Optional (default: true) | Criterion for determining bit matching of the model (SNR or threshold) |

---
## How to Run
### Command
```bash
$ eais profiling
```

### Example (model #10-10)
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
## Execution Results

### Output
The final profiling results can be viewed in the Perfetto UI (Chrome browser). (Load the `NPU_STM_summary_perfetto.json` file at https://ui.perfetto.dev/)

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
