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
