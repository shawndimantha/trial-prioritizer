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

function findingCard(f, opts) {
  const prov = opts && opts.provisional && f.axis !== "3"
    ? ` <span class="prov">(provisional)</span>` : "";
  return el("div", "finding",
    `<div class="head">
       <span class="fid">[${esc(f.id)}]</span>
       <span class="axis">Axis-${esc(f.axis)} · ${esc(AXIS[f.axis] || "")}${prov}</span>
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

function isFallback(d) {
  return !!(d && (d.kind === "fallback" || d.catch || d.bar_holds));
}

async function render(data) {
  seq++; const my = seq; stage.innerHTML = "";
  try {
    if (isFallback(data)) await renderFallback(data, my);
    else await renderFixture(data, my);
  } catch (e) {
    if (live(my)) stage.appendChild(el("div", "fail mono", "render error: " + esc(String(e))));
  }
}

async function renderFixture(data, my) {
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

/* ---- the real artifact (fallback shape) ------------------------------- */
/* Renders results/<ts>-fallback.json verbatim as 4 beats:
   kill-list (clean) -> the catch (deterministic G2 kill of the AMX0035 overclaim)
   -> the bar holds (scaled-back claim still fails G2) -> DO NOT RUN.
   Nothing here is invented: every gate verdict comes from the JSON. Beats the
   spec marks as DROPPED (salsalate/lithium, surviving levers, kill-pass revise,
   catch-as-live-builder) are deliberately absent. */

async function gradeBlock(my, o) {
  const fail = o.verdictKind === "fail";
  const block = add(el("div", "verifier " + (fail ? "failblock" : "passblock")));
  block.appendChild(el("div", "cmd", o.header));
  await pace(170); if (!live(my)) return;
  for (const g of o.gates) {
    const ok = g.passed;
    const row = el("div", "gate",
      `<span class="g">${g.key.toUpperCase()}</span>
       <span class="gname">${GATE_LABEL[g.key] || ""}</span>
       <span class="res ${ok ? "pass" : "fail"}">${ok ? "PASS" : "FAIL"}</span>
       <span class="reason">${esc(g.reason || "")}</span>`);
    block.appendChild(row);
    if (!skip) row.scrollIntoView({ behavior: "smooth", block: "nearest" });
    await pace(130); if (!live(my)) return;
  }
  block.appendChild(el("div", "verdict " + (fail ? "fail" : "pass"), o.verdictText));
  await pace(220);
}

function provLine(text) {
  const n = el("div", "prov-log faint mono", text);
  return n;
}

function constructiveCard(ca) {
  const ids = ca.proposed_remediation_ids || [];
  const axisOf = (id) => (String(id).match(/^[A-Za-z](\d)/) || [])[1] || "?";
  const rows = ids.map((id) =>
    `<div class="prow"><span class="pid">${esc(id)}</span>` +
    `<span class="paxis">axis ${esc(axisOf(id))}</span>` +
    `<span class="pverdict">— no survival verdict</span></div>`).join("");
  return el("div", "incomplete",
    `<div class="ih">&#9888; ${ids.length} remediations proposed across all three axes · grounded · ` +
    `<span class="iwarn">verification INTERRUPTED</span></div>
     <div class="ids">${rows}</div>
     <div class="evid">${esc(ca.evidence || "")}</div>
     <div class="istat">${esc(ca.status || "")} — proposed and grounded, <b>not</b> evaluated. ` +
    `No pass/fail was recorded for these; they are not surviving levers.</div>`);
}

function dnrBanner(dnr) {
  return el("div", "dnr",
    `<div class="dnrhead">${esc(dnr.status || "DO NOT RUN AS DESIGNED")}</div>
     <div class="dnrbody">Repurposing could not be grounded for PSP / 4R-tau: the AMX0035 efficacy
       pitch was rejected on G2, and so was a deliberately scaled-back, efficacy-agnostic version —
       the bar holds. Remediations proposed across all three axes were not verified before the run
       was interrupted. When no remediation clears the bar, the loop returns DO NOT RUN.</div>
     <div class="dnrnote faint">the do-not-run branch fires deterministically; its stub inputs only
       prove the branch triggers — they are not real levers.</div>`);
}

async function renderFallback(data, my) {
  document.getElementById("indication").textContent = "/ PSP";
  document.getElementById("engine").textContent =
    "replay · " + (data.kind || "run") + (data.assembled_from ? " · " + data.assembled_from : "");
  const prov = data.provenance || {};

  phase("&#9655;", "persisted real run · replay", "default demo path · network-flake-proof");
  const banner = add(el("div", "dim mono"));
  banner.style.cssText = "font-size:11.5px;margin-top:-4px";
  banner.textContent = "Assembled from proven, captured results — no live API call required.";
  await pace(440); if (!live(my)) return;

  // BEAT 1 — the kill-list (clean; no per-gate verdicts in the artifact)
  const kl = data.kill_list || [];
  phase("1", "kill-list · the substantiated case", `${kl.length} findings · kill side passed clean`);
  await pace(220); if (!live(my)) return;
  for (const f of kl) { add(findingCard(f, { provisional: true })); await pace(280); if (!live(my)) return; }

  // BEAT 2 + 3 — greenlight: the catch, then the bar holds
  phase("2", "greenlight · does any repurposing clear the same bar?", "the path to yes clears the kill's bar");
  await pace(200); if (!live(my)) return;
  const intro = add(el("div", "dim mono")); intro.style.cssText = "font-size:12px;margin:2px 0 4px";
  intro.textContent = "A remediation must clear the same four gates as the kill. The verifier holds that bar.";
  await pace(300); if (!live(my)) return;

  const cat = data.catch || {};
  if (cat.overclaim) {
    add(el("div", "subhead",
      `the catch <span class="tag">deterministic verifier check — the verifier reliably kills this overclaim; not a live builder pitch</span>`));
    add(findingCard(cat.overclaim));
    await pace(280); if (!live(my)) return;
    const g2 = cat.verifier_g2 || {};
    await gradeBlock(my, {
      header: `$ verify <span class="fid">${esc(cat.overclaim.id)}</span> &nbsp;·&nbsp; deterministic G2 entailment check`,
      gates: [{ key: "g2", passed: !!g2.passed, reason: g2.reason }],
      verdictText: `VERDICT: ${(cat.outcome || "rejected").toUpperCase()} — overclaim killed on G2`,
      verdictKind: "fail",
    });
    if (!live(my)) return;
    if (prov.overclaim_check_log) { add(provLine(`real verifier session log: ${prov.overclaim_check_log}`)); await pace(160); }
  }

  const bh = data.bar_holds || {};
  if (bh.defensible_fixture) {
    add(el("div", "revise",
      `<div class="h">&#8635; scaled back — a deliberately defensible, efficacy-agnostic Phase 2a bridge, re-graded against the same four gates</div>`));
    await pace(340); if (!live(my)) return;
    add(el("div", "subhead",
      `the bar holds <span class="tag">even a hand-written, scaled-back claim is rejected — the verifier doesn't bend to intent</span>`));
    add(findingCard(bh.defensible_fixture));
    await pace(280); if (!live(my)) return;
    const t = bh.verdict_trail || {};
    const gates = GATES.map((k) => ({
      key: k, passed: !!t[k],
      reason: k === "g2" ? (bh.g2_note || "") : "",
    }));
    await gradeBlock(my, {
      header: `$ verify <span class="fid">${esc(bh.defensible_fixture.id)}</span> &nbsp;·&nbsp; re-graded against the same rubric`,
      gates,
      verdictText: `VERDICT: REJECTED — the bar holds (G2)`,
      verdictKind: "fail",
    });
    if (!live(my)) return;
  }

  // Constructive attempt — shown, but visibly incomplete (makes DO NOT RUN earned)
  const ca = data.constructive_attempt;
  if (ca) {
    phase("3", "constructive attempt · proposed across all 3 axes", "grounded · verification interrupted");
    await pace(200); if (!live(my)) return;
    add(constructiveCard(ca));
    await pace(220); if (!live(my)) return;
    if (prov.crashed_greenlight_log) { add(provLine(`crashed-run session log: ${prov.crashed_greenlight_log}`)); await pace(200); }
  }

  // BEAT 4 — DO NOT RUN
  const dnr = data.do_not_run_branch || {};
  phase("4", "verdict · the honest no", "nothing cleared the bar");
  await pace(200); if (!live(my)) return;
  add(dnrBanner(dnr));
  await pace(300); if (!live(my)) return;

  const done = add(el("div", "dim mono"));
  done.style.margin = "22px 0 0";
  done.innerHTML = `<span class="fail">&#9679;</span> replay complete · <b>${esc(dnr.status || "DO NOT RUN AS DESIGNED")}</b> · ` +
    `repurposing rejected on G2 (&times;2) · levers proposed, not verified · nothing cleared the bar`;
}

/* ---- run-live (optional affordance; replay is the default) ------------- */
function wireRunLive() {
  const rl = document.getElementById("runlive");
  if (!rl) return;
  rl.onclick = () => {
    if (document.getElementById("livenote")) return;
    const n = el("div", "livenote mono",
      `<b>Live mode</b> would invoke the engine on the host — the deploy check confirmed ` +
      `<span class="pass">ANTHROPIC_API_KEY</span> present and <span class="pass">ClinicalTrials.gov</span> reachable from egress. ` +
      `This deploy <b>defaults to replay</b> of a persisted real run: a cold live agentic run is slow and can fail mid-talk, ` +
      `and the replayed data is itself real. <a href="#" id="livedismiss">dismiss</a>`);
    n.id = "livenote";
    stage.parentNode.insertBefore(n, stage);
    document.getElementById("livedismiss").onclick = (e) => { e.preventDefault(); n.remove(); };
  };
}

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
wireRunLive();
boot();
