// EAIS SDK 에이전트 화면. 빌드 없는 순수 JS.
"use strict";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

let S = null;          // 서버가 준 세션 요약
let OUT = null;        // 최종 제출 결과
let TAB = "request";
let MODE = "table";    // 3단계 보기: table(표로 설정) | agent(에이전트 질문)

// ── 서버 호출 ──────────────────────────────────────────────────────────
async function api(path, body) {
  const res = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = {};
  try { data = await res.json(); } catch (_) { /* 본문 없음 */ }
  if (!res.ok || data["오류"]) throw new Error(data["오류"] || ("HTTP " + res.status));
  return data;
}

async function act(path, extra) {
  busy(true);
  try {
    S = await api(path, Object.assign({ sid: S.id }, extra || {}));
    render();
  } catch (e) {
    showError(e.message);
  } finally {
    busy(false);
  }
}

function busy(on) {
  document.body.classList.toggle("working", on);
  if (on && MODE === "agent") $("question").innerHTML = '<div class="busy">에이전트가 문서와 모델 정보를 보고 다음 질문을 준비하고 있습니다…</div>';
  $("submit").disabled = on || !S;
}

function toast(msg, level) {
  let t = $("toast");
  if (!t) { t = document.createElement("div"); t.id = "toast"; document.body.appendChild(t); }
  t.className = "toast " + (level || "error");
  t.textContent = msg;
  clearTimeout(t._h);
  t._h = setTimeout(() => { t.className = "toast hide"; }, 3500);
}

function showError(msg) {
  toast(msg);
  if (S) renderQuestion();
}

// ── 상태 ──────────────────────────────────────────────────────────────
async function loadStatus() {
  try {
    const st = await api("/api/status");
    const color = st.llm ? "#35c78a" : "#f0b43c";
    $("status").innerHTML = `<span class="dot" style="background:${color}"></span>` +
      (st.llm ? `LLM ${esc(st.model)}` : "LLM 없음 (규칙 기반)") +
      ` · ${esc(st.sdk)} · MCP ${esc(st.mcp_tool)} @ ${esc(st.mcp_url)}`;
  } catch (e) {
    $("status").textContent = "서버 연결 실패";
  }
}

// ── 업로드 ────────────────────────────────────────────────────────────
function upload(file) {
  if (!/\.(onnx|tflite)$/i.test(file.name)) {
    alertBox("EAIS 는 .onnx 또는 .tflite 모델만 받습니다.");
    return;
  }
  OUT = null;
  $("output").classList.add("hidden");
  $("progress").classList.remove("hidden");
  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/api/upload?name=" + encodeURIComponent(file.name));
  xhr.upload.onprogress = (e) => {
    if (!e.lengthComputable) return;
    const p = Math.round((e.loaded / e.total) * 100);
    $("bar").style.width = p + "%";
    $("ptext").textContent = p < 100 ? `업로드 ${p}%` : "모델 분석 · 첫 질문 준비 중…";
  };
  xhr.onload = () => {
    $("progress").classList.add("hidden");
    let data = {};
    try { data = JSON.parse(xhr.responseText); } catch (_) { /* */ }
    if (xhr.status !== 200 || data["오류"]) {
      alertBox(data["오류"] || "업로드 실패");
      return;
    }
    S = data;
    render();
    $("sec2").scrollIntoView({ behavior: "smooth", block: "start" });
  };
  xhr.onerror = () => { $("progress").classList.add("hidden"); alertBox("업로드 중 연결이 끊겼습니다."); };
  $("bar").style.width = "0";
  $("ptext").textContent = "업로드 0%";
  xhr.send(file);
}

function alertBox(msg) {
  $("model").innerHTML = `<div class="finding error">${esc(msg)}</div>`;
}

// ── 렌더 ──────────────────────────────────────────────────────────────
function render() {
  renderModel();
  renderLog();
  renderQuestion();
  renderSummary();
  renderStages();
  ["sec2", "sec3", "sec4"].forEach((id) => $(id).classList.toggle("locked", !S));
  $("remainBadge").textContent = S && S.remaining ? `(${S.remaining})` : "";
  $("toolbar").classList.toggle("hidden", !S);
  $("advanced").checked = !!(S && S.advanced);
  $("remain").textContent = S ? `남은 질문 ${S.remaining}개` : "";
  $("submit").disabled = !S;
}

function shape(t) { return "[" + t.shape.join(", ") + "]"; }

function renderModel() {
  const m = S.model;
  const opset = m.opset ? Object.entries(m.opset).map(([d, v]) => `${d} ${v}`).join(", ") : "-";
  const ops = opChart(m);
  $("model").innerHTML = `
    <table class="kv">
      <tr><td>파일</td><td class="mono">${esc(m.file_name)}</td></tr>
      <tr><td>형식</td><td>${esc(m.format.toUpperCase())} · ${(m.size_bytes / 1048576).toFixed(2)} MB</td></tr>
      <tr><td>생성</td><td>${esc(m.producer || "-")}</td></tr>
      <tr><td>opset</td><td>${esc(opset)}</td></tr>
      <tr><td>연산자</td><td>${m.op_count}개${m.quantized ? " · 양자화됨" : ""}</td></tr>
      <tr><td>sha256</td><td class="mono">${esc((m.sha256 || "").slice(0, 16))}…</td></tr>
    </table>
    <div class="io">
      <h3>입력 ${m.inputs.length}개</h3>
      ${m.inputs.map((t) => `<div class="t">${esc(t.name)} ${esc(shape(t))} ${esc(t.dtype)}${t.dynamic ? " ⚠동적" : ""} · ${esc(t.layout_guess)}</div>`).join("") || '<div class="empty">읽지 못함</div>'}
      <h3>출력 ${m.outputs.length}개</h3>
      ${m.outputs.slice(0, 6).map((t) => `<div class="t">${esc(t.name)} ${esc(shape(t))} ${esc(t.dtype)}</div>`).join("")}
      <h3>연산자 분포 · ${Object.keys(m.op_types || {}).length}종 ${m.op_count}개</h3>${ops}
    </div>
    ${m.parse_error ? `<div class="finding error">${esc(m.parse_error)}</div>` : ""}
    ${(m.findings || []).map((f) => `<div class="finding ${f.level}">${esc(f.msg)}</div>`).join("")}`;
}

// SDK 3.0 문서 기준으로 눈여겨볼 연산자. 막대 색과 툴팁으로 표시한다
const OP_FLAG = {
  Einsum: ["bad", "downstream 툴체인 미지원 (ContainsEinsumValidator)"],
  QuantizeLinear: ["q", "이미 양자화된 모델 — skip_quantization 검토"],
  DequantizeLinear: ["q", "이미 양자화된 모델 — skip_quantization 검토"],
  QLinearConv: ["q", "양자화 연산자"], QLinearMatMul: ["q", "양자화 연산자"],
  ConvInteger: ["q", "양자화 연산자"], MatMulInteger: ["q", "양자화 연산자"],
  QUANTIZE: ["q", "양자화 연산자"], DEQUANTIZE: ["q", "양자화 연산자"],
};
const OP_TOP = 12;

function opChart(m) {
  const all = Object.entries(m.op_types || {});
  if (!all.length) return '<div class="empty">연산자를 읽지 못했습니다.</div>';
  const total = m.op_count || all.reduce((a, [, v]) => a + v, 0);
  const max = all[0][1];
  const row = ([name, n]) => {
    const [cls, tip] = OP_FLAG[name] || ["", ""];
    const pct = (n / total) * 100;
    return `<div class="oprow ${cls}" title="${esc(tip || name)}">
      <span class="opname">${esc(name)}${tip ? " ⚠" : ""}</span>
      <span class="optrack"><span class="opbar" style="width:${Math.max(2, (n / max) * 100)}%"></span></span>
      <span class="opnum">${n} <em>${pct < 1 ? pct.toFixed(1) : Math.round(pct)}%</em></span>
    </div>`;
  };
  const head = all.slice(0, OP_TOP).map(row).join("");
  const rest = all.slice(OP_TOP);
  // 주의 연산자는 개수가 적어도 접힌 쪽에 숨지 않게 위로 끌어올린다
  const flagged = rest.filter(([k]) => OP_FLAG[k]).map(row).join("");
  const plain = rest.filter(([k]) => !OP_FLAG[k]);
  const more = plain.length
    ? `<details class="opmore"><summary>나머지 ${plain.length}종 보기</summary>${plain.map(row).join("")}</details>` : "";
  return `<div class="opchart">${head}${flagged}${more}</div>`;
}

function renderLog() {
  const box = $("log");
  box.innerHTML = S.log.map((m) => `<div class="msg ${m.role}">${esc(m.text)}</div>`).join("");
  box.scrollTop = box.scrollHeight;
}

function renderQuestion() {
  const q = S.current;
  const box = $("question");
  if (!q) {
    box.innerHTML = `<div class="done">✔ 필요한 질문을 모두 마쳤습니다. 오른쪽 요약을 확인하고 <b>최종 제출</b>을 누르세요.
      ${S.advanced ? "" : "<br>세부 조정이 필요하면 아래 '고급 옵션도 묻기'를 켜세요."}</div>`;
    return;
  }
  const type = q.multi ? "checkbox" : "radio";
  const opts = q.options.map((o, i) => `
    <label class="opt ${o.recommended ? "sel" : ""}">
      <input type="${type}" name="opt" value="${esc(o.key)}" ${o.recommended ? "checked" : ""} data-i="${i}">
      <div>
        <div class="v">${esc(o.label)}${o.recommended ? '<span class="badge">추천</span>' : ""}</div>
        ${o.desc ? `<div class="d">${esc(o.desc)}</div>` : ""}
        ${o.note ? `<div class="n">⚠ ${esc(o.note)}</div>` : ""}
      </div>
    </label>`).join("");
  box.innerHTML = `
    <div class="q">
      <div class="q-label">${esc(q.label)} <span class="mono" style="color:#8a94a8">${esc(q.id)}</span></div>
      <div class="q-text">${esc(q.question)}</div>
      <div class="q-reason"><span class="who">${q.source === "llm" ? "에이전트 추천 이유" : "문서 기준 (LLM 미사용)"}</span>${esc(q.reason)}</div>
      <div class="q-doc">📄 <a href="${esc(q.doc.url)}" target="_blank" rel="noopener">${esc(q.doc.title)}</a> › ${esc(q.doc.section)} · 기본값 <span class="mono">${esc(q.default)}</span></div>
      ${opts ? `<div class="opts">${opts}</div>` : ""}
      <div class="custom">
        <div class="row">
          <div>
            <label>원하는 선택지가 없으면 직접 입력 (입력하면 위 선택보다 우선합니다)</label>
            <textarea id="custom" placeholder="${esc(q.placeholder)}"></textarea>
          </div>
          <div>
            <label>메모 (선택) — SDK 요청의 user_notes 로 함께 전달됩니다</label>
            <input id="note" placeholder="예) 실제 데이터셋은 다음 주에 교체 예정">
          </div>
        </div>
      </div>
      <div class="actions">
        <button class="primary" id="ok">답변</button>
        <button class="ghost" id="skip">기본값으로 넘어가기</button>
      </div>
      ${S.llm_error ? `<div class="err">${esc(S.llm_error)}</div>` : ""}
    </div>`;
  box.querySelectorAll(".opt input").forEach((el) => el.addEventListener("change", () => {
    box.querySelectorAll(".opt").forEach((l) => l.classList.toggle("sel", l.querySelector("input").checked));
  }));
  $("ok").onclick = submitAnswer;
  $("skip").onclick = () => act("/api/skip", { id: q.id });
  $("custom").addEventListener("keydown", (e) => { if (e.key === "Enter" && e.ctrlKey) submitAnswer(); });
}

function submitAnswer() {
  const q = S.current;
  const custom = $("custom").value.trim();
  const note = $("note").value.trim();
  const picked = [...document.querySelectorAll(".opt input:checked")].map((el) => el.value);
  if (!custom && !picked.length) {
    showError("선택지를 고르거나 직접 입력해 주세요.");
    return;
  }
  act("/api/answer", { id: q.id, choice: q.multi ? picked : picked[0], custom, note });
}

const SRC = { option: "선택", input: "직접 입력", custom: "문서 밖 값", "custom→option": "입력→선택지", default: "기본값" };

function renderSummary() {
  const changed = S.answers.filter((a) => a.source !== "default");
  if (!changed.length) {
    $("summary").innerHTML = '<div class="empty">아직 바꾼 값이 없습니다. 모두 문서 기본값으로 요청합니다.</div>';
    return;
  }
  $("summary").innerHTML = changed.map((a) => `
    <div class="ans">
      <div class="top2">
        <span class="l">${esc(a.label)}<span class="src ${esc(a.source)}">${esc(SRC[a.source] || a.source)}</span></span>
        <button class="edit" data-id="${esc(a.id)}">수정</button>
      </div>
      <div class="v">${esc(a.value)}</div>
      ${a.comment ? `<div class="c">${esc(a.comment)}</div>` : ""}
      ${a.note ? `<div class="c" style="color:#6b7489">메모: ${esc(a.note)}</div>` : ""}
    </div>`).join("");
  $("summary").querySelectorAll(".edit").forEach((b) =>
    b.addEventListener("click", () => gotoParam(b.dataset.id)));
}

function gotoParam(id) {
  // 요약의 [수정] → 3단계 표에서 그 파라미터 행으로 이동해 강조한다
  const st = S.stages.find((x) => x.params.some((r) => r.id === id));
  if (!st) return;
  STAGE = st.id;
  setMode("table");
  renderStages();
  const row = document.querySelector(`tr[data-row="${CSS.escape(id)}"]`);
  if (row) {
    row.scrollIntoView({ behavior: "smooth", block: "center" });
    row.classList.add("flash");
    setTimeout(() => row.classList.remove("flash"), 1600);
  }
}

// ── 최종 제출 ──────────────────────────────────────────────────────────
async function submitAll() {
  $("submit").disabled = true;
  try {
    OUT = await api("/api/submit", { sid: S.id });
    TAB = "request";
    renderOutput();
    $("output").classList.remove("hidden");
    $("output").scrollIntoView({ behavior: "smooth" });
  } catch (e) {
    showError(e.message);
  } finally {
    $("submit").disabled = false;
  }
}

function code(caption, text, name) {
  return `<div class="codebox"><div class="cap">${esc(caption)}</div>
    <button class="copy" data-copy="${esc(name)}">복사</button><pre>${esc(text)}</pre></div>`;
}

function renderOutput() {
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === TAB));
  const blobs = {};
  let html = "";
  const add = (caption, text, name) => { blobs[name] = text; html += code(caption, text, name); };
  if (TAB === "request") {
    const n = OUT.warnings.filter((w) => w.level === "error").length;
    if (n) html += `<div class="finding error">점검 결과에 오류 ${n}건이 있습니다. [점검 결과] 탭을 확인하세요.</div>`;
    add(`POST ${OUT.http.url}  —  request.json`, JSON.stringify(OUT.request, null, 2), "request");
  } else if (TAB === "http") {
    add("HTTP 헤더", Object.entries(OUT.http.headers).map(([k, v]) => `${k}: ${v}`).join("\n"), "headers");
    add("curl (Streamable HTTP: initialize → initialized → tools/call)", OUT.http.curl, "curl");
  } else if (TAB === "files") {
    Object.entries(OUT.files).forEach(([path, text], i) => add(path, text, "file" + i));
  } else if (TAB === "cli") {
    add("eais CLI 로 직접 실행할 때", OUT.cli.join("\n"), "cli");
  } else if (TAB === "warnings") {
    html = `<div class="warnlist">${OUT.warnings.length
      ? OUT.warnings.map((w) => `<div class="finding ${w.level}">${esc(w.msg)}</div>`).join("")
      : '<div class="finding ok">문서 규칙상 문제를 찾지 못했습니다.</div>'}</div>`;
  } else if (TAB === "tool") {
    add("SDK MCP 쪽에 있어야 할 도구 정의 (tools/list 형식)", JSON.stringify(OUT.tool_spec, null, 2), "tool");
  }
  $("tabbody").innerHTML = html;
  $("tabbody").querySelectorAll(".copy").forEach((b) => b.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(blobs[b.dataset.copy]); b.textContent = "복사됨"; }
    catch (_) { b.textContent = "복사 실패"; }
    setTimeout(() => { b.textContent = "복사"; }, 1200);
  }));
}

// ── 단계별 설정 ──────────────────────────────────────────────────────
let STAGE = "init";
let PREVIEW = null;    // 업로드 전 미리보기용 단계 목록 (/api/stages)
const LEVEL = { basic: "기본", advanced: "고급", auto: "자동" };

function renderStages() {
  const stages = (S && S.stages) || PREVIEW;
  if (!stages) return;
  const num = (st) => stages.indexOf(st) + 1;

  // 2. 실행 단계 선택 — 카드 전체가 체크박스 라벨
  $("stepper").innerHTML = stages.map((st, i) => `
    ${i ? '<span class="arrow">→</span>' : ""}
    <label class="step ${st.enabled ? "on" : "off"}" title="${esc(st.desc)}">
      <input type="checkbox" class="stepchk" data-toggle="${esc(st.id)}" ${st.enabled ? "checked" : ""} ${S ? "" : "disabled"}>
      <div>
        <div class="stepn">${num(st)} · ${esc(st.id)} <span class="need ${esc(st.need)}">${esc(st.need)}</span></div>
        <div class="stept">${esc(st.title)}</div>
        <code class="stepcmd">${esc(st.cmd.replace(" --w <workspace>", ""))}</code>
      </div>
    </label>`).join("");
  $("stepper").querySelectorAll(".stepchk").forEach((el) => el.addEventListener("change", toggleStep));

  // 3. 단계별 설정 — 선택한 단계만 탭으로 (업로드 전 미리보기는 전부)
  const tabs = S ? stages.filter((st) => st.enabled) : stages;
  if (!tabs.some((st) => st.id === STAGE)) STAGE = tabs.length ? tabs[0].id : null;
  $("stageTabs").innerHTML = tabs.map((st) => `
    <button class="stab ${st.id === STAGE ? "sel" : ""}" data-stage="${esc(st.id)}">
      <b>${num(st)}. ${esc(st.id)}</b> <span>${esc(st.title)}</span>
      <em>${st.active_count}개${st.changed ? ` · 변경 ${st.changed}` : ""}</em>
    </button>`).join("") || '<div class="empty">2단계에서 실행할 단계를 하나 이상 고르세요.</div>';
  $("stageTabs").querySelectorAll(".stab").forEach((b) => b.addEventListener("click", () => {
    STAGE = b.dataset.stage;
    renderStages();
  }));
  const cur = tabs.find((st) => st.id === STAGE);
  if (cur) renderStageBody(cur); else $("stagebody").innerHTML = "";
}

function toggleStep(e) {
  // 문서 순서를 지키며 실행 단계 목록(pipeline.steps)을 다시 만든다
  const id = e.target.dataset.toggle;
  const steps = S.stages.filter((st) => (st.id === id ? e.target.checked : st.enabled)).map((st) => JSON.stringify(st.id));
  if (!steps.length) { e.target.checked = true; return; }
  act("/api/set", { id: "pipeline.steps", choice: steps });
}

function editor(r) {
  if (!r.editable) return `<span class="mono">${esc(r.value)}</span><div class="pdesc">비밀값은 받지 않습니다</div>`;
  if (r.type === "multi") {
    return `<div class="multi">${r.options.map((o) => `
      <label title="${esc(o.desc)}"><input type="checkbox" data-multi="${esc(r.id)}" value="${esc(o.key)}"
        ${(r.values || []).includes(o.key) ? "checked" : ""}> ${esc(o.label)}</label>`).join("")}</div>`;
  }
  if (r.options.length) {
    const known = r.options.some((o) => o.key === r.value_key);
    const custom = r.type !== "bool";
    return `<select data-id="${esc(r.id)}">
        ${r.options.map((o) => `<option value="${esc(o.key)}" ${o.key === r.value_key ? "selected" : ""}>${esc(o.label)}${o.desc ? " — " + esc(o.desc.length > 38 ? o.desc.slice(0, 38) + "…" : o.desc) : ""}${o.key === r.default_key && !/기본/.test(o.desc) ? " (기본)" : ""}</option>`).join("")}
        ${custom ? `<option value="__custom__" ${known ? "" : "selected"}>직접 입력…</option>` : ""}
      </select>
      <input class="cust ${known ? "hidden" : ""}" data-custom="${esc(r.id)}" value="${known ? "" : esc(r.value)}" placeholder="값 입력 후 Enter">`;
  }
  return `<input class="cust" data-custom="${esc(r.id)}" value="${esc(r.value === "null (미적용)" ? "" : r.value)}" placeholder="값 입력 후 Enter">`;
}

function optDesc(r) {
  const o = r.options.find((x) => x.key === r.value_key);
  return o && o.desc ? `<div class="optdesc">▸ ${esc(o.label)}: ${esc(o.desc)}</div>` : "";
}

// 설정 값 칸 색: 기본값 / 선택지에서 바꿈 / 자유 입력 / 문서 선택지 밖
function valClass(r) {
  return { default: "v-default", option: "v-option", "custom→option": "v-option",
           input: "v-input", custom: "v-custom" }[r.source] || "v-default";
}
const LEGEND = `<div class="legend">설정 값 색:
  <span class="lg v-default">기본값</span><span class="lg v-option">선택지에서 변경</span>
  <span class="lg v-input">직접 입력</span><span class="lg v-custom">문서 선택지 밖 값</span></div>`;

function paramRow(r) {
  const changed = r.source !== "default";
  return `<tr data-row="${esc(r.id)}" class="${r.active ? "" : "inactive"}">
    <td><div class="pkey mono">${esc(r.key)}</div><div class="pfile">${esc(r.file)}</div></td>
    <td><div class="plabel">${esc(r.label)} <span class="lvl ${esc(r.level)}">${LEVEL[r.level] || r.level}</span></div>
        <div class="pdesc">${esc(r.desc)}</div>${optDesc(r)}
        ${!r.active && r.condition ? `<div class="cond">조건: ${esc(r.condition)}</div>` : ""}
        <a class="pdoc" href="${esc(r.doc.url)}" target="_blank" rel="noopener">📄 ${esc(r.doc.section)}</a></td>
    <td class="mono">${esc(r.default)}</td>
    <td class="ed ${valClass(r)}">${r.active || !S ? editor(r) : `<span class="mono muted">${esc(r.value)}</span>`}</td>
    <td>${changed ? `<span class="src ${esc(r.source)}">${esc(SRC[r.source] || r.source)}</span>
        <button class="edit" data-reset="${esc(r.id)}">기본값으로</button>` : '<span class="src default">기본값</span>'}</td>
  </tr>`;
}

function renderStageBody(st) {
  const shown = st.enabled ? st.params.filter((r) => r.active) : st.params;
  const off = st.enabled ? st.params.filter((r) => !r.active) : [];
  const head = `<tr><th>파라미터 키</th><th>설명</th><th>기본값</th><th>설정 값</th><th>상태</th></tr>`;
  $("stagebody").innerHTML = `
    <div class="stagecard">
      <div class="st-top">
        <div><b>${esc(st.title)}</b> <span class="need ${esc(st.need)}">${esc(st.need)}</span></div>
        <code>${esc(st.cmd)}</code>
      </div>
      <div class="st-desc">${esc(st.desc)}</div>
      <div class="st-out">산출물: ${esc(st.outputs)} · <a href="${esc(st.doc_url)}" target="_blank" rel="noopener">📄 ${esc(st.section_title)}</a></div>
      ${!S ? '<div class="finding info">문서 기본값 미리보기입니다. 모델 파일을 올리면 모델 입력에 맞춰 채워지고 값을 바꿀 수 있습니다.</div>'
        : st.enabled ? "" : '<div class="finding warn">이 단계는 실행 목록에서 빠져 있어 아래 값이 요청에 들어가지 않습니다. 위 체크박스로 켜면 바꿀 수 있습니다.</div>'}
    </div>
    ${shown.length ? LEGEND : ""}
    ${shown.length ? `<table class="ptable ${st.enabled ? "" : "off"}">${head}${shown.map(paramRow).join("")}</table>`
      : '<div class="empty">이 단계에서 설정할 파라미터가 없습니다.</div>'}
    ${off.length ? `<details class="opmore"><summary>조건 때문에 지금은 쓰지 않는 파라미터 ${off.length}개</summary>
      <table class="ptable">${head}${off.map(paramRow).join("")}</table></details>` : ""}`;

  const body = $("stagebody");
  if (!S) { body.querySelectorAll("select, input, button").forEach((el) => { el.disabled = true; }); return; }
  body.querySelectorAll("select[data-id]").forEach((el) => el.addEventListener("change", () => {
    const inp = el.parentElement.querySelector(".cust");
    if (el.value === "__custom__") { inp.classList.remove("hidden"); inp.focus(); return; }
    act("/api/set", { id: el.dataset.id, choice: el.value });
  }));
  body.querySelectorAll("input[data-custom]").forEach((el) => {
    const commit = () => {
      const v = el.value.trim();
      if (v) act("/api/set", { id: el.dataset.custom, custom: v });
    };
    el.addEventListener("change", commit);          // Enter 와 포커스 이동 모두 change 로 들어온다
  });
  body.querySelectorAll("input[data-multi]").forEach((el) => el.addEventListener("change", () => {
    const id = el.dataset.multi;
    const vals = [...body.querySelectorAll(`input[data-multi="${CSS.escape(id)}"]:checked`)].map((x) => x.value);
    if (!vals.length) { el.checked = true; return; }
    act("/api/set", { id, choice: vals });
  }));
  body.querySelectorAll("[data-reset]").forEach((b) => b.addEventListener("click", () =>
    act("/api/set", { id: b.dataset.reset, choice: "__default__" })));
}

// ── 이벤트 ────────────────────────────────────────────────────────────
$("file").addEventListener("change", (e) => e.target.files[0] && upload(e.target.files[0]));
const drop = $("drop");
["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => e.dataTransfer.files[0] && upload(e.dataTransfer.files[0]));
$("advanced").addEventListener("change", (e) => act("/api/advanced", { on: e.target.checked }));
$("fill").addEventListener("click", () => act("/api/defaults"));
function setMode(mode) {
  MODE = mode;
  document.querySelectorAll("#modeTabs button").forEach((b) => b.classList.toggle("on", b.dataset.mode === mode));
  $("tableView").classList.toggle("hidden", mode !== "table");
  $("agentView").classList.toggle("hidden", mode !== "agent");
  if (mode === "agent" && S) renderQuestion();
}
$("modeTabs").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (b) setMode(b.dataset.mode);
});
$("submit").addEventListener("click", submitAll);
$("tabs").addEventListener("click", (e) => {
  if (e.target.dataset.tab) { TAB = e.target.dataset.tab; renderOutput(); }
});
loadStatus();
api("/api/stages").then((d) => { PREVIEW = d.stages; if (!S) renderStages(); }).catch(() => {});
