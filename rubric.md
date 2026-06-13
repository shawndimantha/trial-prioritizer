# rubric.md — verifier grading rubric

This is the single source of truth the verifier grades against. The verifier sees only this rubric and one finding at a time, in a fresh, independent context — never the builder's reasoning.

## The four gates

A finding stands only if it passes **all four** gates. The verifier returns PASS/FAIL per gate with a one-line reason.

| Gate | Requirement | FAIL trigger |
| --- | --- | --- |
| **G1 Grounding** | Cites a specific, retrievable public source (NCT ID, named FDA guidance, published trial). | Vague / unnamed / unretrievable source → hallucination risk. |
| **G2 Entailment** | Verdict follows from the cited data; numbers match the source. | Verdict overstates / misstates the source. |
| **G3 Quantification** | Verdict carries a quantitative threshold (e.g., "powered for 30% PSPRS slowing; comparable trials saw 0% despite engagement"). | Qualitative-only ("seems risky"). |
| **G4 Remediation** | Specific, actionable fix tied to the flaw — or a reasoned "do not run." | Generic ("rethink the mechanism") with no concrete change. |

## Completion gate

Every finding across all three axes must pass G1–G4. The verifier emits one machine-readable line that the loop reads to decide whether to continue:

```
STATUS: PASS
```
or
```
STATUS: FAIL [finding_ids]
```

That line is the human-free definition of "done." When `STATUS: FAIL [finding_ids]` is emitted, the builder revises **only** the listed findings and the loop returns to the verifier. The loop terminates only on `STATUS: PASS`.
