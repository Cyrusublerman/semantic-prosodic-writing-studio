from __future__ import annotations

from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import Field, field_validator, model_validator

from .base import ContractModel
from .identifiers import FailureId, ReviewId, WarningId
from .references import AgentReference, ObjectReference, VersionReference
from .registry import failure_definition, validate_registered, warning_definition
from .time import UtcDateTime


class PresenceState(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
    NOT_REQUESTED = "not_requested"
    UNAVAILABLE = "unavailable"
    WITHHELD = "withheld"
    FAILED = "failed"
    AMBIGUOUS = "ambiguous"


class EvidenceMethod(StrEnum):
    MEASURED = "measured"
    PARSED = "parsed"
    RETRIEVED = "retrieved"
    COMPUTED = "computed"
    DERIVED = "derived"
    RULE_INFERRED = "rule_inferred"
    STATISTICAL_INFERRED = "statistical_inferred"
    MODEL_INFERRED = "model_inferred"
    HUMAN_ASSERTED = "human_asserted"
    HUMAN_REVIEWED = "human_reviewed"
    IMPORTED = "imported"
    DEFAULTED = "defaulted"


class ReviewState(StrEnum):
    UNREVIEWED = "unreviewed"
    MACHINE_CHECKED = "machine_checked"
    HUMAN_REVIEWED = "human_reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"


class ProcessingState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_HUMAN = "awaiting_human"
    SUCCEEDED = "succeeded"
    PARTIALLY_SUCCEEDED = "partially_succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class ConfidenceKind(StrEnum):
    PROBABILITY = "probability"
    CALIBRATED_PROBABILITY = "calibrated_probability"
    AGREEMENT = "agreement"
    COVERAGE = "coverage"
    HEURISTIC_STRENGTH = "heuristic_strength"
    ORDINAL = "ordinal"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class ConfidenceRecord(ContractModel):
    kind: ConfidenceKind
    value: float | int | str
    method: str = Field(min_length=1, max_length=512)
    calibration_set: VersionReference | None = None
    sample_size: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def validate_value(self) -> "ConfidenceRecord":
        if self.kind in {
            ConfidenceKind.PROBABILITY,
            ConfidenceKind.CALIBRATED_PROBABILITY,
            ConfidenceKind.AGREEMENT,
            ConfidenceKind.COVERAGE,
            ConfidenceKind.HEURISTIC_STRENGTH,
        }:
            if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
                raise ValueError(f"{self.kind.value} confidence requires a numeric value")
            if not 0 <= float(self.value) <= 1:
                raise ValueError("numeric confidence must be between 0 and 1")
        if self.kind is ConfidenceKind.CALIBRATED_PROBABILITY and self.calibration_set is None:
            raise ValueError("calibrated_probability requires calibration_set")
        if self.kind is ConfidenceKind.ORDINAL and not isinstance(self.value, str):
            raise ValueError("ordinal confidence requires a string value")
        return self


class AlternativeRecord(ContractModel):
    value: object
    confidence: ConfidenceRecord | None = None
    rationale: str | None = Field(default=None, max_length=2048)


class ReviewRecord(ContractModel):
    review_id: ReviewId
    state: ReviewState
    reviewer: AgentReference
    reviewed_at: UtcDateTime
    rationale: str | None = Field(default=None, max_length=4096)
    evidence: tuple[ObjectReference, ...] = ()


class WarningRecord(ContractModel):
    warning_id: WarningId
    code: str
    name: str
    severity: Severity
    scope: str = Field(min_length=1, max_length=512)
    message: str | None = Field(default=None, max_length=4096)
    retryable: bool = False
    remediation: str | None = Field(default=None, max_length=4096)
    related_objects: tuple[ObjectReference, ...] = ()

    @model_validator(mode="after")
    def validate_registry_entry(self) -> "WarningRecord":
        definition = warning_definition(self.code)
        if self.name != definition["name"]:
            raise ValueError("warning name does not match registered code")
        if self.severity.value != definition["severity"]:
            raise ValueError("warning severity does not match registered code")
        return self


class FailureRecord(ContractModel):
    failure_id: FailureId
    code: str
    name: str
    severity: Severity = Severity.ERROR
    scope: str = Field(min_length=1, max_length=512)
    message: str | None = Field(default=None, max_length=4096)
    retryable: bool = False
    remediation: str | None = Field(default=None, max_length=4096)
    related_objects: tuple[ObjectReference, ...] = ()

    @model_validator(mode="after")
    def validate_registry_entry(self) -> "FailureRecord":
        definition = failure_definition(self.code)
        if self.name != definition["name"]:
            raise ValueError("failure name does not match registered code")
        if self.severity not in {Severity.ERROR, Severity.FATAL}:
            raise ValueError("failure severity must be error or fatal")
        return self


T = TypeVar("T")


class QualifiedValue(ContractModel, Generic[T]):
    presence: PresenceState
    value: T | None = None
    evidence_method: EvidenceMethod | None = None
    review_state: ReviewState = ReviewState.UNREVIEWED
    confidence: ConfidenceRecord | None = None
    alternatives: tuple[AlternativeRecord, ...] = ()
    warnings: tuple[WarningRecord, ...] = ()
    failures: tuple[FailureRecord, ...] = ()

    @model_validator(mode="after")
    def validate_presence_contract(self) -> "QualifiedValue[T]":
        if self.presence is PresenceState.PRESENT and self.value is None:
            raise ValueError("present qualified value requires value")
        if self.presence is not PresenceState.PRESENT and self.value is not None:
            raise ValueError("non-present qualified value must not carry value")
        if self.presence is PresenceState.AMBIGUOUS and not self.alternatives:
            raise ValueError("ambiguous qualified value requires alternatives")
        if self.presence is PresenceState.FAILED and not self.failures:
            raise ValueError("failed qualified value requires a failure record")
        return self
