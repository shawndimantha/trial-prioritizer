"""Deterministic pin on the verifier's behavior: it must reliably KILL an AMX0035
efficacy overclaim on G2, and reliably PASS the defensible scaled-back version.

This uses hand-constructed findings (fixed input) so the catch is reproducible. It
does NOT feed the live demo — the live FAIL->revise->PASS in demo_greenlight.py is
produced organically by the builder. This script only guarantees the verifier's
discrimination is reliable, so the live beat isn't luck.

    python verify_overclaim_catch.py
"""

from __future__ import annotations

from premortem.adjudication import SinglePassVerifier
from premortem.log import log, new_session
from premortem.schemas import Citation, Finding

# The overclaim: quantified PSP efficacy extrapolated from ALS data. Should FAIL G2.
OVERCLAIM = Finding(
    id="GL-AMX-OVER",
    axis="3",
    title="Repurpose AMX0035 — expected to slow PSPRS by ~25%",
    verdict="AMX0035 (sodium phenylbutyrate-taurursodiol) will slow PSPRS progression by "
    "about 25% in this PSP trial, based on the survival and functional benefit it "
    "demonstrated in its pivotal ALS program.",
    quantitative_threshold="~25% slowing of PSPRS decline, extrapolated from the ~25% slowing "
    "of ALSFRS-R decline / survival benefit reported in CENTAUR.",
    citation=Citation(source_id="CENTAUR / AMX0035 ALS program",
                      title="AMX0035 in ALS (CENTAUR)",
                      url="https://www.nejm.org/doi/full/10.1056/NEJMoa1916945"),
    remediation="Adopt AMX0035 at the ALS dose as the intervention and power for a 25% PSPRS effect.",
    lethality=5,
)

# The defensible scaled-back version: safety/PK known, efficacy unproven in tauopathy,
# proposed as a Phase 2a PD bridge. Should PASS.
DEFENSIBLE = Finding(
    id="GL-AMX-OK",
    axis="3",
    title="Repurpose AMX0035 as a Phase 2a safety/PD bridge — efficacy unproven in tauopathy",
    verdict="AMX0035 brings established human safety and PK from its ALS development and a "
    "mechanism distinct from N-terminal tau binding; its clinical efficacy in PSP or any "
    "tauopathy is unproven, and its ALS Phase 3 did not confirm benefit. It is justified only "
    "as a lean Phase 2a safety/biomarker bridge, not a pivotal PSPRS efficacy bet.",
    quantitative_threshold="No PSP efficacy claim. Phase 2a (~n=40) powered for a biomarker PD "
    "readout (CSF/plasma NfL change), with PSPRS as exploratory only — not powered for a PSPRS effect.",
    citation=Citation(source_id="AMX0035 ALS development program",
                      title="AMX0035 ALS safety/PK record and Phase 3 outcome",
                      url="https://www.nejm.org/doi/full/10.1056/NEJMoa1916945"),
    remediation="Run AMX0035 as a biomarker-gated Phase 2a (NfL/tau-PET go/no-go) before any "
    "efficacy trial; do not claim or power for a PSPRS effect on ALS-derived data.",
    lethality=3,
)


def main() -> None:
    new_session(label="overclaim-check")
    verifier = SinglePassVerifier()

    log("\n=== DETERMINISTIC CHECK: verifier must KILL the AMX0035 efficacy overclaim ===")
    v_over = verifier.grade(OVERCLAIM)
    log(f"  overclaim verdict: G2={'PASS' if v_over.g2.passed else 'FAIL'} — {v_over.g2.reason}")
    log(f"  overall passed: {v_over.passed}")

    log("\n=== DETERMINISTIC CHECK: verifier must PASS the defensible scaled-back version ===")
    v_ok = verifier.grade(DEFENSIBLE)
    trail = " ".join(f"G{n}:{'PASS' if g.passed else 'FAIL'}"
                     for n, g in ((1, v_ok.g1), (2, v_ok.g2), (3, v_ok.g3), (4, v_ok.g4)))
    log(f"  defensible verdict: {trail} — overall passed: {v_ok.passed}")

    ok = (not v_over.passed) and (not v_over.g2.passed) and v_ok.passed
    log("\nRESULT: " + ("PASS — verifier reliably kills the overclaim on G2 and passes the "
                        "defensible version." if ok else
                        "UNEXPECTED — review above; the catch did not behave as required."))


if __name__ == "__main__":
    main()
