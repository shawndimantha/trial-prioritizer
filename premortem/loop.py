"""The builder -> verifier -> revise loop. Terminates only when the verifier
passes 100% of findings (STATUS: PASS) — the builder cannot mark itself done.
The STATUS line is computed here by aggregating each finding's per-gate VERDICT
into the rubric.md completion gate."""

from __future__ import annotations

from dataclasses import dataclass

from .adjudication import Verifier
from .builder import Builder
from .log import log
from .memory import append_kill
from .schemas import Finding, FindingSet, Verdict


def _trail(v: Verdict) -> str:
    return " ".join(
        f"G{n}:{'PASS' if gr.passed else 'FAIL'}"
        for n, gr in ((1, v.g1), (2, v.g2), (3, v.g3), (4, v.g4))
    )


@dataclass
class Result:
    status: str  # "STATUS: PASS" or "STATUS: FAIL [ids]"
    kill_list: list[Finding]
    verdicts: list[Verdict]
    iterations: int
    greenlight: object = None  # GreenlightResult | None (attached by run_job)


def run_premortem(job, builder: Builder, verifier: Verifier, max_iters: int = 5) -> Result:
    log(f"BUILDER: drafting Axis-3 findings for protocol: {job.protocol.get('name', '(unnamed)')}")
    findings = builder.draft_findings(job).findings
    log(f"BUILDER: drafted {len(findings)} finding(s): {', '.join(f.id for f in findings)}")
    verdicts: list[Verdict] = []
    status = "STATUS: FAIL"
    iterations = 0

    for iterations in range(1, max_iters + 1):
        log(f"\n--- VERIFICATION PASS {iterations} (independent context per finding) ---")
        verdicts = []
        for f in findings:
            v = verifier.grade(f)
            verdicts.append(v)
            log(f"   [{f.id}] {_trail(v)}  {'PASS' if v.passed else 'FAIL'}: {f.title}")
            for reason in v.failed_gate_reasons():
                log(f"        ✗ {reason}")
        failed = [v for v in verdicts if not v.passed]
        if not failed:
            status = "STATUS: PASS"
            log(f"\n{status}  — all {len(findings)} finding(s) cleared the verifier.")
            break

        # On FAIL the builder revises ONLY the failed findings; we merge by id.
        failed_ids = [v.finding_id for v in failed]
        log(f"\nSTATUS: FAIL [{', '.join(failed_ids)}] — builder will revise these.")
        log(f"BUILDER: revising {len(failed)} finding(s): {', '.join(failed_ids)}")
        revised = builder.revise(job, failed, FindingSet(findings=findings)).findings
        by_id = {f.id: f for f in findings}
        for rf in revised:
            by_id[rf.id] = rf
        findings = list(by_id.values())
    else:
        failed_ids = ", ".join(v.finding_id for v in verdicts if not v.passed)
        status = f"STATUS: FAIL [{failed_ids}] (max iterations reached)"
        log(f"\n{status}")

    # Rank surviving findings most-lethal-first into the kill-list.
    kill_list = sorted(findings, key=lambda f: -f.lethality)

    if status == "STATUS: PASS":
        verdict_by_id = {v.finding_id: v for v in verdicts}
        for f in kill_list:
            append_kill(f, verdict_by_id[f.id])

    return Result(status=status, kill_list=kill_list, verdicts=verdicts, iterations=iterations)
