# Trial Pre-Mortem (PSP)

## The problem

In rare neurodegeneration, a single clinical trial costs years and nine figures —
and program after program has died re-running a mechanism that **already failed**,
sometimes despite demonstrably hitting its molecular target. Progressive
Supranuclear Palsy (PSP), a 4-repeat tauopathy with no disease-modifying therapy,
is the clearest example: a string of anti-tau antibody trials engaged the target
and produced **zero clinical benefit**. The most valuable thing a tool can tell a
drug developer is often *"do not run this trial as designed"* — before the spend,
not after.

This is a **pre-mortem**, not a dashboard. Given a protocol synopsis (population,
mechanism, endpoints, powering, design), it doesn't score-and-display — it
**reasons**: it proposes findings about where the trial will die, critiques them
against public ground truth, and **kills any finding it cannot substantiate from a
retrievable source.** The output is a ranked kill-list plus either a defensible
redesign or a reasoned "do not run."

## Who it's for

Clinical-development strategists and biotech execs in rare neurodegeneration
deciding whether to greenlight a program, and translational investors sizing the
risk — the people about to commit years and capital to a mechanism that may have
already failed in disguise.

## How it works

A **builder** (Opus 4.8) retrieves public data (ClinicalTrials.gov v2 +
web search/fetch) and drafts per-axis findings. An **independent verifier**
grades each finding in a **fresh context** against [`rubric.md`](rubric.md)'s four
gates — G1 grounding, G2 entailment, G3 quantification, G4 remediation — and the
loop terminates only when the verifier passes 100% of findings. The verifier sees
only the rubric and one finding, never the builder's reasoning, so it doesn't bend
to intent. A second, constructive **greenlight pass** then proposes remediations
that are themselves findings held to the *same* bar: optimism that can't be
grounded dies exactly like a hallucinated risk.

See [`CLAUDE.md`](CLAUDE.md) for the architecture and invariants,
[`rubric.md`](rubric.md) for the gates, and [`verifier.md`](verifier.md) for the
verifier prompt.

**What a real run shows:** on a naive N-terminal anti-tau design, the kill-list is
grounded in the actual graveyard (gosuranemab/PASSPORT, tilavonemab), and the
greenlight pass holds the line — the verifier rejects even a scaled-back
repurposing pitch for lacking a grounded PSP/4R-tau mechanistic link, and when no
remediation clears the bar it returns **DO NOT RUN AS DESIGNED**. The rigor is the
point.

## This slice

Indication v1 is **PSP**, and the indication is a parameter — the same three-axis
structure reruns on other rare neuro (ALS, FTD). Built so far: the four
capability-dial seams, ClinicalTrials.gov retrieval, the builder→verifier→revise
**kill loop** and the constructive **greenlight pass**, closed end-to-end on
**Axis 3** (mechanism / translational risk). Axes 1 and 2 (population; endpoint &
powering) and the adversarial-panel verifier are scaffolded but not built out.
This is a focused proof, not a complete product.

## Run (engine)

```sh
pip install -e .                 # or: uv pip install -e .
export ANTHROPIC_API_KEY=...     # or put it in .env (gitignored)
python run.py                    # uses protocols/anti_tau_antibody.json
python run.py protocols/naive_nterminal.json   # the naive-design seed
```

It retrieves real PSP trials (watch the NCT IDs stream in the log), drafts Axis-3
findings, grades each independently, revises failures, prints a ranked kill-list,
then runs the greenlight pass. Confirmed kills append to `memory/kills.jsonl`;
each run writes a human-readable session log to `logs/`.

## Web replay (`web/`)

[`web/`](web/) is a small, self-contained Flask app that **replays a persisted
run** as a public page — the kill → revise → greenlight arc exactly as the engine
produced it. It does not modify or import the engine; it reads a run JSON
(`web/runs/*.json`, newest wins). It carries a real persisted run so the page is
self-contained, exposes a `/health` check (API key present? ClinicalTrials.gov
reachable?), and deploys to Railway from inside `web/`. See
[`web/README.md`](web/README.md) for local run and deploy steps.

## Layout

```
premortem/
  config.py        SEAM 1 — model-agnostic call site (role -> model) + agentic loop
  job.py           SEAM 2 — queue-able unit of work (one protocol = one Job)
  adjudication.py  SEAM 3 — pluggable verifier (SinglePass now; AdversarialPanel stub)
  memory.py        SEAM 4 — append confirmed kills to memory/kills.jsonl
  retrieval.py     ClinicalTrials.gov v2 tool + web_search / web_fetch
  schemas.py       Finding / Verdict (one field per gate)
  builder.py       drafts + revises findings; proposes greenlight remediations
  greenlight.py    constructive pass — remediations graded by the same verifier
  loop.py          builder -> verifier -> revise; computes STATUS
protocols/         input synopses (anti_tau_antibody, naive_nterminal, + kill-list)
run.py             engine entry point (kill loop + greenlight)
web/               replay + deploy frontend (reads a persisted run JSON)
```
