"""Greenlight pass — the back half of the demo arc. Runs the SAME builder->verifier
loop constructively: each proposed remediation is a Finding graded against the same
rubric.md by the same SinglePassVerifier in a fresh context. Optimism that can't be
grounded FAILs exactly like a hallucinated risk; it is revised or dropped. Output:
a greenlight configuration of verified remediations, or a reasoned "do not run".

No new grading system — reuses Verifier, rubric.md, the Finding schema, and the loop
skeleton from loop.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .adjudication import Verifier
from .builder import Builder
from .log import log
from .loop import _trail
from .schemas import Finding, FindingSet, Verdict


@dataclass
class GreenlightResult:
    status: str  # "GREENLIGHT CONFIGURATION" or "DO NOT RUN AS DESIGNED"
    config: list[Finding]            # surviving, verifier-passed remediations
    dropped: list[Finding] = field(default_factory=list)  # never cleared the bar
    verdicts: list[Verdict] = field(default_factory=list)
    iterations: int = 0


def run_greenlight(job, kill_list, builder: Builder, verifier: Verifier, max_iters: int = 5) -> GreenlightResult:
    log("\n" + "#" * 72)
    log("GREENLIGHT PASS — constructive remediation under the SAME gates")
    log("#" * 72)

    findings = builder.propose_remediations(job, kill_list).findings
    log(f"BUILDER: proposed {len(findings)} remediation(s): {', '.join(f.id for f in findings)}")

    verdicts: list[Verdict] = []
    iterations = 0
    for iterations in range(1, max_iters + 1):
        log(f"\n--- GREENLIGHT VERIFICATION PASS {iterations} (independent context per remediation) ---")
        verdicts = []
        for f in findings:
            v = verifier.grade(f)
            verdicts.append(v)
            log(f"   [{f.id}] {_trail(v)}  {'PASS' if v.passed else 'FAIL'}: {f.title}")
            for reason in v.failed_gate_reasons():
                log(f"        ✗ {reason}")
        failed = [v for v in verdicts if not v.passed]
        if not failed:
            log("\nAll proposed remediations cleared the verifier.")
            break
        failed_ids = [v.finding_id for v in failed]
        log(f"\nFAIL [{', '.join(failed_ids)}] — optimism outran the evidence; builder will revise.")
        log(f"BUILDER: revising {len(failed)} remediation(s): {', '.join(failed_ids)}")
        revised = builder.revise_remediations(job, failed, FindingSet(findings=findings)).findings
        by_id = {f.id: f for f in findings}
        for rf in revised:
            by_id[rf.id] = rf
        findings = list(by_id.values())

    # Survivors are remediations whose latest verdict passed.
    passed_ids = {v.finding_id for v in verdicts if v.passed}
    config = [f for f in findings if f.id in passed_ids]
    dropped = [f for f in findings if f.id not in passed_ids]

    status = "GREENLIGHT CONFIGURATION" if config else "DO NOT RUN AS DESIGNED"
    log(f"\n{status} — {len(config)} verified remediation(s), {len(dropped)} dropped.")

    return GreenlightResult(
        status=status, config=config, dropped=dropped, verdicts=verdicts, iterations=iterations
    )
