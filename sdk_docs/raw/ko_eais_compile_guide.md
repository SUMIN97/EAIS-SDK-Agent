# eais compile — 사용 가이드

`eais compile` 명령어는 양자화 된 모델을(conversion 수행) Device에서 실행하기 위해 컴파일하여 nnc 생성하는 커맨드입니다.
그리고 `Config/compiler_tuning_mode_config.yaml` 파일에서 **기본 옵션 값 변경**, **추가 최적화** 적용 등을 위해 세부 옵션을 추가적으로 지정할 수 있습니다.

---

## 사전 조건

> [!NOTE]
> eais conversion 완료 된 이후 workspace 내에 conversion 결과물인 Converter_result 폴더가 있어야 합니다.

---

## Exynos AI Compiler High-Level 개요도

![image](https://soc-developer.semiconductor.samsung.com/ai1/b1cbfb10-d2cd-4c59-806a-d6d9adf2e508?response-content-type=image%2Fpng&Expires=1796581128&Signature=N-WI7sdSUkWevzKA0JqBCima1sAxC8JThw-1C~BD8CG8WrLlhgoVcpTrOtb5aP9ew9BgySKZeaz0WFbv7j2V49ITdJT3XQDrjP6MJhZJcrGpQ6ADBgk-VIrBltwZItw3daqrL~paVi-vo6ftd5XQ6l9Z79YweEff-sKX9bFB9fT40hXx7f6c~tZapVVcuiW9T2y-QovlQXQRoWS8lZOtNiZ~~NVoJPxwVsZlmsItyLB9NhGQVAqQIXM15HJfseySKOzPttJkNsribrYg8pU6a0d8sfZUEboIOs3c6EJ~yX4f8FortN8ARGWXMgk6P3YvKfvWEyiXgQa2zMnMPTnZWg__&Key-Pair-Id=K3Q589AYB0FA7R)

---

## 옵션 정리
`Worskapce 내에 있는 최상위 yaml 파일에 있는 compiler 설정`

| 옵션 | 필수 여부 | 설명 |
|---|---|---|
| `mode` | 필수 (기본: default) | nnc 컴파일 모드를 설정합니다.(default: single core, multicore: multi core) tuning_mode는 compiler_tuning_mode_config.yaml 에서 추가적인 옵션을 지정하는 모드 |
| `debug_str` | 선택 (기본: "") | yaml에 지정된 옵션 외에 추가적으로 지정하기 위한 빌드 옵션  |
| `compiler_advanced_config` | 선택 (기본: `Config/compiler_tuning_mode_config.yaml`) | mode가 tuning_mode 일 경우에 지정하는 yaml 파일 |

`compiler_tuning_mode_config.yaml 옵션에 지정된 yaml 파일 설정` <br>
yaml 파일 내에 있는 옵션 전부 확인하지 않고, 아래 기본 옵션 외에 성능 및 바이너리 사이즈 관련 최적화 옵션만 확인하면 됨
| 옵션 | 필수 여부 | 설명 |
|---|---|---|
| `cast_inout` | 선택 (기본: hw) | Type casting fp32 to fp16 for nnc input data and fp16 to fp32 for nnc output data |
| `compiler` | 필수 (기본: NPU) | Compiler option (NPU, CPUGPU, DSP) |
| `dequant_type` | 선택 (기본: hw) | Dequantiztion type |
| `enable_stm` | 선택 (기본: true) | Generate compile log for profiling |
| `input_conversion` | 선택 (기본: hw_cfu) | Add a Raster2Cell format converter node at start of network |
| `output_conversion` | 선택 (기본: hw_icfu) | Add a Cell2Raster format converter node at end of network |
| `multi_vc` | 필수 (기본: true) | Multi-VC settings for OFM, IFM, and Weight transfer |
| `multicore` | 필수 (기본: true) | Enable NPU multicore |
| `optimization` | 필수 (기본: O2) | Compiler Optimization level (O0, O1, O2) |
| `quant_type` | 필수 (기본: hw) | Quantiztion type |
| `multi_ncp` | 필수 (기본: true) | Generate multi-ncp for custom op which is running on CPU/GPU |
| `enable_hw_cost_based_stratum` | 선택 (기본: true) | This is optimization parameter for stratum tiling based on HW cost ("-D") |
| `loop_scheduling` | 선택 (기본: false) | compiler scheduling ("-D") 성능 |
| `enable_automated_graph_slicing` | 선택 (기본: false) | compiler scheduling ("-D") 성능 |
| `dram_reduction` | 선택 (기본: false) | feature map compression ("-D") 바이너리 사이즈 |
| `weight_comp` | 선택 (기본: false) | weight compression ("-D") 바이너리 사이즈 |
| `remove_redundant_sfr_setting` | 선택 (기본: false) | nnc size optimization ("-C") 바이너리 사이즈 |
| `vc_allocation` | 선택 (기본: '') | nnc size optimization (설정 값은 `static`, "-C") 바이너리 사이즈 |
| `cluster_execution` | 선택 (기본: true) | Enable NPU cluster |

전체 yaml file (참고)
| 옵션 | 필수 여부 | 설명 |
|---|---|---|
| `assign_cpu` | 선택 (기본: "") | Assign specific layer to cpu device |
| `assign_dsp` | 선택 (기본: "") | Assign specific layer to dsp device |
| `assign_npu` | 선택 (기본: "") | Assign specific layer to npu device |
| `assign_ve` | 선택 (기본: "") | Assign specific layer to ve device |
| `assign_gpu` | 선택 (기본: "") | Assign specific layer to gpu device |
| `cast_inout` | 선택 (기본: hw) | Type casting fp32 to fp16 for nnc input data and fp16 to fp32 for nnc output data |
| `compiler` | 필수 (기본: NPU) | Compiler option (NPU, CPUGPU, DSP) |
| `dequant_type` | 선택 (기본: hw) | Dequantiztion type |
| `enable_stm` | 선택 (기본: true) | Generate compile log for profiling |
| `input_conversion` | 선택 (기본: hw_cfu) | Add a Raster2Cell format converter node at start of network |
| `output_conversion` | 선택 (기본: hw_icfu) | Add a Cell2Raster format converter node at end of network |
| `multi_vc` | 필수 (기본: true) | Multi-VC settings for OFM, IFM, and Weight transfer |
| `multicore` | 필수 (기본: true) | Enable NPU multicore |
| `optimization` | 필수 (기본: O2) | Compiler Optimization level (O0, O1, O2) |
| `quant_type` | 필수 (기본: hw) | Quantiztion type |
| `enable_active_stratum` | 선택 (기본: false) | This is optimization parameter for stratum tiling |
| `enable_hw_cost_based_stratum` | 선택 (기본: true) | This is optimization parameter for stratum tiling based on HW cost |
| `enable_ofm_reuse` | 선택 (기본: false) | Enable the reuse of OFM region for IFM | 
| `strict_dfs` | 선택 (기본: false) | This is optimization parameter for tiling scheduling |
| `use_fine_grained_deps` | 선택 (기본: false) | This is optimization parameter for tiling scheduling |
| `best_fit_generalized` | 선택 (기본: false) | Control whether generalized best fit allocation is to be used |
| `tuning_config` | 선택 (기본: Config/nnc_graph_tiling.json) | Path of nnc graph tiling config file,default path is {workspace}/Config/nnc_graph_tiling.json |
| `pattern_config` | 선택 (기본: Config/pattern_config.json) | Path of nnc optimization pattern config file,default path is {workspace}/Config/pattern_config.json |
| `schedule_config` | 선택 (기본: Config/schedule.cfg.0) | Path of nnc schedule config file,default path is {workspace}/Config/schedule.cfg.0 |
| `schedule_dep_config` | 선택 (기본: Config/schedule_dep.cfg) | Path of nnc schedule_dep config file,default path is {workspace}/Config/schedule_dep.cfg |
| `multi_ncp` | 필수 (기본: true) | Generate multi-ncp for custom op which is running on CPU/GPU |
| `enable_automated_graph_slicing` | 선택 (기본: false) | compiler scheduling |
| `cfu_double_buffering` | 선택 (기본: true) | compiler scheduling |
| `graph_slicing_before_cu_multi_node_lowering` | 선택 (기본: false) | compiler scheduling |
| `tiling_fragmentation_factor` | 선택 (기본: 1.0) | compiler scheduling |
| `loop_scheduling` | 선택 (기본: false) | compiler scheduling |
| `eltsum_to_conv_lowering` | 선택 (기본: true) | replace eltsum to conv op |
| `cell_packing` | 선택 (기본: true) | cells are packed into the same physical SRAM word |
| `dram_reduction` | 선택 (기본: false) | feature map compression |
| `weight_comp` | 선택 (기본: false) | weight compression |
| `enable_permute_reordering` | 선택 (기본: true) | transpose reordering |
| `remove_redundant_sfr_setting` | 선택 (기본: false) | nnc size optimization |
| `vc_allocation` | 선택 (기본: '') | nnc size optimization |
| `parallel_execution_in_stratum` | 선택 (기본: true) | compiler scheduling |
| `remove_redundant_load_store` | 선택 (기본: true) | remove redundant load store |
| `enable_post_allocation_passes` | 선택 (기본: true) | compiler sram allocation |
| `enable_opt_kcell_conversion` | 선택 (기본: true) | optimized shape conversion |
| `enable_batch_reinterpretation` | 선택 (기본: true) | re-interpret batch dimension |
| `cluster_execution` | 선택 (기본: true) | Enable NPU cluster |

---

## 실행 방법
### 명령어
```bash
$ eais compile
```

---

### 예시 (#10-19 모델)
```bash
$ vim 01-19_hdr_verifier_cnn.yaml
... skip ...
compiler:
  mode: default                                                         #[default, multicore, tuning_mode, gen-ai, gaussl, gaussi]: default, use default param settings, multicore, use multicore param settings, tuning_mode, set param in compiler_tuning_mode_config.yaml
  debug_str:                                                            #[str]: Debug str for compiler
  compiler_advanced_config: Config/compiler_tuning_mode_config.yaml     #[path]: if mode is tuning_mode, please set params in this yaml file

$ vim Config/compiler_tuning_mode_config.yaml
assign_cpu:                                        #[str]: Assign specific layer to cpu device
assign_dsp:                                        #[str]: Assign specific layer to dsp device
assign_npu:                                        #[str]: Assign specific layer to npu device
assign_ve:                                         #[str]: Assign specific layer to ve device
assign_gpu:                                        #[str]: Assign specific layer to gpu device
cast_inout: hw                                     #[sw, hw, none]: Type casting fp32 to fp16 for nnc input data and fp16 to fp32 for nnc output data
compiler: NPU                                      #[NPU, CPUGPU, DSP]: Compiler option
dequant_type: hw                                   #[sw, hw, none]: Dequantiztion type
enable_stm: true                                   #[bool]: Generate compile log including L1 tiling information
input_conversion: hw_cfu                           #[sw_cfu, hw_cfu, no_cfu]: Add a Tensor2Cell format converter node at start of network
output_conversion: hw_icfu                         #[sw_icfu, hw_icfu, no_icfu]: Add a Tensor2Cell format converter node at end of network
multi_vc: true                                     #[bool]: Introduce Multi-VC for OFM, IFM, and weight transfer
multicore: true                                    #[bool]: Enable NPU multicore
optimization: O2                                   #[O0, O1, O2]: Optimization choice
quant_type: hw                                     #[sw, hw, none]: Quantiztion type
enable_active_stratum: false                       #[bool]: This is optimization parameter for stratum tiling
enable_hw_cost_based_stratum: true                 #[bool]: This is optimization parameter for stratum tiling based on HW cost
enable_ofm_reuse: false                            #[bool]: Enable the reuse of OFM region for IMFM.
strict_dfs: false                                  #[bool]: This is optimization parameter for tiling scheduling
use_fine_grained_deps: false                       #[bool]: This is optimization parameter for tiling scheduling
best_fit_generalized: false                        #[bool]: Control whether generalized best fit allocation is to be used.
tuning_config: Config/nnc_graph_tiling.json        #[path]: Path of nnc graph tiling config file,default path is {workspace}/Config/nnc_graph_tiling.json
pattern_config: Config/pattern_config.json         #[path]: Path of nnc optimization pattern config file,default path is {workspace}/Config/pattern_config.json
schedule_config: Config/schedule.cfg.0             #[path]: Path of nnc schedule config file,default path is {workspace}/Config/schedule.cfg.0
schedule_dep_config: Config/schedule_dep.cfg       #[path]: Path of nnc schedule_dep config file,default path is {workspace}/Config/schedule_dep.cfg
multi_ncp: true                                    #[bool]: Generate multi-ncp(ucgo) custom op
enable_automated_graph_slicing: false              #[bool]: compiler scheduling
cfu_double_buffering: true                         #[bool]: compiler scheduling
graph_slicing_before_cu_multi_node_lowering: false #[bool]: compiler scheduling
tiling_fragmentation_factor: 1.0                   #[float]: compiler scheduling
loop_scheduling: false                             #[bool]: compiler scheduling
eltsum_to_conv_lowering: true                      #[bool]: replace eltsum to conv op
cell_packing: true                                 #[bool]: several cells are packed into the same physical SRAM word
dram_reduction: false                              #[bool]: weight compression
weight_comp: false                                 #[bool]: weight compression
enable_permute_reordering: true                    #[bool]: transpose reordering
remove_redundant_sfr_setting: false                #[bool]: nnc compression
vc_allocation:                                     #[str]: nnc compression
parallel_execution_in_stratum: true                #[bool]: compiler scheduling
remove_redundant_load_store: true                  #[bool]: remove redundant load store
enable_post_allocation_passes: true                #[bool]: compiler sram allocation
enable_opt_kcell_conversion: true                  #[bool]: optimized shape conversion
enable_batch_reinterpretation: true                #[bool]: re-interpret batch dimension
cluster_execution: true                            #[bool]: Enable NPU cluster
```

> [!NOTE] Default 모드 일때 사용되는 옵션과 값
> ```
> --input_conversion hw_cfu --output_conversion hw_icfu 
> -D cluster_execution=true 
> --dequant_type_hw_or_sw sw --quant_type_hw_or_sw sw
> --cast_hw_or_sw sw --multi_vc True -D enable_hw_cost_based_stratum=true
> ```

nncontainer-gen 빌드 로그 (Default 모드)
``` bash
$ cat nncontainer-gen.txt
Graphgen command:
nncontainer-gen --compiler NPU --snc "<path-to-model>/01-19_hdr_verifier_cnn_test/Converter_result/HW_output_new_snc_9.7.10.30.snc" --framework SNC  --soc-type Ulysses \
--input_conversion hw_cfu --output_conversion hw_icfu -D cluster_execution=true  --chip_version EVT1 --schema_version v3 --dequant_type_hw_or_sw sw --quant_type_hw_or_sw sw \
--npuhw "/usr/local/lib/python3.10/dist-packages/eais/lib/npuc_new/ulysses/hardware_configuration.EVT1.xml" \
--npupass "/usr/local/lib/python3.10/dist-packages/eais/lib/npuc_new/ulysses/O2.json" \
--cast_hw_or_sw sw --multi_vc True -D enable_hw_cost_based_stratum=true --computational_workload 88504 --enable_stm True --export_io_info 1  \
-o <path-to-model>/01-19_hdr_verifier_cnn_test/Compiler_result > <path-to-model>/01-19_hdr_verifier_cnn_test/Compiler_result/profile_log.txt  \
--tuning_config Config/nnc_graph_tiling.json
```

> [!NOTE] Tuning 모드 일때 사용되는 옵션과 값
> ```
> --input_conversion hw_cfu --output_conversion hw_icfu 
> -D cluster_execution=true
> --dequant_type_hw_or_sw hw --quant_type_hw_or_sw hw 
> --cast_hw_or_sw hw --multi_vc True -D enable_hw_cost_based_stratum=true --multi_ncp true 
> ```

nncontainer-gen 빌드 로그 (Tuning 모드)
``` bash
$ cat nncontainer-gen.txt
Graphgen command:
nncontainer-gen --compiler NPU --snc "<path-to-model>/01-19_hdr_verifier_cnn_test/Converter_result/HW_output_new_snc_9.7.10.30.snc" --framework SNC  --soc-type Ulysses \
--input_conversion hw_cfu --output_conversion hw_icfu -D cluster_execution=true  --chip_version EVT1 --schema_version v3 --dequant_type_hw_or_sw hw --quant_type_hw_or_sw hw \
--npuhw "/usr/local/lib/python3.10/dist-packages/eais/lib/npuc_new/ulysses/hardware_configuration.EVT1.xml" \
--npupass "/usr/local/lib/python3.10/dist-packages/eais/lib/npuc_new/ulysses/O2.json" \
--cast_hw_or_sw hw --multi_vc True -D enable_hw_cost_based_stratum=true --multi_ncp true  --computational_workload 88504 --enable_stm True --export_io_info 1 \
-o <path-to-model>/01-19_hdr_verifier_cnn_test/Compiler_result > <path-to-model>/01-19_hdr_verifier_cnn_test/Compiler_result/profile_log.txt \
--tuning_config Config/nnc_graph_tiling.json
```

---

## 실행 결과

### 산출물
```bash
01-19_hdr_verifier_cnn
├── 01-19_hdr_verifier_cnn.onnx
├── 01-19_hdr_verifier_cnn.yaml
└── Compiler_result
    ├── gen_files
    │   └── graph_0
    │       ├── npu
    │       │   ├── backend
    │       │   │   ├── backend.isa
    │       │   │   ├── back_end_TENSOR_ENGINE_0.bin
    │       │   │   ├── back_end_TENSOR_ENGINE_0_CMDQ
    │       │   │   │   ├── commands.asm
    │       │   │   │   └── commands.bin
    │       │   │   ├── back_end_TENSOR_ENGINE_0.csv
    │       │   │   ├── back_end_TENSOR_ENGINE_0.isa
    │       │   │   ├── back_end_VECTOR_ENGINE_0.bin
    │       │   │   ├── back_end_VECTOR_ENGINE_0_CMDQ
    │       │   │   │   ├── commands.asm
    │       │   │   │   └── commands.bin
    │       │   │   ├── back_end_VECTOR_ENGINE_0.csv
    │       │   │   ├── back_end_VECTOR_ENGINE_0.isa
    │       │   │   ├── merged_const.bin
    │       │   │   ├── ncp.bin
    │       │   │   ├── profile_log.txt
    │       │   │   ├── profile_npue.json
    │       │   │   └── weights.bin
    │       │   ├── frontend
    │       │   │   └── frontend.ir
    │       │   └── middleend
    │       │       └── middle_end.ir
    │       └── npu_config
    ├── main_graph_O2_SingleCore.nnc
    ├── NNCInfo.csv
    ├── nncontainer-gen.txt
    └── profile_log.txt
```

---

## CLI 명령어 사용법
### 명령어
CLI 명령에 있는 debug_str 옵션 값을 통해서 추가 옵션을 지정할 수 있습니다.
```bash
$ eais compile --mode tuning_mode --debug_str '-D dram_reduction=true -D weight_comp=true -C remove_redundant_sfr_setting=true'
```
성능: "-D enable_automated_graph_slicing=true -D loop_scheduling=true -D flc"<br>
사이즈: "-D dram_reduction=true -D weight_comp=true -C remove_redundant_sfr_setting=true -C vc_allocation=static"

```bash
Graphgen command:
nncontainer-gen --compiler NPU --snc "<path-to-model>/01-19_hdr_verifier_cnn_test/Converter_result/HW_output_new_snc_9.7.10.30.snc" --framework SNC  --soc-type Ulysses \
--input_conversion hw_cfu --output_conversion hw_icfu -D cluster_execution=true  --chip_version EVT1 --schema_version v3 --dequant_type_hw_or_sw hw --quant_type_hw_or_sw hw \
--npuhw "/usr/local/lib/python3.10/dist-packages/eais/lib/npuc_new/ulysses/hardware_configuration.EVT1.xml" \
--npupass "/usr/local/lib/python3.10/dist-packages/eais/lib/npuc_new/ulysses/O2.json" \
--cast_hw_or_sw hw --multi_vc True -D multivc_byte_size_threshold=2048 -D dram_reduction=true -D weight_comp=true -C remove_redundant_sfr_setting=true \
-D enable_hw_cost_based_stratum=true --multi_ncp true  --computational_workload 88504 --enable_stm True --export_io_info 1 \
-o <path-to-model>/01-19_hdr_verifier_cnn_test/Compiler_result > <path-to-model>/01-19_hdr_verifier_cnn_test/Compiler_result/profile_log.txt \
--tuning_config Config/nnc_graph_tiling.json
```

### 옵션 Prefix 설명
| 약어 | 설명 |
|------|------|
| `-D` | Middleend에 전달하는 옵션 |
| `-C` | Backend에 전달하는 옵션 |
| `-N` | 로그 및 System SW에 전달하는 옵션 |
