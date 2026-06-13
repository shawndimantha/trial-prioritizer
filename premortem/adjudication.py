"""SEAM 3 — the pluggable adjudication layer.

`Verifier` is the interface the loop depends on. `SinglePassVerifier` is today's
implementation: it grades one finding in a FRESH, INDEPENDENT context built from
verifier.md + the full rubric.md + exactly one finding — never the builder's
reasoning (a load-bearing invariant from CLAUDE.md). `AdversarialPanelVerifier`
is the documented "one Opus flex" to build once the single-pass loop runs.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path

from .config import run_tool_loop
from .retrieval import TOOLS, dispatch_tool
from .schemas import Finding, GateResult, Verdict

_ROOT = Path(__file__).resolve().parent.parent
VERIFIER_PROMPT = (_ROOT / "verifier.md").read_text()
RUBRIC = (_ROOT / "rubric.md").read_text()

# Tolerant of "G1: PASS — reason", "G1: FAIL - reason", "G1 PASS: reason".
_GATE_RE = re.compile(r"^\s*G([1-4])\s*[:\-]?\s*(PASS|FAIL)\s*[—\-:]*\s*(.*)$", re.IGNORECASE | re.MULTILINE)


class Verifier(ABC):
    @abstractmethod
    def grade(self, finding: Finding) -> Verdict:
        ...


def _serialize_finding(f: Finding) -> str:
    return (
        f"FINDING_ID: {f.id}\n"
        f"AXIS: {f.axis}\n"
        f"TITLE: {f.title}\n"
        f"VERDICT (claim): {f.verdict}\n"
        f"QUANTITATIVE THRESHOLD: {f.quantitative_threshold}\n"
        f"CITATION: {f.citation.source_id} — {f.citation.title} {f.citation.url}\n"
        f"REMEDIATION: {f.remediation}"
    )


class SinglePassVerifier(Verifier):
    def __init__(self) -> None:
        # verifier.md promises the verifier "has only this rubric, one finding,
        # and tool access" — so the rubric IS concatenated into its context.
        self.system = VERIFIER_PROMPT + "\n\n---\n\n# rubric.md (the grading contract)\n\n" + RUBRIC

    def grade(self, finding: Finding) -> Verdict:
        user = (
            "Grade the following single finding against the rubric. Retrieve the "
            "cited source with your tools to confirm it is real and that the "
            "numbers match.\n\n" + _serialize_finding(finding)
        )
        text, _ = run_tool_loop("verifier", self.system, user, TOOLS, dispatch_tool)
        return self._parse(finding.id, text)

    @staticmethod
    def _parse(finding_id: str, text: str) -> Verdict:
        gates: dict[int, GateResult] = {}
        for m in _GATE_RE.finditer(text):
            n = int(m.group(1))
            passed = m.group(2).upper() == "PASS"
            reason = m.group(3).strip() or "(no reason given)"
            gates[n] = GateResult(passed=passed, reason=reason)

        def g(n: int) -> GateResult:
            # Fail-closed: a gate the verifier didn't report is treated as FAIL.
            return gates.get(n, GateResult(passed=False, reason="gate not found in verifier output — treated as FAIL"))

        return Verdict(finding_id=finding_id, g1=g(1), g2=g(2), g3=g(3), g4=g(4))


class AdversarialPanelVerifier(Verifier):
    """Planned, not yet built. The "one Opus flex" (CLAUDE.md): for each finding,
    spawn N independent red-team subagents in fresh contexts, each tasked to find
    the cheapest counterexample. Kill the finding if a majority refute it. Build
    this once SinglePassVerifier runs end-to-end."""

    def grade(self, finding: Finding) -> Verdict:  # pragma: no cover
        raise NotImplementedError("Adversarial panel verifier: planned, not yet built.")
