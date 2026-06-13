"""The builder -> verifier -> revise loop. Terminates only when the verifier
passes 100% of findings (STATUS: PASS) — the builder cannot mark itself done.
The STATUS line is computed here by aggregating each finding's per-gate VERDICT
into the rubric.md completion gate."""

from __future__ import annotations

from dataclasses import dataclass

from .adjudication import Verifier
from .builder import Builder
from .memory import append_kill
from .schemas import Finding, FindingSet, Verdict


@dataclass
class Result:
    status: str  # "STATUS: PASS" or "STATUS: FAIL [ids]"
    kill_list: list[Finding]
    verdicts: list[Verdict]
    iterations: int


def run_premortem(job, builder: Builder, verifier: Verifier, max_iters: int = 5) -> Result:
    findings = builder.draft_findings(job).findings
    verdicts: list[Verdict] = []
    status = "STATUS: FAIL"
    iterations = 0

    for iterations in range(1, max_iters + 1):
        verdicts = [verifier.grade(f) for f in findings]
        failed = [v for v in verdicts if not v.passed]
        if not failed:
            status = "STATUS: PASS"
            break

        # On FAIL the builder revises ONLY the failed findings; we merge by id.
        revised = builder.revise(job, failed, FindingSet(findings=findings)).findings
        by_id = {f.id: f for f in findings}
        for rf in revised:
            by_id[rf.id] = rf
        findings = list(by_id.values())
    else:
        failed_ids = ", ".join(v.finding_id for v in verdicts if not v.passed)
        status = f"STATUS: FAIL [{failed_ids}] (max iterations reached)"

    # Rank surviving findings most-lethal-first into the kill-list.
    kill_list = sorted(findings, key=lambda f: -f.lethality)

    if status == "STATUS: PASS":
        verdict_by_id = {v.finding_id: v for v in verdicts}
        for f in kill_list:
            append_kill(f, verdict_by_id[f.id])

    return Result(status=status, kill_list=kill_list, verdicts=verdicts, iterations=iterations)
