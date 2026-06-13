"""SEAM 4 — memory as an outer loop. Every confirmed kill appends a reusable
failure pattern to memory/kills.jsonl. Sharpens the agent within a run today;
compounds into an institutional pre-mortem memory across runs. This is the moat
(CLAUDE.md)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .schemas import Finding, Verdict

KILLS_PATH = Path(__file__).resolve().parent.parent / "memory" / "kills.jsonl"


def append_kill(finding: Finding, verdict: Verdict) -> None:
    KILLS_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "finding_id": finding.id,
        "axis": finding.axis,
        "title": finding.title,
        "pattern": finding.verdict,
        "quantitative": finding.quantitative_threshold,
        "citation": finding.citation.model_dump(),
        "remediation": finding.remediation,
        "lethality": finding.lethality,
        "verifier": {
            "g1": verdict.g1.model_dump(),
            "g2": verdict.g2.model_dump(),
            "g3": verdict.g3.model_dump(),
            "g4": verdict.g4.model_dump(),
        },
    }
    with KILLS_PATH.open("a") as fh:
        fh.write(json.dumps(record) + "\n")
