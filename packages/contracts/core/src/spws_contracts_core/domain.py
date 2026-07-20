"""SPWS domain contracts: InputPackage, RawSource, PKL query/result, promotion."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from .base import ContractModel
from .digests import DigestRecord
from .quality import WarningRecord
from .time import UtcDateTime


class ReadMode(StrEnum):
    SNAPSHOT = "snapshot"
    WORKING_TREE = "working_tree"
    REMOTE = "remote"


class WriteMode(StrEnum):
    PROMOTION_ONLY = "promotion_only"
    DISABLED = "disabled"


class RightsState(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    PRIVATE = "private"
    UNKNOWN = "unknown"


class PrivacyState(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    PRIVATE = "private"
    UNKNOWN = "unknown"


class RetrievalMethod(StrEnum):
    LEXICAL = "lexical"
    METADATA = "metadata"
    RELATIONSHIP = "relationship"
    SEMANTIC = "semantic"
    COMBINED = "combined"
    DIRECT = "direct"


class PromotionOperation(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    LINK = "link"
    SUPERSEDE = "supersede"
    ARCHIVE_PROPOSAL = "archive_proposal"


class TextSpan(ContractModel):
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)
    start_byte: int | None = Field(default=None, ge=0)
    end_byte: int | None = Field(default=None, ge=0)
    quote: str | None = None

    @model_validator(mode="after")
    def validate_span(self) -> "TextSpan":
        if self.end_char < self.start_char:
            raise ValueError("end_char must be >= start_char")
        if self.start_byte is not None and self.end_byte is not None and self.end_byte < self.start_byte:
            raise ValueError("end_byte must be >= start_byte")
        return self


class ProvenanceStamp(ContractModel):
    repository_identity: str
    commit_sha: str | None = None
    working_tree: bool = False
    object_uid: str | None = None
    relative_path: str | None = None
    content_digest: DigestRecord | None = None
    extracted_at: UtcDateTime
    rights: RightsState = RightsState.UNKNOWN
    privacy: PrivacyState = PrivacyState.UNKNOWN
    reproducible: bool = True
    warnings: list[WarningRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_reproducibility(self) -> "ProvenanceStamp":
        if self.working_tree:
            object.__setattr__(self, "reproducible", False)
            if self.commit_sha is None:
                object.__setattr__(self, "commit_sha", "WORKING_TREE")
        elif not self.commit_sha:
            raise ValueError("snapshot provenance requires commit_sha")
        return self


class InputPackage(ContractModel):
    """Material entering the system without interpretation."""

    package_id: str
    schema_version: str = "0.1.0"
    media_type: str = "text/plain"
    encoding: str = "utf-8"
    text: str | None = None
    bytes_location: str | None = None
    source_label: str | None = None
    creator: str | None = None
    capture_route: str = "direct_text"
    captured_at: UtcDateTime
    rights: RightsState = RightsState.UNKNOWN
    privacy: PrivacyState = PrivacyState.UNKNOWN
    retention_policy: str | None = None
    requested_operations: list[str] = Field(default_factory=list)
    user_metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[WarningRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_payload(self) -> "InputPackage":
        if self.text is None and self.bytes_location is None:
            raise ValueError("InputPackage requires text or bytes_location")
        return self


class RawSource(ContractModel):
    """Immutable retained source object."""

    source_id: str
    schema_version: str = "0.1.0"
    input_package_id: str
    media_type: str
    encoding: str = "utf-8"
    text: str | None = None
    content_digest: DigestRecord
    stored_at: UtcDateTime
    storage_location: str
    rights: RightsState
    privacy: PrivacyState
    provenance: ProvenanceStamp | None = None
    immutable: bool = True

    @field_validator("immutable")
    @classmethod
    def must_be_immutable(cls, value: bool) -> bool:
        if not value:
            raise ValueError("RawSource must remain immutable")
        return value


class PKLRelationship(ContractModel):
    type: str
    target: str
    note: str | None = None
    confidence: str | float | None = None
    evidence: list[str] = Field(default_factory=list)


class PKLQuery(ContractModel):
    text: str | None = None
    object_types: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    rights_filter: list[RightsState] = Field(
        default_factory=lambda: [RightsState.PUBLIC, RightsState.INTERNAL]
    )
    privacy_filter: list[PrivacyState] = Field(
        default_factory=lambda: [PrivacyState.PUBLIC, PrivacyState.INTERNAL]
    )
    commit: str | None = None
    result_limit: int = Field(default=20, ge=1, le=500)
    include_working_tree: bool = False


class PKLResult(ContractModel):
    object_uid: str
    title: str
    relevant_span: TextSpan | None = None
    path: str
    commit: str
    digest: DigestRecord
    relationships: list[PKLRelationship] = Field(default_factory=list)
    rights: RightsState
    privacy: PrivacyState
    confidence: float = Field(ge=0.0, le=1.0)
    retrieval_method: RetrievalMethod
    summary: str | None = None
    object_type: str | None = None
    reproducible: bool = True
    extracted_at: UtcDateTime | None = None
    warnings: list[WarningRecord] = Field(default_factory=list)


class ConflictInfo(ContractModel):
    base_digest: str | None = None
    current_digest: str | None = None
    proposed_digest: str | None = None
    conflict_kind: str | None = None
    details: str | None = None


class PKLPromotionBundle(ContractModel):
    """Proposed knowledge change for human review; never auto-applied."""

    bundle_id: str
    schema_version: str = "0.1.0"
    content_version: str = "0.1.0"
    operation: PromotionOperation
    target_uid: str | None = None
    proposed_new_uid: str | None = None
    proposed_content: dict[str, Any] | str
    source_evidence: list[dict[str, Any]] = Field(default_factory=list)
    originating_run_id: str
    provenance: ProvenanceStamp
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[WarningRecord] = Field(default_factory=list)
    rights_assessment: RightsState = RightsState.UNKNOWN
    privacy_assessment: PrivacyState = PrivacyState.UNKNOWN
    conflict: ConflictInfo | None = None
    created_at: UtcDateTime
    review_status: str = "unreviewed"

    @model_validator(mode="after")
    def validate_target(self) -> "PKLPromotionBundle":
        if self.operation is PromotionOperation.CREATE and not self.proposed_new_uid:
            raise ValueError("CREATE requires proposed_new_uid")
        if self.operation is not PromotionOperation.CREATE and not self.target_uid:
            raise ValueError(f"{self.operation} requires target_uid")
        return self


class RevisionDecisionKind(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    COMBINE = "combine"
    DEFER = "defer"
    MANUAL_REPLACE = "manual_replace"


class RevisionDecision(ContractModel):
    decision_id: str
    run_id: str
    candidate_ids: list[str] = Field(default_factory=list)
    kind: RevisionDecisionKind
    decided_at: UtcDateTime
    decided_by: str = "human"
    rationale: str | None = None
    resulting_text: str | None = None


class RunManifest(ContractModel):
    run_id: str
    pipeline_id: str
    started_at: UtcDateTime
    finished_at: UtcDateTime | None = None
    commit_sha: str | None = None
    read_mode: ReadMode
    component_versions: dict[str, str] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    input_refs: list[str] = Field(default_factory=list)
    output_refs: list[str] = Field(default_factory=list)
    warnings: list[WarningRecord] = Field(default_factory=list)
    status: str = "running"
