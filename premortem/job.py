"""SEAM 2 — the queue-able unit of work. One protocol = one Job. `run_job` is the
single entry the loop runs: one protocol in the demo today, an entire portfolio
run unattended tomorrow, same code."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Job:
    protocol: dict
    indication: str = "PSP"
    axes: tuple[str, ...] = ("3",)  # this slice covers Axis 3 only


def run_job(job: Job, greenlight: bool = True):
    # Imported here so the seam stays import-light and dependency-injectable.
    from .adjudication import SinglePassVerifier
    from .builder import Builder
    from .loop import run_premortem

    builder, verifier = Builder(), SinglePassVerifier()
    result = run_premortem(job, builder, verifier)

    # Greenlight only when the kill loop produced a kill-list to remediate.
    if greenlight and result.status.startswith("STATUS: PASS") and result.kill_list:
        from .greenlight import run_greenlight

        result.greenlight = run_greenlight(job, result.kill_list, builder, verifier)

    return result
