"""Isolated greenlight pass on a fixed kill-list — the demo capture for the
back half of the arc. Runs the real builder->verifier loop live (the builder
genuinely proposes remediations, the verifier genuinely grades them), writes the
session log AND a structured results.json so the run can be rehearsed/narrated.

    python demo_greenlight.py

Skips the ~25-45 min kill loop by loading a fixed, real kill-list; the greenlight
beat (overclaim -> G2 FAIL -> revise -> PASS) is fully live.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from premortem.adjudication import SinglePassVerifier
from premortem.builder import Builder
from premortem.greenlight import run_greenlight
from premortem.job import Job
from premortem.log import current_path, log, new_session
from premortem.schemas import Finding

ROOT = Path(__file__).resolve().parent
PROTOCOL = ROOT / "protocols" / "naive_nterminal.json"
KILL_LIST = ROOT / "protocols" / "naive_nterminal_killlist.json"
RESULTS_DIR = ROOT / "results"


def _verdict_dict(v) -> dict:
    return {
        "finding_id": v.finding_id,
        "passed": v.passed,
        "g1": v.g1.model_dump(),
        "g2": v.g2.model_dump(),
        "g3": v.g3.model_dump(),
        "g4": v.g4.model_dump(),
    }


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text())
    kill_list = [Finding(**f) for f in json.loads(KILL_LIST.read_text())]
    job = Job(protocol=protocol, indication=protocol.get("indication", "PSP"))

    new_session(label="greenlight-demo")
    log(f"SESSION log: {current_path()}")
    log(f"GREENLIGHT DEMO on fixed kill-list ({len(kill_list)} fatal elements): "
        f"{', '.join(f.id for f in kill_list)}")

    g = run_greenlight(job, kill_list, Builder(), SinglePassVerifier())

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS_DIR / f"{ts}-greenlight.json"
    out.write_text(json.dumps({
        "protocol": protocol.get("name"),
        "kill_list": [f.model_dump() for f in kill_list],
        "greenlight": {
            "status": g.status,
            "iterations": g.iterations,
            "config": [f.model_dump() for f in g.config],
            "dropped": [f.model_dump() for f in g.dropped],
            "verdicts": [_verdict_dict(v) for v in g.verdicts],
        },
    }, indent=2))
    log(f"\nresults.json: {out}")
    log(f"(session log: {current_path()})")


if __name__ == "__main__":
    main()
