from __future__ import annotations

from pydantic import Field

from spws_contracts_core.base import ContractModel


class EvidenceRef(ContractModel):
    object_uid: str
    title: str | None = None
    span_quote: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class LineAnnotation(ContractModel):
    line_index: int = Field(ge=0)
    line_text: str
    syllable_count: int = Field(ge=0)
    stress_pattern: str | None = None
    meter_name: str | None = None
    foot_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)


class PoetryAnalysisResult(ContractModel):
    text: str
    lines: list[LineAnnotation]
    engine: str
    pkl_evidence_count: int = 0
