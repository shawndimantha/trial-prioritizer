# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

Greenfield. As of this writing the repository contains only this file — no code, build, or test scaffolding exists yet. This document is the spec future instances build against. When you add tooling (package manager, test runner, data-fetch scripts), record the actual build/lint/test commands here, including how to run a single test.

## What this is

An agent that takes a proposed clinical trial protocol synopsis and tells a drug developer whether it's worth running and where it will die — a **pre-mortem**, not a dashboard. It does not score-and-display. It reasons: proposes findings, critiques them against real public data, kills weak elements, and returns either a revised defensible protocol or the verdict **"do not run this trial as designed,"** naming what would have to change.

**Indication v1: Progressive Supranuclear Palsy (PSP)** — a 4-repeat (4R) tauopathy, fatal, no disease-modifying therapy, the modern tau-drug trial graveyard. The indication is a **parameter**: swapping it (ALS, FTD, other rare neuro) reruns the same three-axis structure. Preserve that parameterization — it is the orchestration story, not a v2 nicety.

Buyer: clinical-development strategists / biotech execs in rare neurodegeneration deciding whether to greenlight a program, and translational investors sizing risk.

## Core architecture — builder + verifier loop

```
INPUT protocol synopsis
   │
   ▼
BUILDER (Opus 4.8) ── retrieves public data, drafts per-axis findings,
   │  findings        proposes verdicts + remediations
   ▼
VERIFIER (FRESH context, Opus 4.8) ── grades each finding against rubric.md
   │                                    in an INDEPENDENT context → PASS/FAIL + reason
   │
 any FAIL? ──yes──► builder revises ONLY failed findings ──► (loop to verifier)
   │
   no
   ▼
emit kill-list + (revised protocol | "do not run")
```

Two invariants that define the product. Do not erode them for convenience:

1. **The verifier runs in a fresh, independent context.** It sees only the rubric and one finding — never the builder's reasoning. Independent grading beats self-critique; this is the whole point. Do not pass builder rationale into the verifier's context.
2. **The builder may not mark itself done.** Completion is gated by the verifier passing 100% of findings. "Done" is verifiable without a human.

**Context wiring.** The verifier's prompt is `verifier.md`; it promises the verifier "has only this rubric, one finding, and tool access." Honor that literally: the verifier context = `verifier.md` + the full contents of `rubric.md` + exactly one finding. Concatenate `rubric.md` in (the prompt says "this rubric"). Pass nothing from the builder — not its rationale, not other findings, not the input synopsis beyond what the single finding restates.

## The three stress-test axes

Every finding belongs to one axis and must be grounded in a retrievable public source.

- **Axis 1 — Population / enrollment feasibility.** Will it enroll, on what timeline, given a rare heterogeneous population? Ground truth: ClinicalTrials.gov comparable PSP trials (planned vs actual N, sites, duration, status), PSP prevalence (~5–7/100,000), MDS-PSP 2017 diagnostic criteria, phenotype distribution (Richardson syndrome vs variants). Failure mode: over-narrow eligibility collapses an already-tiny pool; too-broad admits heterogeneity that washes out signal; misdiagnosis inflates screen-fail rates.
- **Axis 2 — Endpoint & powering validity.** Is the primary endpoint defensible, and is the trial powered for a realistic effect in a noisy, declining population? Ground truth: PSPRS as standard primary, published progression rates/variances, FDA posture (no approved DMT → endpoint path open but unvalidated), biomarker status (CSF/plasma tau, NfL, tau-PET are engagement/secondary, **not** validated surrogates). Failure mode: powering on an optimistic slowing effect against a noisy scale at small N; leaning on a biomarker as if it were an approvable surrogate.
- **Axis 3 — Mechanism / translational risk (the killer axis — make this the deepest).** Does engaging this target plausibly translate to benefit, given what already failed? Ground truth: the anti-tau graveyard — gosuranemab (Biogen, PASSPORT), tilavonemab (AbbVie), davunetide (Allon), tideglusib (GSK-3). Several engaged the target and showed no clinical benefit. Sharpest catch: a new program targeting extracellular N-terminal tau inherits PASSPORT/tilavonemab's failure mode — flag **"target engagement ≠ clinical benefit here; these specific trials proved it"** and demand a differentiated translational rationale (different tau species e.g. seed-competent MTBR tau, total-tau lowering via ASO, or earlier intervention window). No differentiated answer → "do not run."

## Grounding gate (G1) — non-negotiable

**Verify all trial landmarks live.** Pull NCT IDs and exact results during the build via live retrieval — do not trust this file's or the model's recall of trial names, numbers, or outcomes. Live retrieval is what makes the verifier meaningful; grounding is gate G1. A finding that cannot cite a retrievable public source FAILs, whether it's a risk or an optimistic remediation.

All four gates are defined in **`rubric.md`** — the single source of truth the verifier grades against: G1 Grounding, G2 Entailment (verdict follows from cited data, numbers match), G3 Quantification (carries a quantitative threshold, not qualitative "seems risky"), G4 Remediation (specific actionable fix or reasoned "do not run"). The verifier emits one machine-readable line — `STATUS: PASS` or `STATUS: FAIL [finding_ids]` — that the loop reads to decide whether to continue. On FAIL, the builder revises only the listed findings. That line is the human-free definition of "done."

## The greenlight pass — kill-list to defensible yes

After the kill-list, run the **same builder→verifier loop a second time, constructively**: for each fatal finding the builder proposes a remediation that is itself a finding subject to the same gates (this is the G4 remediation field). Output is a greenlight configuration whose every surviving claim passed the verifier — or, only if nothing survives, a hard "do not run."

**The rule that protects the build: the path to yes clears the same evidentiary bar as the kill.** Optimism that can't be grounded in a retrievable source is a FAIL, exactly like a hallucinated risk. This is architecturally free — it reuses the loop and the remediation field.

Two greenlight levers:
- **Repurposing** (attacks Axis 3, collapses IND burden): an approved drug brings known safety/PK/tox and can target a differentiated mechanism vs the dead antibodies. Ground each candidate in three retrievable facts — existing approval, mechanistic link to 4R-tau/neurodegeneration, prior human signal. Illustrative candidates to verify live: salsalate (tau-acetylation), lithium (GSK-3β). Confirm status/results via G1.
- **Better IND design** (attacks Axis 2 and the engagement-≠-benefit trap): biomarker-gated go/no-go interim; earlier therapeutic window; phenotype enrichment (Richardson syndrome); adaptive/Bayesian design; built-in futility gate. Each lever is a verifier-gradeable claim, not a vibe.

**Scope guardrail:** build the kill loop first; add the greenlight pass only once one axis closes end-to-end. If time is short, greenlight on Axis 3 alone (repurposing + differentiated mechanism) is the highest-value slice.

## Capability dial — four seams (build these before logic)

This is a **harness with a capability dial**, not an app: today bounded by Opus 4.8, architected so raising the dial (a long-horizon model later) raises the ceiling *without a rewrite*. Build four seams from the first commit — they are interfaces, not features; cheap now, expensive to retrofit:

1. **Model-agnostic call site.** Builder, verifier, and planner roles each get their model from config, not hardcoded. Swapping models is a config flag, never a refactor. *(Do this first — ~10 min.)*
2. **Queue-able unit of work.** One protocol = one job on a queue. One protocol in the demo today → an entire portfolio run unattended tomorrow, same code.
3. **Pluggable verifier / adjudication layer.** Today a single-pass grader behind an interface, so a one-shot verifier can be swapped for an adversarial panel by config.
4. **Memory as an outer loop.** Every kill appends a reusable failure pattern to a file (e.g. "N-terminal extracellular tau engagement → no PSP benefit; generalizes to target-engagement-without-downstream-effect"). Sharpens within a run today; compounds into institutional pre-mortem memory across runs. This is the actual moat.

**The one Opus flex to build (after the basic loop runs):** make the verifier **adversarial** — a red-team subagent in an independent context whose job is to find the cheapest counterexample to each finding before it stands. It elevates the loop you already have and is the clearest "beyond basic integration" beat. Optional higher-wow stretches — pick **at most one**, only if Axis 3 is already solid: long-context corpus synthesis (reason across the entire PSP trial landscape at once — empirical enrollment-rate distribution across every interventional PSP trial — not RAG over one chunk), or vision (read a Kaplan-Meier curve / forest plot out of a trial PDF).

**Discipline:** judges score what *runs*. Build the working Axis-3 loop first, add the adversarial verifier as the one flex, wire the four seams (cheap), and *talk* the long-horizon future using the seams as evidence. Do not let future-proofing become the reason the working slice isn't done.

## Build order (don't skip)

1. **Wire the four seams before logic** (config/interfaces, ~15 min total; retrofitting later is the expensive path).
2. The spec files (`CLAUDE.md`, `rubric.md`, `verifier.md`) are already in place.
3. **Wire ClinicalTrials.gov retrieval first** of the actual logic — grounding is the whole game; a verifier with nothing to retrieve is theater.
4. **Hard-code ONE input protocol synopsis** — an anti-tau antibody design is the natural choice (it sets up the Axis-3 catch). Do not build an input UI.
5. **Close the builder→verifier→revise loop on a single Axis-3 finding** before scaling to all three axes. One axis working end-to-end beats three half-built.
6. Only once that loop runs: make the verifier adversarial. Everything beyond — other axes, a second model role, the optional long-context/vision stretch — is gravy, added in priority order against the clock.

## Public data sources (all open)

- **ClinicalTrials.gov** (public API) — comparable PSP trials: N, sites, duration, status, endpoints, results.
- **FDA** guidance/approvals — neurodegeneration endpoints; note PSP has no approved DMT.
- **Published trial results** — PASSPORT (gosuranemab), tilavonemab, davunetide, tideglusib.
- **MDS-PSP 2017 diagnostic criteria** — eligibility realism.
- **Prevalence / registries** — PSP epidemiology; patient orgs (e.g. CurePSP).

Always retrieve live and cite NCT IDs / source titles rather than relying on memory.
