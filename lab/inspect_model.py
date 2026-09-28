# -*- coding: utf-8 -*-
"""업로드한 모델 파일에서 질문에 필요한 메타정보만 읽는다 (표준 라이브러리만 사용).

onnx / tflite 패키지 없이 파일 형식을 직접 읽는다.
  · ONNX  : protobuf. 가중치(raw_data)는 읽지 않고 seek 으로 건너뛰므로 수 GB 모델도 금방 끝난다.
  · TFLite: flatbuffer. 파일 전체를 mmap 으로 열어 필요한 테이블만 따라간다.

읽는 것: 입력/출력 이름·shape·dtype, opset, 연산자 종류별 개수, 양자화 여부, Einsum 유무.
여기서 찾은 문제(findings)는 SDK 3.0 ModelValidator 규칙을 그대로 옮긴 것이다.
"""

import mmap
import os
import struct

ONNX_DTYPES = {1: "float32", 2: "uint8", 3: "int8", 4: "uint16", 5: "int16", 6: "int32",
               7: "int64", 8: "string", 9: "bool", 10: "float16", 11: "float64",
               12: "uint32", 13: "uint64", 16: "bfloat16"}
TFLITE_DTYPES = {0: "float32", 1: "float16", 2: "int32", 3: "uint8", 4: "int64", 5: "string",
                 6: "bool", 7: "int16", 8: "complex64", 9: "int8", 10: "float64",
                 15: "uint32", 16: "uint16"}
TFLITE_OPS = {0: "ADD", 1: "AVERAGE_POOL_2D", 2: "CONCATENATION", 3: "CONV_2D",
              4: "DEPTHWISE_CONV_2D", 6: "DEQUANTIZE", 9: "FULLY_CONNECTED", 14: "LOGISTIC",
              17: "MAX_POOL_2D", 18: "MUL", 19: "RELU", 22: "RESHAPE", 23: "RESIZE_BILINEAR",
              25: "SOFTMAX", 28: "TANH", 34: "PAD", 39: "TRANSPOSE", 40: "MEAN", 41: "SUB",
              67: "TRANSPOSE_CONV", 97: "RESIZE_NEAREST_NEIGHBOR", 114: "QUANTIZE"}
QUANT_OPS = {"QuantizeLinear", "DequantizeLinear", "QLinearConv", "QLinearMatMul",
             "ConvInteger", "MatMulInteger", "QUANTIZE", "DEQUANTIZE"}


# ── ONNX (protobuf) ───────────────────────────────────────────────────

def _varint(f):
    shift, result = 0, 0
    while True:
        b = f.read(1)
        if not b:
            raise ValueError("파일이 중간에 끝났습니다")
        b = b[0]
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result
        shift += 7


def _fields(f, end):
    """(필드 번호, wire type, 값) 을 낸다. 길이 구분 필드의 값은 (시작 위치, 길이) 다.

    호출한 쪽이 그 구간을 읽든 말든, 다음 필드로 넘어가기 전에 구간 끝으로 seek 한다.
    """
    while f.tell() < end:
        key = _varint(f)
        num, wt = key >> 3, key & 7
        if wt == 0:
            yield num, wt, _varint(f)
        elif wt == 1:
            f.seek(8, 1)
            yield num, wt, None
        elif wt == 5:
            f.seek(4, 1)
            yield num, wt, None
        elif wt == 2:
            ln = _varint(f)
            start = f.tell()
            yield num, wt, (start, ln)
            f.seek(start + ln)
        else:
            raise ValueError("지원하지 않는 protobuf wire type %d" % wt)


def _str(f, span):
    f.seek(span[0])
    return f.read(span[1]).decode("utf-8", "replace")


def _value_info(f, span):
    name, dtype, shape = "", None, []
    for num, _, v in _fields(f, span[0] + span[1]):
        if num == 1:
            name = _str(f, v)
        elif num == 2:                                   # TypeProto
            for tn, _, tv in _fields(f, v[0] + v[1]):
                if tn != 1:                              # tensor_type 만 본다
                    continue
                for sn, _, sv in _fields(f, tv[0] + tv[1]):
                    if sn == 1:
                        dtype = ONNX_DTYPES.get(sv, "type%d" % sv)
                    elif sn == 2:                        # TensorShapeProto
                        for dn, _, dv in _fields(f, sv[0] + sv[1]):
                            if dn != 1:
                                continue
                            dim = "?"
                            for kn, _, kv in _fields(f, dv[0] + dv[1]):
                                if kn == 1:
                                    dim = kv
                                elif kn == 2:
                                    dim = _str(f, kv) or "?"
                            shape.append(dim)
    return {"name": name, "dtype": dtype or "float32", "shape": shape}


def _inspect_onnx(path, info):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        graph, opset = None, {}
        for num, _, v in _fields(f, size):
            if num == 1:
                info["ir_version"] = v
            elif num == 2:
                info["producer"] = _str(f, v)
            elif num == 3:
                info["producer"] = (info.get("producer", "") + " " + _str(f, v)).strip()
            elif num == 7:
                graph = v
            elif num == 8:
                domain, version = "", 0
                for on, _, ov in _fields(f, v[0] + v[1]):
                    if on == 1:
                        domain = _str(f, ov)
                    elif on == 2:
                        version = ov
                opset[domain or "ai.onnx"] = version
        info["opset"] = opset
        if graph is None:
            raise ValueError("ONNX graph 를 찾지 못했습니다")

        ops, inits, inputs, outputs = {}, set(), [], []
        f.seek(graph[0])                                 # 위 루프가 파일 끝까지 갔으므로 graph 시작으로 돌아간다
        for num, _, v in _fields(f, graph[0] + graph[1]):
            if num == 1:                                 # NodeProto
                op = ""
                for nn, _, nv in _fields(f, v[0] + v[1]):
                    if nn == 4:
                        op = _str(f, nv)
                ops[op] = ops.get(op, 0) + 1
            elif num == 2:
                info["graph_name"] = _str(f, v)
            elif num == 5:                               # initializer — 이름만 읽는다
                for tn, _, tv in _fields(f, v[0] + v[1]):
                    if tn == 8:
                        inits.add(_str(f, tv))
            elif num == 11:
                inputs.append(_value_info(f, v))
            elif num == 12:
                outputs.append(_value_info(f, v))
        # IR 3 이하는 initializer 도 graph input 에 들어 있다. 진짜 입력만 남긴다
        info["inputs"] = [i for i in inputs if i["name"] not in inits]
        info["outputs"] = outputs
        info["op_types"] = ops


# ── TFLite (flatbuffer) ───────────────────────────────────────────────

class _FB:
    def __init__(self, buf):
        self.b = buf

    def u32(self, p):
        return struct.unpack_from("<I", self.b, p)[0]

    def i32(self, p):
        return struct.unpack_from("<i", self.b, p)[0]

    def field(self, table, idx):
        """테이블의 idx 번째 필드 절대 위치. 없으면 None."""
        vt = table - self.i32(table)
        vt_size = struct.unpack_from("<H", self.b, vt)[0]
        slot = 4 + 2 * idx
        if slot >= vt_size:
            return None
        off = struct.unpack_from("<H", self.b, vt + slot)[0]
        return table + off if off else None

    def vector(self, pos):
        vec = pos + self.u32(pos)
        return vec + 4, self.u32(vec)

    def tables(self, table, idx):
        pos = self.field(table, idx)
        if pos is None:
            return []
        start, n = self.vector(pos)
        return [start + 4 * i + self.u32(start + 4 * i) for i in range(n)]

    def ints(self, table, idx):
        pos = self.field(table, idx)
        if pos is None:
            return []
        start, n = self.vector(pos)
        return [self.i32(start + 4 * i) for i in range(n)]

    def string(self, table, idx):
        pos = self.field(table, idx)
        if pos is None:
            return ""
        start, n = self.vector(pos)
        return bytes(self.b[start:start + n]).decode("utf-8", "replace")

    def scalar(self, table, idx, fmt, default=0):
        pos = self.field(table, idx)
        return default if pos is None else struct.unpack_from(fmt, self.b, pos)[0]


def _inspect_tflite(path, info):
    with open(path, "rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        fb = _FB(mm)
        model = fb.u32(0)
        info["tflite_version"] = fb.scalar(model, 0, "<I")
        info["producer"] = fb.string(model, 3)
        codes = []
        for oc in fb.tables(model, 1):
            code = max(fb.scalar(oc, 0, "<b"), fb.scalar(oc, 3, "<i"))
            custom = fb.string(oc, 1)
            codes.append(custom or TFLITE_OPS.get(code, "BUILTIN_%d" % code))
        subgraphs = fb.tables(model, 2)
        if not subgraphs:
            raise ValueError("TFLite subgraph 가 없습니다")
        sg = subgraphs[0]
        tensors = fb.tables(sg, 0)

        def tensor(i):
            t = tensors[i]
            shape = fb.ints(t, 0)
            sig = fb.ints(t, 7)
            if sig and len(sig) == len(shape):
                shape = [s if s >= 0 else "?" for s in sig]
            return {"name": fb.string(t, 3),
                    "dtype": TFLITE_DTYPES.get(fb.scalar(t, 1, "<b"), "type?"),
                    "shape": shape}

        info["inputs"] = [tensor(i) for i in fb.ints(sg, 1)]
        info["outputs"] = [tensor(i) for i in fb.ints(sg, 2)]
        ops = {}
        for op in fb.tables(sg, 3):
            idx = fb.scalar(op, 0, "<I")
            name = codes[idx] if idx < len(codes) else "?"
            ops[name] = ops.get(name, 0) + 1
        info["op_types"] = ops
        info["subgraphs"] = len(subgraphs)


# ── 공통 ──────────────────────────────────────────────────────────────

def guess_layout(shape, fmt):
    """입력 shape 으로 dbgen order 를 짐작한다. 모르면 프레임워크 기본값."""
    dims = [d if isinstance(d, int) else None for d in shape]
    ch = (1, 3, 4)
    if len(dims) == 4:
        if dims[1] in ch and dims[3] not in ch:
            return "nchw"
        if dims[3] in ch and dims[1] not in ch:
            return "nhwc"
    if len(dims) == 3:
        if dims[0] in ch and dims[2] not in ch:
            return "chw"
        if dims[2] in ch and dims[0] not in ch:
            return "hwc"
    return "nhwc" if fmt == "tflite" else "nchw"


def _findings(info):
    out = []
    ops = info.get("op_types") or {}
    base = (info.get("opset") or {}).get("ai.onnx")
    if info["format"] == "onnx" and base:
        if 13 <= base <= 21:
            out.append({"level": "ok", "msg": "ONNX opset %d — OpsetVersionValidator 통과 범위(13–21)" % base})
        elif base < 13:
            out.append({"level": "warn", "msg": "ONNX opset %d — conversion 에서 13 으로 자동 변환됩니다" % base})
        else:
            out.append({"level": "error", "msg": "ONNX opset %d — 13–21 범위 밖이라 OpsetVersionValidator 가 실패합니다" % base})
    dyn = [i["name"] for i in info.get("inputs", []) if i.get("dynamic")]
    if dyn:
        out.append({"level": "warn", "msg": "동적 차원이 있는 입력: %s — dbgen shape 에 정수를 지정하고, "
                    "고정 shape 로 다시 export 하는 것을 권합니다 (DynamicInputValidator)" % ", ".join(dyn)})
    if ops.get("Einsum"):
        out.append({"level": "error", "msg": "Einsum 연산자 %d개 — downstream 툴체인이 지원하지 않습니다 "
                    "(ContainsEinsumValidator)" % ops["Einsum"]})
    if info.get("quantized"):
        out.append({"level": "info", "msg": "이미 양자화된 모델로 보입니다 (QDQ/int8) — skip_quantization: true 검토"})
    if len(info.get("inputs", [])) > 1:
        out.append({"level": "info", "msg": "입력이 %d개입니다 — dbgen_spec.yaml 에 입력마다 항목을 씁니다" % len(info["inputs"])})
    return out


def inspect(path, file_name, sha256=None):
    """모델 파일 메타정보. 읽다 실패해도 예외 대신 parse_error 를 채워 돌려준다."""
    stem, ext = os.path.splitext(file_name)
    fmt = {".onnx": "onnx", ".tflite": "tflite"}.get(ext.lower(), "unknown")
    info = {"file_name": file_name, "model_name": stem, "format": fmt,
            "size_bytes": os.path.getsize(path), "sha256": sha256,
            "inputs": [], "outputs": [], "op_types": {}, "parse_error": None}
    try:
        if fmt == "onnx":
            _inspect_onnx(path, info)
        elif fmt == "tflite":
            _inspect_tflite(path, info)
        else:
            info["parse_error"] = "EAIS 입력은 .onnx 또는 .tflite 입니다"
    except (ValueError, struct.error, OSError, IndexError) as exc:
        info["parse_error"] = "모델을 읽지 못했습니다: %s" % exc

    for t in info["inputs"] + info["outputs"]:
        t["dynamic"] = any(not isinstance(d, int) or d <= 0 for d in t["shape"])
    for t in info["inputs"]:
        t["layout_guess"] = guess_layout(t["shape"], fmt)
    ops = info["op_types"]
    info["op_count"] = sum(ops.values())
    info["op_types"] = dict(sorted(ops.items(), key=lambda kv: -kv[1]))
    # TFLite 는 입력이 int8/uint8 이면 full-integer 양자화 모델이다. ONNX 의 uint8 입력은 이미지일 수 있어 보지 않는다
    info["quantized"] = any(op in QUANT_OPS for op in ops) or (
        fmt == "tflite" and any(t["dtype"] in ("int8", "uint8") for t in info["inputs"]))
    info["has_einsum"] = bool(ops.get("Einsum"))
    info["findings"] = _findings(info)
    return info
