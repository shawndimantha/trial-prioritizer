"""Data shapes. Each Finding carries one field per gate so the verifier can
grade it mechanically against rubric.md (G1 grounding, G2 entailment,
G3 quantification, G4 remediation)."""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """G1 — a specific, retrievable public source."""

    source_id: str = Field(description="NCT ID, FDA guidance name, or publication identifier")
    title: str = Field(description="Title of the source as retrieved")
    url: str = Field(default="", description="Retrievable URL if available")


class Finding(BaseModel):
    id: str = Field(description="Stable id, e.g. 'A3-1'. Keep identical across revisions.")
    axis: Literal["1", "2", "3"]
    title: str = Field(description="One-line statement of the flaw")
    verdict: str = Field(description="The claim: what is wrong and why (graded by G2)")
    quantitative_threshold: str = Field(
        description="A concrete numeric threshold or comparison (graded by G3), "
        "e.g. 'powered for 30% PSPRS slowing; PASSPORT saw 0% despite engagement'"
    )
    citation: Citation
    remediation: str = Field(
        description="A specific, actionable fix tied to the flaw — or a reasoned "
        "'do not run' with stated conditions (graded by G4)"
    )
    lethality: int = Field(ge=1, le=5, description="5 = fatal/most-lethal; ranks the kill-list")


class FindingSet(BaseModel):
    findings: List[Finding]


class GateResult(BaseModel):
    passed: bool
    reason: str


class Verdict(BaseModel):
    finding_id: str
    g1: GateResult
    g2: GateResult
    g3: GateResult
    g4: GateResult

    @property
    def passed(self) -> bool:
        return all(g.passed for g in (self.g1, self.g2, self.g3, self.g4))

    def failed_gate_reasons(self) -> list[str]:
        out = []
        for name, gr in (("G1", self.g1), ("G2", self.g2), ("G3", self.g3), ("G4", self.g4)):
            if not gr.passed:
                out.append(f"{name}: {gr.reason}")
        return out
