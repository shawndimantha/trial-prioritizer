# Trial Pre-Mortem (PSP)

A clinical-trial pre-mortem harness. A **builder** drafts grounded findings about
where a proposed trial will die; an **independent verifier** grades each finding
against [`rubric.md`](rubric.md) in a fresh context and kills any it cannot
substantiate from a retrievable public source. The loop terminates only when the
verifier passes 100% of findings.

See [`CLAUDE.md`](CLAUDE.md) for the architecture and invariants,
[`rubric.md`](rubric.md) for the four gates, and [`verifier.md`](verifier.md) for
the verifier prompt.

## This slice

The first working slice (per the CLAUDE.md build order): the four capability-dial
seams, ClinicalTrials.gov retrieval, and the builder→verifier→revise loop closed
on **one hard-coded anti-tau antibody protocol for Axis 3** (mechanism /
translational risk). Three axes and the greenlight pass are not built yet.

## Run

```sh
pip install -e .                 # or: uv pip install -e .
export ANTHROPIC_API_KEY=...     # or put it in .env and source it
python run.py                    # uses protocols/anti_tau_antibody.json
python run.py path/to/other.json # any protocol synopsis
```

It will retrieve real PSP trials (watch for NCT IDs in the run), draft Axis-3
findings, grade each independently, revise failures, and print a ranked kill-list.
Confirmed kills are appended to `memory/kills.jsonl`.

## Layout

```
premortem/
  config.py        SEAM 1 — model-agnostic call site (role -> model) + agentic loop
  job.py           SEAM 2 — queue-able unit of work (one protocol = one Job)
  adjudication.py  SEAM 3 — pluggable verifier (SinglePass now; AdversarialPanel stub)
  memory.py        SEAM 4 — append confirmed kills to memory/kills.jsonl
  retrieval.py     ClinicalTrials.gov v2 tool + web_search / web_fetch
  schemas.py       Finding / Verdict (one field per gate)
  builder.py       drafts + revises Axis-3 findings
  loop.py          builder -> verifier -> revise; computes STATUS
protocols/         hard-coded input synopses
run.py             entry point
```
