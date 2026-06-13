"""Assemble the FALLBACK demo from already-proven, captured results — fully
offline, no API calls. Produces a coherent session log + results.json the
frontend can replay if the full live greenlight run does not land in time.

Every piece here is real and already observed:
  1. THE CATCH      — the verifier killed the AMX0035 efficacy overclaim on G2
                      (deterministic check; real verdict reason, verbatim).
  2. THE BAR HOLDS  — even a hand-written "defensible" version was rejected on G2
                      for lacking a grounded PSP/4R-tau link (verifier enforcing
                      the bar independent of intent).
  3. CONSTRUCTIVE   — the builder grounded and proposed 7 remediations across
                      Axes 1/2/3 before an infra timeout interrupted verification.
  4. DO-NOT-RUN     — the honest-no branch fires deterministically when nothing
                      clears the bar.

    python build_fallback.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from premortem.greenlight import run_greenlight
from premortem.log import current_path, log, new_session
from premortem.schemas import Citation, Finding, FindingSet, GateResult, Verdict
from verify_overclaim_catch import DEFENSIBLE, OVERCLAIM

ROOT = Path(__file__).resolve().parent
KILL_LIST = ROOT / "protocols" / "naive_nterminal_killlist.json"
RESULTS_DIR = ROOT / "results"

# --- Real, captured verifier output (verbatim from the deterministic check) ---
OVERCLAIM_G2_REASON = (
    "Verdict claims ~25% PSPRS slowing in PSP, but the source is an ALS trial; it "
    "does not entail a PSP effect, and the finding misrepresents a Phase 2 result "
    "(later refuted by the failed Phase 3 PHOENIX and market withdrawal) as a "
    '"pivotal" benefit.'
)
# Defensible fixture's recorded gate trail: G1:PASS G2:FAIL G3:PASS G4:PASS
DEFENSIBLE_TRAIL = {"g1": True, "g2": False, "g3": True, "g4": True}
DEFENSIBLE_G2_NOTE = (
    "Rejected on G2 for asserting repurposing value without a grounded mechanistic "
    "link to PSP / 4R-tau — the verifier holds the bar even against a hand-written "
    "scaled-back claim."
)
# Real remediation IDs the builder grounded + proposed before the infra timeout.
PROPOSED_IDS = ["A3-1", "A3-2", "A3-3", "A2-1", "A2-2", "A3-4", "A1-1"]
PROPOSED_EVIDENCE = (
    "builder grounded via clinicaltrials_lookup + web_search + web_fetch across "
    "AMX0035/CENTAUR, PHOENIX, plasma NfL enrichment, mPSPRS-15 power, Richardson "
    "enrichment, and tilavonemab futility (see crashed-run session log)"
)


def _verdict_dict(v: Verdict) -> dict:
    return {
        "finding_id": v.finding_id,
        "passed": v.passed,
        "g1": v.g1.model_dump(),
        "g2": v.g2.model_dump(),
        "g3": v.g3.model_dump(),
        "g4": v.g4.model_dump(),
    }


def main() -> None:
    kill_list = [Finding(**f) for f in json.loads(KILL_LIST.read_text())]

    new_session(label="fallback-demo")
    log("FALLBACK DEMO — assembled from proven, captured results (offline).")
    log(f"SESSION log: {current_path()}")

    # 0. The kill-list this design produced (real input to the greenlight pass).
    log("\n" + "=" * 72)
    log("KILL-LIST (the substantiated case against the naive N-terminal design)")
    log("=" * 72)
    for f in kill_list:
        tag = f"Axis-{f.axis}" + (" (provisional)" if f.axis != "3" else "")
        log(f"  [{f.id}] {tag} (lethality {f.lethality}/5) {f.title}")

    # 1. THE CATCH — verifier kills the AMX0035 efficacy overclaim on G2.
    log("\n" + "=" * 72)
    log("GREENLIGHT CATCH — the verifier kills an overclaimed repurposing pitch")
    log("=" * 72)
    log(f"  proposed remediation: {OVERCLAIM.title}")
    log(f"  optimistic claim:     {OVERCLAIM.verdict}")
    log(f"  verifier G2: FAIL — {OVERCLAIM_G2_REASON}")
    log("  -> overclaim REJECTED. Optimism that outran the evidence dies on the "
        "same gate that kills a hallucinated risk.")

    # 2. THE BAR HOLDS — even the scaled-back version was rejected on G2.
    log("\n" + "=" * 72)
    log("THE BAR HOLDS — even a scaled-back repurposing claim is rejected")
    log("=" * 72)
    trail = " ".join(f"G{i+1}:{'PASS' if DEFENSIBLE_TRAIL[g] else 'FAIL'}"
                     for i, g in enumerate(("g1", "g2", "g3", "g4")))
    log(f"  proposed remediation: {DEFENSIBLE.title}")
    log(f"  verifier: {trail}")
    log(f"  G2 note: {DEFENSIBLE_G2_NOTE}")

    # 3. CONSTRUCTIVE ATTEMPT — builder grounded 7 remediations across axes.
    log("\n" + "=" * 72)
    log("CONSTRUCTIVE ATTEMPT — builder proposed grounded remediations across axes")
    log("=" * 72)
    log(f"  proposed: {', '.join(PROPOSED_IDS)} (Axes 1/2/3)")
    log(f"  evidence: {PROPOSED_EVIDENCE}")
    log("  status:   verification interrupted by an infra read-timeout before "
        "completion (since fixed via streaming).")

    # 4. DO-NOT-RUN BRANCH — fires deterministically when nothing clears (offline).
    log("\n" + "=" * 72)
    log("DO-NOT-RUN BRANCH — the honest 'no' when no remediation can be grounded")
    log("=" * 72)

    def _f(fid):
        return Finding(id=fid, axis="3", title="ungroundable remediation " + fid,
                       verdict="claim with no retrievable support",
                       quantitative_threshold="n/a",
                       citation=Citation(source_id="none", title="none", url=""),
                       remediation="n/a", lethality=3)

    class _StubBuilder:
        def propose_remediations(self, job, kl):
            return FindingSet(findings=[_f("R-1"), _f("R-2")])

        def revise_remediations(self, job, failed, current):
            return FindingSet(findings=[_f(v.finding_id) for v in failed])

    class _AlwaysFail:
        def grade(self, f):
            return Verdict(finding_id=f.id,
                           g1=GateResult(passed=False, reason="no retrievable source"),
                           g2=GateResult(passed=True, reason="n/a"),
                           g3=GateResult(passed=True, reason="n/a"),
                           g4=GateResult(passed=True, reason="n/a"))

    dnr = run_greenlight(object(), [kill_list[0]], _StubBuilder(), _AlwaysFail(), max_iters=2)

    # --- persist results.json ---
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS_DIR / f"{ts}-fallback.json"
    out.write_text(json.dumps({
        "kind": "fallback",
        "assembled_from": "proven, captured results (no live run required)",
        "kill_list": [f.model_dump() for f in kill_list],
        "catch": {
            "overclaim": OVERCLAIM.model_dump(),
            "verifier_g2": {"passed": False, "reason": OVERCLAIM_G2_REASON},
            "outcome": "rejected",
        },
        "bar_holds": {
            "defensible_fixture": DEFENSIBLE.model_dump(),
            "verdict_trail": DEFENSIBLE_TRAIL,
            "g2_note": DEFENSIBLE_G2_NOTE,
        },
        "constructive_attempt": {
            "proposed_remediation_ids": PROPOSED_IDS,
            "evidence": PROPOSED_EVIDENCE,
            "status": "verification interrupted by infra timeout (since fixed via streaming)",
        },
        "do_not_run_branch": {
            "status": dnr.status,
            "dropped_ids": [f.id for f in dnr.dropped],
            "config_ids": [f.id for f in dnr.config],
        },
        "provenance": {
            "overclaim_check_log": "logs/*overclaim-check.log",
            "crashed_greenlight_log": "logs/20260613T203916Z-greenlight-demo.log",
        },
    }, indent=2))
    log(f"\nresults.json: {out}")
    log(f"(session log: {current_path()})")
    log("\nFALLBACK READY — replayable session log + results.json persisted.")


if __name__ == "__main__":
    main()
