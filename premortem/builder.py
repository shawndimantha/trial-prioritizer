"""The BUILDER. Retrieves public data, drafts per-axis findings, and revises only
the findings the verifier failed. This slice covers Axis 3 (mechanism /
translational risk) — the killer axis.

The builder works in two phases so structured output and tool use don't collide:
  A) an agentic tool loop that gathers live evidence and writes a free-text dossier,
  B) a tool-free structuring call that turns the dossier into a validated FindingSet.
"""

from __future__ import annotations

import json

from .config import parse_model, run_tool_loop
from .retrieval import TOOLS, dispatch_tool
from .schemas import FindingSet, Verdict

AXIS3_SYSTEM = """You are the BUILDER in a clinical-trial pre-mortem. Your job is to \
find where a proposed trial will die — not to cheerlead it. This pass covers \
AXIS 3 — MECHANISM / TRANSLATIONAL RISK, the deepest axis.

The question: does engaging this target plausibly translate to clinical benefit, \
GIVEN WHAT HAS ALREADY FAILED in this indication?

Ground truth you must check LIVE with your tools (never from memory):
- The anti-tau graveyard in PSP: gosuranemab (Biogen, PASSPORT), tilavonemab \
(AbbVie), davunetide (Allon), tideglusib. Several DEMONSTRATED TARGET ENGAGEMENT \
(e.g. lowered N-terminal CSF tau) and still showed NO clinical benefit.
- Use clinicaltrials_lookup to pull exact NCT IDs, planned vs actual enrollment, \
status, why-stopped, and posted results. Use web_search / web_fetch for FDA \
posture and published trial outcomes.

Your sharpest catch: a program that engages EXTRACELLULAR N-TERMINAL TAU by the \
same logic inherits the failure mode of PASSPORT / tilavonemab. Flag it plainly: \
"target engagement != clinical benefit here; these specific trials proved it." \
Then demand a differentiated translational rationale — a different tau species \
(e.g. seed-competent microtubule-binding-region tau), total-tau lowering (ASO), \
or an earlier intervention window. If there is no differentiated answer, the \
correct output is "do not run as designed."

Every finding you draft must satisfy four gates (it will be graded by an \
independent verifier against rubric.md):
- G1 GROUNDING: cite a specific, retrievable source (a real NCT ID you retrieved, \
named FDA guidance, or a published trial). Cite only what you actually retrieved.
- G2 ENTAILMENT: your claim must follow from what the source says; numbers must match.
- G3 QUANTIFICATION: carry a concrete numeric threshold or comparison, not "seems risky".
- G4 REMEDIATION: a specific, actionable fix — or a reasoned "do not run" with \
stated conditions.

Investigate with your tools now. Then write a dossier: for each finding give a \
title, the claim, the quantitative threshold/comparison, the exact source \
(NCT ID / title / URL), a remediation, and how lethal it is (1-5)."""

GREENLIGHT_SYSTEM = """You are the BUILDER running the GREENLIGHT pass. The kill \
loop has already shown why this trial dies. Your job now is to construct the path \
to YES — for each fatal element, propose a REMEDIATION that is itself a finding \
subject to the SAME four gates (G1-G4) and graded by the SAME independent verifier.

The one rule that protects this build: the path to yes clears the SAME evidentiary \
bar as the kill. Optimism you cannot ground in a retrievable source FAILs exactly \
like a hallucinated risk. Do NOT pre-hedge your proposals into safety — state the \
strongest defensible case for each lever and let the verifier hold you to the \
evidence. A remediation that cannot be grounded after revision is dropped; if \
nothing survives, the honest output is "do not run as designed."

Levers — ground each LIVE with your tools (clinicaltrials_lookup, web_search, \
web_fetch); cite only what you retrieve:
- REPURPOSING: propose AMX0035 (sodium phenylbutyrate-taurursodiol, also studied \
as ORION/CENTAUR). Make the affirmative case: state AND QUANTIFY the expected \
clinical benefit it would bring to THIS PSP trial, drawn from its strongest prior \
efficacy evidence. (Be specific about the expected PSPRS effect.)
- BIOMARKER-GATED GO/NO-GO: a pre-specified NfL (or tau-PET / CSF tau) interim \
that catches engagement-without-benefit before a full Phase 3.
- ENDPOINT: replace the legacy 28-item PSPRS with a sensitive instrument \
(mPSPRS-15 or CAFS).
- POPULATION: Richardson-syndrome enrichment / earlier-stage enrollment.
- FUTILITY GATE: a pre-specified interim that would have stopped the dead trials \
early (tilavonemab precedent).

Investigate with your tools, then write a dossier. For each remediation give: the \
lever (title), the optimistic claim of what it buys (this is graded by G2), the \
quantitative basis (G3), the exact source (G1 — NCT ID / title / URL), the concrete \
protocol change it implies (G4), and an impact score 1-5 (5 = decisive)."""

STRUCTURE_SYSTEM = """You convert a pre-mortem evidence dossier into structured \
findings. Preserve the evidence faithfully — do not invent citations or numbers \
not present in the dossier. Use stable ids like 'A3-1', 'A3-2'. Assign each \
finding its TRUE axis: '1' = population / enrollment feasibility, '2' = endpoint \
& powering validity (sample size, MCID, choice of rating scale), '3' = mechanism \
/ translational risk. Most findings in this Axis-3 pass are '3'; honestly label \
powering / sample-size / endpoint-instrument findings as '2'. lethality is 1-5 \
(5 = fatal)."""


def _protocol_brief(job) -> str:
    return "PROPOSED PROTOCOL SYNOPSIS:\n" + json.dumps(job.protocol, indent=2)


def _killlist_brief(kill_list) -> str:
    blocks = []
    for f in kill_list:
        blocks.append(
            f"[{f.id}] (Axis-{f.axis}) {f.title}\n"
            f"   why fatal: {f.verdict}\n"
            f"   threshold: {f.quantitative_threshold}"
        )
    return "FATAL ELEMENTS FROM THE KILL-LIST (each needs a grounded remediation):\n\n" + "\n\n".join(blocks)


class Builder:
    def __init__(self, role: str = "builder") -> None:
        self.role = role

    def draft_findings(self, job) -> FindingSet:
        user = _protocol_brief(job) + "\n\nRun your Axis-3 pre-mortem on this protocol."
        dossier, _ = run_tool_loop(self.role, AXIS3_SYSTEM, user, TOOLS, dispatch_tool)
        return self._structure(dossier)

    def revise(self, job, failed: list[Verdict], current: FindingSet) -> FindingSet:
        by_id = {f.id: f for f in current.findings}
        blocks = []
        for v in failed:
            f = by_id[v.finding_id]
            reasons = "\n   - ".join(v.failed_gate_reasons())
            blocks.append(
                f"[{f.id}] {f.title}\n"
                f"  current claim: {f.verdict}\n"
                f"  current citation: {f.citation.source_id} — {f.citation.title}\n"
                f"  failed gates:\n   - {reasons}"
            )
        user = (
            _protocol_brief(job)
            + "\n\nThe independent verifier FAILED the findings below. Re-investigate "
            "with your tools (retrieve live sources to fix grounding/entailment) and "
            "produce CORRECTED findings ONLY for these ids, keeping the same id "
            "values. Address every failed gate.\n\n" + "\n\n".join(blocks)
        )
        dossier, _ = run_tool_loop(self.role, AXIS3_SYSTEM, user, TOOLS, dispatch_tool)
        return self._structure(dossier)

    def _structure(self, dossier: str) -> FindingSet:
        return parse_model(self.role, STRUCTURE_SYSTEM, dossier, FindingSet)

    # --- Greenlight pass (constructive; same gates, same verifier) ---

    def propose_remediations(self, job, kill_list) -> FindingSet:
        user = (
            _protocol_brief(job) + "\n\n" + _killlist_brief(kill_list)
            + "\n\nConstruct the path to yes: propose grounded remediations as findings."
        )
        dossier, _ = run_tool_loop(self.role, GREENLIGHT_SYSTEM, user, TOOLS, dispatch_tool)
        return self._structure(dossier)

    def revise_remediations(self, job, failed: list[Verdict], current: FindingSet) -> FindingSet:
        by_id = {f.id: f for f in current.findings}
        blocks = []
        for v in failed:
            f = by_id[v.finding_id]
            reasons = "\n   - ".join(v.failed_gate_reasons())
            blocks.append(
                f"[{f.id}] {f.title}\n"
                f"  optimistic claim: {f.verdict}\n"
                f"  source: {f.citation.source_id} — {f.citation.title}\n"
                f"  failed gates:\n   - {reasons}"
            )
        user = (
            _protocol_brief(job)
            + "\n\nThe independent verifier FAILED these proposed remediations under "
            "the same gates that kill a hallucinated risk — your optimism outran the "
            "evidence. Re-ground them (retrieve live) and produce CORRECTED "
            "remediations ONLY for these ids, keeping the same id values. If a "
            "remediation cannot be honestly grounded, scale the claim back to what the "
            "source supports (e.g. known safety / differentiated mechanism rather than "
            "claimed efficacy) — or concede it.\n\n" + "\n\n".join(blocks)
        )
        dossier, _ = run_tool_loop(self.role, GREENLIGHT_SYSTEM, user, TOOLS, dispatch_tool)
        return self._structure(dossier)
