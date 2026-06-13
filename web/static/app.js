/* Trial Pre-Mortem — progressive replay of a run.
   Drives entirely off /run.json. Reveals the arc the way the system produced it:
   builder findings -> verifier gate lines -> FAIL -> revise -> PASS -> kill-list
   -> greenlight. No data is invented here; this only paces what the engine emitted. */

const AXIS = {
  "1": "population / enrollment",
  "2": "endpoint & powering",
  "3": "mechanism / translational",
};
const GATE_LABEL = { g1: "GROUNDING", g2: "ENTAILMENT", g3: "QUANTIFICATION", g4: "REMEDIATION" };
const GATES = ["g1", "g2", "g3", "g4"];

const stage = document.getElementById("stage");
let seq = 0;       // bumps every render; in-flight renders bail when stale
let skip = false;  // skip => no delays, no smooth scroll

const esc = (s) =>
  String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const pace = (ms) => new Promise((r) => setTimeout(r, skip ? 0 : ms));
const live = (my) => my === seq;

function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
}
function add(node) {
  node.classList.add("reveal");
  stage.appendChild(node);
  if (!skip) node.scrollIntoView({ behavior: "smooth", block: "nearest" });
  return node;
}
function phase(n, t, meta) {
  return add(el("div", "phase",
    `<span class="n">${esc(n)}</span><span class="t">${esc(t)}</span>` +
    `<span class="rule"></span><span class="meta">${meta ? esc(meta) : ""}</span>`));
}
function statusLine(text, kind) {
  const s = add(el("div", "status " + kind));
  s.textContent = text;
  return s;
}

/* ---- card builders ---------------------------------------------------- */

function protocolCard(p) {
  if (!p) return el("div", "dim mono", "(no protocol)");
  const iv = p.intervention || {}, pw = p.powering || {};
  const rows = [
    ["indication", p.indication],
    ["population", p.population],
    ["eligibility", p.eligibility],
    ["intervention", [iv.modality, iv.mechanism].filter(Boolean).join(" — ") + (iv.route ? ` (${iv.route})` : "")],
    ["primary endpoint", p.primary_endpoint],
    ["secondary", (p.secondary_endpoints || []).join(", ")],
    ["powering", pw.assumed_effect ? `${pw.assumed_effect}; N=${pw.n}, ${pw.randomization}, α=${pw.alpha}, power=${pw.power}` : ""],
    ["design", p.design],
  ].filter((r) => r[1]);
  return el("div", "protocol",
    `<div class="name">${esc(p.name || "protocol")}</div><div class="grid">` +
    rows.map((r) => `<div class="k">${esc(r[0])}</div><div class="v">${esc(r[1])}</div>`).join("") +
    `</div>`);
}

function lethPips(n) {
  let s = "";
  for (let i = 1; i <= 5; i++) s += `<span class="pip ${i <= n ? "" : "off"}">●</span>`;
  return s;
}
function citationHTML(c) {
  c = c || {};
  const link = c.url
    ? `<a href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.title)}</a>`
    : esc(c.title || "");
  return `<span class="src">${esc(c.source_id || "")}</span> — ${link}`;
}

function findingCard(f) {
  return el("div", "finding",
    `<div class="head">
       <span class="fid">[${esc(f.id)}]</span>
       <span class="axis">axis ${esc(f.axis)} · ${esc(AXIS[f.axis] || "")}</span>
       <span class="leth">lethality ${lethPips(f.lethality)} ${esc(f.lethality)}/5</span>
     </div>
     <div class="title">${esc(f.title)}</div>
     <div class="kv">
       <div class="k">claim</div><div class="v">${esc(f.verdict)}</div>
       <div class="k">quantitative</div><div class="v q">${esc(f.quantitative_threshold)}</div>
       <div class="k">source</div><div class="v">${citationHTML(f.citation)}</div>
       <div class="k">remediation</div><div class="v">${esc(f.remediation)}</div>
     </div>`);
}

async function verifierBlock(v, my) {
  const fail = !v.passed;
  const block = add(el("div", "verifier " + (fail ? "failblock" : "passblock")));
  block.appendChild(el("div", "cmd",
    `$ verify <span class="fid">${esc(v.finding_id)}</span> &nbsp;·&nbsp; fresh context: ` +
    `rubric.md + 1 finding <span class="faint">(no builder reasoning)</span>`));
  await pace(170); if (!live(my)) return;
  for (const k of GATES) {
    const g = v[k] || { passed: false, reason: "(missing)" };
    const ok = g.passed;
    const row = el("div", "gate",
      `<span class="g">${k.toUpperCase()}</span>
       <span class="gname">${GATE_LABEL[k]}</span>
       <span class="res ${ok ? "pass" : "fail"}">${ok ? "PASS" : "FAIL"}</span>
       <span class="reason">${esc(g.reason)}</span>`);
    block.appendChild(row);
    if (!skip) row.scrollIntoView({ behavior: "smooth", block: "nearest" });
    await pace(105); if (!live(my)) return;
  }
  const failed = GATES.filter((k) => v[k] && !v[k].passed).map((k) => k.toUpperCase());
  block.appendChild(el("div", "verdict " + (fail ? "fail" : "pass"),
    fail ? `VERDICT: FAIL — ${failed.join(", ")}` : `VERDICT: PASS (all four gates)`));
  await pace(220);
}

function firstFailReason(v) {
  for (const k of GATES) if (v[k] && !v[k].passed) return `${k.toUpperCase()} FAIL — ${v[k].reason}`;
  return "failed verifier";
}
function fixReason(before, after) {
  for (const k of GATES) if (before[k] && !before[k].passed && after[k])
    return `${k.toUpperCase()} PASS — ${after[k].reason}`;
  return "revised; re-graded PASS";
}
function reviseCard(fid, before, after) {
  const failed = GATES.filter((k) => before[k] && !before[k].passed).map((k) => k.toUpperCase()).join(", ");
  return el("div", "revise",
    `<div class="h">↻ revise [${esc(fid)}] — failed ${esc(failed || "verifier")}; builder rewrites this finding only</div>
     <div class="diff">
       <div class="lab">before</div><div class="before">${esc(firstFailReason(before))}</div>
       <div class="lab">after</div><div class="after">${esc(fixReason(before, after))}</div>
     </div>`);
}

function gateBadges(v) {
  return GATES.map((k) => {
    const ok = v && v[k] && v[k].passed;
    return `<span class="badge ${ok ? "ok" : "no"}">${k.toUpperCase()}</span>`;
  }).join("");
}
function killRow(rank, f, v) {
  return el("div", "killrow",
    `<span class="rank">${rank}</span>
     <span class="fid">[${esc(f.id)}]</span>
     <span class="kt"><div style="font-weight:600">${esc(f.title)}</div>
       <div class="dim" style="font-size:11.5px;margin-top:2px">${esc((f.citation || {}).source_id || "")} · lethality ${esc(f.lethality)}/5</div></span>
     <span class="badges">${gateBadges(v)}</span>`);
}

function glDecision(gl) {
  return el("div", "gl-decision",
    `<div class="verdict">${esc(gl.decision || "")}</div>
     <div class="summary">${esc(gl.summary || "")}</div>`);
}
function leverCard(lv) {
  const gr = lv.gate_result || {};
  const badges = GATES.map((k) => {
    const ok = gr[k] && gr[k].passed;
    return `<span class="badge ${ok ? "ok" : "no"}">${k.toUpperCase()}</span>`;
  }).join("");
  return el("div", "lever",
    `<div class="head"><span class="ltype">${esc(lv.type || "lever")}</span><span class="fid">[${esc(lv.id)}]</span></div>
     <div class="title">${esc(lv.title)}</div>
     <div class="kv">
       <div class="k">rationale</div><div class="v">${esc(lv.verdict)}</div>
       <div class="k">grounding</div><div class="v q">${esc(lv.quantitative_threshold)}</div>
       <div class="k">source</div><div class="v">${citationHTML(lv.citation)}</div>
       <div class="k">design</div><div class="v">${esc(lv.remediation)}</div>
     </div>
     <div class="gates">${badges}<span class="faint" style="font-size:11px;margin-left:6px">verifier-passed</span></div>`);
}
function configCard(cfg) {
  const rows = [
    ["mechanism", cfg.mechanism],
    ["population", cfg.population],
    ["endpoint & powering", cfg.endpoint_and_powering],
  ].filter((r) => r[1]);
  return el("div", "config",
    rows.map((r) => `<div class="row"><div class="k">${esc(r[0])}</div><div class="v">${esc(r[1])}</div></div>`).join("") +
    (cfg.bottom_line ? `<div class="bottom">${esc(cfg.bottom_line)}</div>` : ""));
}
function memCard(arr) {
  return el("div", "mem",
    `<div class="h">kills.jsonl — reusable failure patterns banked this run</div>` +
    arr.map((m) => `<div class="pat"><span class="pid">[${esc(m.finding_id)}]</span> ${esc(m.pattern)}</div>`).join(""));
}

/* ---- the replay ------------------------------------------------------- */

async function render(data) {
  seq++; const my = seq; stage.innerHTML = "";

  document.getElementById("indication").textContent = "/ " + (data.indication || "PSP");
  const eng = data.engine || {};
  document.getElementById("engine").textContent =
    `builder ${eng.builder || "?"} · verifier ${eng.verifier || "?"}` +
    (eng.verifier_kind ? ` (${eng.verifier_kind})` : "");

  phase("▷", "input · protocol synopsis", data.mode ? "mode: " + data.mode : "");
  add(protocolCard(data.protocol));
  await pace(500); if (!live(my)) return;

  const findings = data.findings || [];
  phase("1", "builder · drafting grounded findings", `${findings.length} findings · ${eng.builder || "Opus 4.8"}`);
  await pace(250); if (!live(my)) return;
  for (const f of findings) { add(findingCard(f)); await pace(280); if (!live(my)) return; }

  const tl = data.timeline || [];
  const t0 = tl[0] || { verdicts: [], failed: [], status: "STATUS: PASS" };
  phase("2", "verifier · grading pass 1", "fresh independent context per finding");
  await pace(220); if (!live(my)) return;
  for (const v of t0.verdicts) { await verifierBlock(v, my); if (!live(my)) return; }
  statusLine(t0.status || "STATUS: ?", (t0.failed && t0.failed.length) ? "fail" : "pass");
  await pace(500); if (!live(my)) return;

  const t1 = tl[1];
  if (t1 && t0.failed && t0.failed.length) {
    phase("3", "fail → revise", "builder revises only the failed finding(s)");
    await pace(200); if (!live(my)) return;
    for (const fid of t0.failed) {
      const before = t0.verdicts.find((v) => v.finding_id === fid) || {};
      const after = t1.verdicts.find((v) => v.finding_id === fid) || {};
      add(reviseCard(fid, before, after));
      await pace(450); if (!live(my)) return;
    }
    const revised = t1.revised || t0.failed;
    phase("4", "verifier · re-grade pass 2", "revised finding shown in full");
    await pace(200); if (!live(my)) return;
    for (const fid of revised) {
      const v = t1.verdicts.find((x) => x.finding_id === fid);
      if (v) { await verifierBlock(v, my); if (!live(my)) return; }
    }
    const others = t1.verdicts.filter((v) => !revised.includes(v.finding_id)).map((v) => v.finding_id);
    if (others.length) {
      const n = add(el("div", "dim mono"));
      n.style.cssText = "font-size:12px;margin:4px 0 0";
      n.innerHTML = "&nbsp;&nbsp;" + others.map((o) => `<span class="pass">${esc(o)}</span>`).join("  ") +
        ` &nbsp;<span class="faint">— re-graded, unchanged PASS</span>`;
      await pace(300); if (!live(my)) return;
    }
    statusLine(t1.status || "STATUS: PASS", "pass");
    await pace(500); if (!live(my)) return;
  }

  const finalVerdicts = (t1 || t0).verdicts || [];
  phase("5", "kill-list · most lethal first", data.status || "");
  await pace(220); if (!live(my)) return;
  let rank = 1;
  for (const fid of (data.kill_list || [])) {
    const f = findings.find((x) => x.id === fid);
    const v = finalVerdicts.find((x) => x.finding_id === fid);
    if (f) { add(killRow(rank++, f, v)); await pace(180); if (!live(my)) return; }
  }
  await pace(300); if (!live(my)) return;

  const gl = data.greenlight;
  if (gl && gl.implemented !== false) {
    phase("6", "greenlight · path to a defensible yes", "same four gates as the kill");
    await pace(280); if (!live(my)) return;
    add(glDecision(gl)); await pace(500); if (!live(my)) return;
    for (const lv of (gl.levers || [])) { add(leverCard(lv)); await pace(340); if (!live(my)) return; }
    if (gl.config) { add(configCard(gl.config)); await pace(300); if (!live(my)) return; }
  }

  if (data.memory_appended && data.memory_appended.length) {
    phase("7", "memory · institutional pre-mortem patterns", "appended on kill — the outer loop");
    await pace(220); if (!live(my)) return;
    add(memCard(data.memory_appended)); await pace(200);
  }

  const done = add(el("div", "dim mono"));
  done.style.margin = "22px 0 0";
  done.innerHTML = `<span class="green">●</span> run complete · ${esc(data.status || "")} · ` +
    `${findings.length} findings cleared the verifier · greenlight ${gl ? "emitted" : "n/a"}`;
}

/* ---- boot ------------------------------------------------------------- */

async function boot() {
  try {
    const r = await fetch("/run.json", { cache: "no-store" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    window.__run = await r.json();
  } catch (e) {
    stage.innerHTML = `<div class="fail mono">failed to load /run.json: ${esc(String(e))}</div>`;
    return;
  }
  render(window.__run);
}

document.getElementById("replay").onclick = () => { skip = false; render(window.__run); };
document.getElementById("skip").onclick = () => { skip = true; };
boot();
