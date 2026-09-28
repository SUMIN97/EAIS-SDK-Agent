# eais compile — Usage Guide

The `eais compile` command compiles a quantized model (performing conversion) to run on a Device, generating an nnc.
Additionally, detailed options can be specified in the `Config/compiler_tuning_mode_config.yaml` file to **change default option values** and apply **additional optimizations**.

---

## Prerequisites

> [!NOTE]
> After eais conversion is complete, the Converter_result folder (the output of conversion) must exist inside the workspace.

---

## Exynos AI Compiler High-Level Overview

```
                        [ SNC ]
                           │
                           ▼
          ┌─────────────────────────────────────────────┐
          │       Frontend (Graph Generator)            │
          │                             ┌──────────┐    │
          │  Parser → In-house IR       │  Merger  ├────┼──► NNC
          │              │              └────▲─────┘    │
          │   Engine Partitioning            │          │
          └──────────────┬───────────────────┼──────────┘
                      TE/VE IR               │ NCP
                         │                   │
                         ▼                   │
          ┌──────────────────────────────┐   │
          │           Middleend          │   │
          │                              │   │
          │  Graph Optimization          │   │
          │         │                    │   │
          │       Tiling                 │   │
          │         │                    │   │
          │  Memory Allocation           │   │
          │                              │   │
          │  Instruction Scheduling      │   │
          │         │                    │   │
          │  HW dependent Optimizations  │   │
          └──────────────┬───────────────┘   │
                   Optimized IR              │
                         │                   │
                         ▼                   │
          ┌──────────────────────────────┐   │
          │            Backend           │   │
          │                              │   │
          │  vISA Gen  →  vISA           │   │
          │                │             │   │
          │           CMDQ Gen           │   │
          │                │             │   │
          │           NCP Gen            │   │
          │          commands.bin        │   │
          └──────────────┬───────────────┘   │
                         │ NCP               │
                         └───────────────────┘
```

## Legend

| Abbreviation | Description |
|------|------|
| `NNC` | Neural Network Container (final output) |
| `NCP` | Network Control Program |
| `Merger` | Takes NCP as input and generates NNC (final stage) |

---

## Option Summary
`Compiler settings in the top-level yaml file inside the Workspace`

| Option | Required | Description |
|---|---|---|
| `mode` | Required (default: default) | Sets the nnc compile mode. (default: single core, multicore: multi core) tuning_mode is a mode for specifying additional options in compiler_tuning_mode_config.yaml |
| `debug_str` | Optional (default: "") | Build options for specifying additional settings beyond those defined in the yaml |
| `compiler_advanced_config` | Optional (default: `Config/compiler_tuning_mode_config.yaml`) | The yaml file to use when mode is tuning_mode |

`Settings in the yaml file specified by compiler_tuning_mode_config.yaml options`
| Option | Required | Description |
|---|---|---|
| `assign_cpu` | Optional (default: "") | Assign specific layer to cpu device |
| `assign_dsp` | Optional (default: "") | Assign specific layer to dsp device |
| `assign_npu` | Optional (default: "") | Assign specific layer to npu device |
| `assign_ve` | Optional (default: "") | Assign specific layer to ve device |
| `assign_gpu` | Optional (default: "") | Assign specific layer to gpu device |
| `cast_inout` | Optional (default: hw) | Type casting fp32 to fp16 for nnc input data and fp16 to fp32 for nnc output data |
| `compiler` | Required (default: NPU) | Compiler option (NPU, CPUGPU, DSP) |
| `dequant_type` | Optional (default: hw) | Dequantiztion type |
| `enable_stm` | Optional (default: true) | Generate compile log for profiling |
| `input_conversion` | Optional (default: hw_cfu) | Add a Raster2Cell format converter node at start of network |
| `output_conversion` | Optional (default: hw_icfu) | Add a Cell2Raster format converter node at end of network |
| `multi_vc` | Required (default: true) | Multi-VC settings for OFM, IFM, and Weight transfer |
| `multicore` | Required (default: true) | Enable NPU multicore |
| `optimization` | Required (default: O2) | Compiler Optimization level (O0, O1, O2) |
| `quant_type` | Required (default: hw) | Quantiztion type |
| `enable_active_stratum` | Optional (default: false) | This is optimization parameter for stratum tiling |
| `enable_hw_cost_based_stratum` | Optional (default: true) | This is optimization parameter for stratum tiling based on HW cost |
| `enable_ofm_reuse` | Optional (default: false) | Enable the reuse of OFM region for IFM | 
| `strict_dfs` | Optional (default: false) | This is optimization parameter for tiling scheduling |
| `use_fine_grained_deps` | Optional (default: false) | This is optimization parameter for tiling scheduling |
| `best_fit_generalized` | Optional (default: false) | Control whether generalized best fit allocation is to be used |
| `tuning_config` | Optional (default: Config/nnc_graph_tiling.json) | Path of nnc graph tiling config file,default path is {workspace}/Config/nnc_graph_tiling.json |
| `pattern_config` | Optional (default: Config/pattern_config.json) | Path of nnc optimization pattern config file,default path is {workspace}/Config/pattern_config.json |
| `schedule_config` | Optional (default: Config/schedule.cfg.0) | Path of nnc schedule config file,default path is {workspace}/Config/schedule.cfg.0 |
| `schedule_dep_config` | Optional (default: Config/schedule_dep.cfg) | Path of nnc schedule_dep config file,default path is {workspace}/Config/schedule_dep.cfg |
| `multi_ncp` | Required (default: true) | Generate multi-ncp for custom op which is running on CPU/GPU |
| `enable_automated_graph_slicing` | Optional (default: false) | compiler scheduling |
| `cfu_double_buffering` | Optional (default: true) | compiler scheduling |
| `graph_slicing_before_cu_multi_node_lowering` | Optional (default: false) | compiler scheduling |
| `tiling_fragmentation_factor` | Optional (default: 1.0) | compiler scheduling |
| `loop_scheduling` | Optional (default: false) | compiler scheduling |
| `eltsum_to_conv_lowering` | Optional (default: true) | replace eltsum to conv op |
| `cell_packing` | Optional (default: true) | cells are packed into the same physical SRAM word |
| `dram_reduction` | Optional (default: false) | feature map compression |
| `weight_comp` | Optional (default: false) | weight compression |
| `enable_permute_reordering` | Optional (default: true) | transpose reordering |
| `remove_redundant_sfr_setting` | Optional (default: false) | nnc size optimization |
| `vc_allocation` | Optional (default: '') | nnc size optimization |
| `parallel_execution_in_stratum` | Optional (default: true) | compiler scheduling |
| `remove_redundant_load_store` | Optional (default: true) | remove redundant load store |
| `enable_post_allocation_passes` | Optional (default: true) | compiler sram allocation |
| `enable_opt_kcell_conversion` | Optional (default: true) | optimized shape conversion |
| `enable_batch_reinterpretation` | Optional (default: true) | re-interpret batch dimension |
| `cluster_execution` | Optional (default: true) | Enable NPU cluster |

---

## How to Run
### Command
```bash
$ eais compile
```

---

### Example (models #10-19)
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

> [!NOTE] Options and values used in Default mode
> ```
> --input_conversion hw_cfu --output_conversion hw_icfu 
> -D cluster_execution=true 
> --dequant_type_hw_or_sw sw --quant_type_hw_or_sw sw
> --cast_hw_or_sw sw --multi_vc True -D enable_hw_cost_based_stratum=true
> ```

> [!NOTE] Options and values used in Tuning mode
> ```
> --input_conversion hw_cfu --output_conversion hw_icfu 
> -D cluster_execution=true
> --dequant_type_hw_or_sw hw --quant_type_hw_or_sw hw 
> --cast_hw_or_sw hw --multi_vc True -D enable_hw_cost_based_stratum=true --multi_ncp true 
> ```

nncontainer-gen build log (Default mode)
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

nncontainer-gen build log (Tuning mode)
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

## Execution Results

### Output Artifacts
```bash
01-19_hdr_verifier_cnn
├── 01-19_hdr_verifier_cnn.onnx
├── 01-19_hdr_verifier_cnn.yaml
└── Compiler_result
    ├── gen_files
    │   └── graph_0
    │       ├── npu
    │       │   ├── backend
    │       │   │   ├── backend.isa
    │       │   │   ├── back_end_TENSOR_ENGINE_0.bin
    │       │   │   ├── back_end_TENSOR_ENGINE_0_CMDQ
    │       │   │   │   ├── commands.asm
    │       │   │   │   └── commands.bin
    │       │   │   ├── back_end_TENSOR_ENGINE_0.csv
    │       │   │   ├── back_end_TENSOR_ENGINE_0.isa
    │       │   │   ├── back_end_VECTOR_ENGINE_0.bin
    │       │   │   ├── back_end_VECTOR_ENGINE_0_CMDQ
    │       │   │   │   ├── commands.asm
    │       │   │   │   └── commands.bin
    │       │   │   ├── back_end_VECTOR_ENGINE_0.csv
    │       │   │   ├── back_end_VECTOR_ENGINE_0.isa
    │       │   │   ├── merged_const.bin
    │       │   │   ├── ncp.bin
    │       │   │   ├── profile_log.txt
    │       │   │   ├── profile_npue.json
    │       │   │   └── weights.bin
    │       │   ├── frontend
    │       │   │   └── frontend.ir
    │       │   └── middleend
    │       │       └── middle_end.ir
    │       └── npu_config
    ├── main_graph_O2_SingleCore.nnc
    ├── NNCInfo.csv
    ├── nncontainer-gen.txt
    └── profile_log.txt
```

---

## CLI Command Usage
### Command
Additional options can be specified via the debug_str option value in the CLI command.
```bash
$ eais compile --mode tuning_mode --debug_str '-D dram_reduction=true -D weight_comp=true -C remove_redundant_sfr_setting=true'
```

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

### Option Prefix Description
| Abbreviation | Description |
|------|------|
| `-D` | Option passed to Middleend |
| `-C` | Option passed to Backend |
| `-N` | Option passed to logging and System SW |
