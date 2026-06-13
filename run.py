"""Entry point. Loads the hard-coded anti-tau antibody protocol, runs the
Axis-3 pre-mortem, and prints the kill-list with its gate trail.

    python run.py [path/to/protocol.json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from premortem.job import Job, run_job
from premortem.log import current_path, log, new_session

ROOT = Path(__file__).resolve().parent
DEFAULT_PROTOCOL = ROOT / "protocols" / "anti_tau_antibody.json"


def _print_result(result) -> None:
    log("\n" + "=" * 72)
    log(f"{result.status}   (iterations: {result.iterations})")
    log("=" * 72)
    log("\nKILL-LIST (most lethal first):\n")
    for i, f in enumerate(result.kill_list, 1):
        v = next((x for x in result.verdicts if x.finding_id == f.id), None)
        axis_tag = f"Axis-{f.axis}" + (" (provisional)" if f.axis != "3" else "")
        log(f"{i}. [{f.id}] {axis_tag} (lethality {f.lethality}/5) {f.title}")
        log(f"     claim:       {f.verdict}")
        log(f"     quantitative:{f.quantitative_threshold}")
        log(f"     source:      {f.citation.source_id} — {f.citation.title} {f.citation.url}")
        log(f"     remediation: {f.remediation}")
        if v:
            trail = " ".join(
                f"G{n}:{'PASS' if gr.passed else 'FAIL'}"
                for n, gr in ((1, v.g1), (2, v.g2), (3, v.g3), (4, v.g4))
            )
            log(f"     verifier:    {trail}")
        log()

    if result.status.startswith("STATUS: PASS"):
        log('VERDICT: every finding cleared the verifier. For this design, the '
            'kill-list above is the case for "do not run as designed" until each '
            "item is remediated. (Greenlight pass not yet implemented.)")


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PROTOCOL
    protocol = json.loads(path.read_text())
    new_session(label=path.stem)
    log(f"SESSION log: {current_path()}")
    job = Job(protocol=protocol, indication=protocol.get("indication", "PSP"))
    result = run_job(job)
    _print_result(result)
    log(f"\n(log written to {current_path()})")


if __name__ == "__main__":
    main()
