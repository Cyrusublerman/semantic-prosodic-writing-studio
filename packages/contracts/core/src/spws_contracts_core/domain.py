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
    RESTRICTED_PENDING_REVIEW = "restricted_pending_review"
    PRIVATE = "private"
    UNKNOWN = "unknown"


class PrivacyState(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    PRIVATE = "private"
    UNKNOWN = "unknown"


class DialectCode(StrEnum):
    EN_AU = "en-AU"
    EN_GB = "en-GB"
    EN_US = "en-US"
    UNKNOWN = "unknown"


class PronunciationStatus(StrEnum):
    SOURCED = "sourced"
    INFERRED = "inferred"
    DISPUTED = "disputed"
    UNKNOWN = "unknown"


def normalize_rights_ingest(value: RightsState | str | None) -> RightsState:
    """Map ingest aliases: bare ``restricted`` → ``restricted_pending_review``."""
    if value is None:
        return RightsState.RESTRICTED_PENDING_REVIEW
    if isinstance(value, RightsState):
        state = value
    else:
        raw = str(value).strip().lower().replace("-", "_")
        if raw in {"restricted", "restricted_pending_review"}:
            return RightsState.RESTRICTED_PENDING_REVIEW
        try:
            state = RightsState(raw)
        except ValueError:
            return RightsState.UNKNOWN
    if state is RightsState.RESTRICTED:
        return RightsState.RESTRICTED_PENDING_REVIEW
    return state


def rights_allows_retrieval(rights: RightsState) -> bool:
    """Fail closed: unknown and pending-review material never enter retrieval."""
    return rights in {RightsState.PUBLIC, RightsState.INTERNAL}


class DialectPolicy(ContractModel):
    """Active dialect policy for a work (D003 / D016). Default Australian English."""

    primary: DialectCode = DialectCode.EN_AU
    allowed_variants: list[DialectCode] = Field(
        default_factory=lambda: [DialectCode.EN_AU, DialectCode.EN_GB, DialectCode.EN_US]
    )
    spelling_convention: DialectCode = DialectCode.EN_AU
    schema_version: str = "0.1.0"


class PronunciationVariant(ContractModel):
    dialect: DialectCode = DialectCode.UNKNOWN
    ipa: str | None = None
    status: PronunciationStatus = PronunciationStatus.UNKNOWN
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    schema_version: str = "0.1.0"


class LexicalRecord(ContractModel):
    """Sense-aware lexical data mapped from adapters (D012 / D015)."""

    record_id: str
    lemma: str
    sense_id: str | None = None
    definition: str | None = None
    rarity: float | None = Field(default=None, ge=0.0, le=1.0)
    frequency: float | None = None
    register_labels: list[str] = Field(default_factory=list)
    morphology: dict[str, Any] = Field(default_factory=dict)
    pronunciation_variants: list[PronunciationVariant] = Field(default_factory=list)
    stress_pattern: str | None = None
    syllable_count: int | None = Field(default=None, ge=0)
    rhyme_keys: list[str] = Field(default_factory=list)
    semantic_relations: dict[str, list[str]] = Field(default_factory=dict)
    field_confidence: dict[str, float] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = "0.1.0"


class ExchangeEnvelope(ContractModel):
    """Lightweight universal envelope for exchanged domain objects (integration_contracts)."""

    object_id: str
    object_type: str
    schema_version: str = "0.1.0"
    created_at: UtcDateTime | None = None
    created_by: str | None = None
    source_objects: list[str] = Field(default_factory=list)
    project_id: str | None = None
    language: str = "en"
    dialect: DialectCode = DialectCode.EN_AU
    permissions: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    review_state: str = "unreviewed"
    payload: dict[str, Any] = Field(default_factory=dict)


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


class MeaningScale(StrEnum):
    WORD = "word"
    SENSE = "sense"
    PHRASE = "phrase"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    FRAGMENT_CHUNK = "fragment_chunk"


class AuthorshipClass(StrEnum):
    QUOTE = "quote"
    USER = "user"
    OBSERVATION = "observation"
    EXTRACTED = "extracted"
    MACHINE_DERIVATIVE = "machine_derivative"


class StructuralScope(StrEnum):
    WORK = "work"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    STANZA = "stanza"
    SENTENCE = "sentence"
    LINE = "line"
    PHRASE = "phrase"
    WORD = "word"
    PHONEME = "phoneme"


class CandidateStatus(StrEnum):
    PROPOSED = "proposed"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    COMBINED = "combined"
    FAILED = "failed"


class MeaningUnit(ContractModel):
    unit_id: str
    scale: MeaningScale
    text: str
    span: TextSpan | None = None
    source_object_id: str | None = None
    parent_unit_id: str | None = None
    content_digest: DigestRecord | None = None
    rights: RightsState = RightsState.UNKNOWN
    privacy: PrivacyState = PrivacyState.UNKNOWN
    object_uid: str | None = None
    commit_sha: str | None = None
    schema_version: str = "0.1.0"


class MeaningProfile(ContractModel):
    unit_id: str
    embedding: list[float] | None = None
    model_id: str | None = None
    model_version: str | None = None
    domain_tags: list[str] = Field(default_factory=list)
    register_tags: list[str] = Field(default_factory=list)
    affect_tags: list[str] = Field(default_factory=list)
    imagery_tags: list[str] = Field(default_factory=list)
    theme_tags: list[str] = Field(default_factory=list)
    concept_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    analyser: str = "spws_semantics"
    analyser_version: str = "0.1.0"
    schema_version: str = "0.1.0"


class SimilarityQuery(ContractModel):
    query_id: str | None = None
    text: str | None = None
    unit_id: str | None = None
    target_scales: list[MeaningScale] = Field(default_factory=list)
    fragment_types: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    rights_allowed: list[RightsState] = Field(default_factory=list)
    privacy_allowed: list[PrivacyState] = Field(default_factory=list)
    commit: str | None = None
    result_limit: int = Field(default=10, ge=1, le=100)
    weight_vector: float = 0.7
    weight_tags: float = 0.2
    weight_graph: float = 0.1
    schema_version: str = "0.1.0"

    @model_validator(mode="after")
    def require_text_or_unit(self) -> "SimilarityQuery":
        if self.text is None and self.unit_id is None:
            raise ValueError("SimilarityQuery requires text or unit_id")
        return self


class SimilarityHit(ContractModel):
    unit_id: str
    text: str
    scale: MeaningScale
    score_combined: float
    score_vector: float = 0.0
    score_tags: float = 0.0
    score_graph: float = 0.0
    explanation: str | None = None
    object_uid: str | None = None
    span: TextSpan | None = None
    theme_tags: list[str] = Field(default_factory=list)
    path: str | None = None
    schema_version: str = "0.1.0"


class SimilarityResultSet(ContractModel):
    query: SimilarityQuery
    hits: list[SimilarityHit] = Field(default_factory=list)
    model_id: str | None = None
    model_version: str | None = None
    warnings: list[str] = Field(default_factory=list)
    schema_version: str = "0.1.0"


class StructuralUnit(ContractModel):
    unit_id: str
    scope: StructuralScope
    text: str | None = None
    span: TextSpan | None = None
    parent_id: str | None = None
    child_ids: list[str] = Field(default_factory=list)
    source_object_id: str | None = None
    ordinal: int | None = None
    schema_version: str = "0.1.0"


class Annotation(ContractModel):
    annotation_id: str
    source_object: str
    scope: StructuralScope | None = None
    location: TextSpan | None = None
    feature: str
    value: Any = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    alternatives: list[Any] = Field(default_factory=list)
    analyser: str
    analyser_version: str = "0.1.0"
    schema_version: str = "0.1.0"


class AnalysisBundle(ContractModel):
    bundle_id: str
    source_object_id: str
    annotations: list[Annotation] = Field(default_factory=list)
    structural_units: list[StructuralUnit] = Field(default_factory=list)
    created_at: UtcDateTime
    component_versions: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    schema_version: str = "0.1.0"


class SourceFragment(ContractModel):
    fragment_id: str
    source_object_id: str
    text: str
    span: TextSpan | None = None
    authorship: AuthorshipClass
    fragment_type: str | None = None
    rights: RightsState = RightsState.UNKNOWN
    privacy: PrivacyState = PrivacyState.UNKNOWN
    derived_from: str | None = None
    schema_version: str = "0.1.0"


class NormalisedSource(ContractModel):
    normalised_id: str
    source_object_id: str
    text: str
    transform_trace: list[str] = Field(default_factory=list)
    uncertain_regions: list[TextSpan] = Field(default_factory=list)
    encoding: str = "utf-8"
    schema_version: str = "0.1.0"


class WorkSpecification(ContractModel):
    spec_id: str
    mode: str = "poetry_revision"
    purpose: str | None = None
    audience: str | None = None
    subject: str | None = None
    form: str | None = None
    voice: str | None = None
    linguistic_register: str | None = None
    length: str | None = None
    dialect_policy: DialectPolicy = Field(default_factory=DialectPolicy)
    semantic_arc: list[str] = Field(default_factory=list)
    emotional_arc: list[str] = Field(default_factory=list)
    motif_plan: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    source_policy: dict[str, Any] = Field(default_factory=dict)
    machine_assistance_policy: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = "0.1.0"


class StudioConstraint(ContractModel):
    constraint_id: str
    target_scope: str
    constraint_type: str
    hard: bool = False
    measurement_method: str | None = None
    tolerance: float | None = None
    weight: float = 1.0
    evidence: list[str] = Field(default_factory=list)
    schema_version: str = "0.1.0"


class WorkPlan(ContractModel):
    plan_id: str
    work_spec_id: str
    structural_units: list[StructuralUnit] = Field(default_factory=list)
    constraints: list[StudioConstraint] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    unresolved_decisions: list[str] = Field(default_factory=list)
    schema_version: str = "0.1.0"


class GenerationSpecification(ContractModel):
    gen_spec_id: str
    method_family: str
    work_plan_id: str | None = None
    source_permissions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    candidate_count: int = 3
    deterministic_seed: int | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    # Reserved for future LLM producers (D005); unused by deterministic path.
    provider: str | None = None
    model: str | None = None
    model_revision: str | None = None
    prompt_template_id: str | None = None
    cost_estimate: float | None = None
    retention_policy: str | None = None
    schema_version: str = "0.1.0"


class Candidate(ContractModel):
    candidate_id: str
    content: str
    method_family: str
    generation_spec_id: str | None = None
    source_material: list[str] = Field(default_factory=list)
    constraint_trace: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    status: CandidateStatus = CandidateStatus.PROPOSED
    provenance_note: str | None = None
    target_span: TextSpan | None = None
    line_index: int | None = None
    schema_version: str = "0.1.0"


class CandidateSet(ContractModel):
    set_id: str
    target_scope: str | None = None
    candidates: list[Candidate] = Field(default_factory=list)
    generation_spec_id: str | None = None
    schema_version: str = "0.1.0"


class EvaluationResult(ContractModel):
    evaluation_id: str
    subject_id: str
    criterion: str
    measured_value: float | None = None
    inferred_label: str | None = None
    human_judgement: str | None = None
    evidence: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    schema_version: str = "0.1.0"


class EvaluationBundle(ContractModel):
    bundle_id: str
    subject_id: str
    results: list[EvaluationResult] = Field(default_factory=list)
    created_at: UtcDateTime
    schema_version: str = "0.1.0"


class RevisionOperation(ContractModel):
    operation_id: str
    original_text: str
    revised_text: str
    operation: str
    reason: str | None = None
    affected_constraints: list[str] = Field(default_factory=list)
    predicted_improvements: list[str] = Field(default_factory=list)
    predicted_degradations: list[str] = Field(default_factory=list)
    candidate_id: str | None = None
    line_index: int | None = None
    target_span: TextSpan | None = None
    schema_version: str = "0.1.0"


class ManuscriptVersion(ContractModel):
    manuscript_id: str
    version_id: str
    text: str
    parent_version_ids: list[str] = Field(default_factory=list)
    accepted_change_ids: list[str] = Field(default_factory=list)
    unresolved_alternatives: list[str] = Field(default_factory=list)
    work_plan_id: str | None = None
    created_at: UtcDateTime
    provenance_map: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = "0.1.0"


class Classification(ContractModel):
    """Minimal labelled classification of a subject (theme, form, register, etc.)."""

    classification_id: str
    label: str
    category: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    subject_id: str | None = None
    schema_version: str = "0.1.0"


class ClassificationBundle(ContractModel):
    """Set of classifications for one subject."""

    bundle_id: str
    subject_id: str
    classifications: list[Classification] = Field(default_factory=list)
    created_at: UtcDateTime
    schema_version: str = "0.1.0"


class PublicationBundle(ContractModel):
    """Export-facing publication package linking manuscript, decision, and files."""

    bundle_id: str
    manuscript_id: str
    version_id: str
    title: str | None = None
    clean_text: str | None = None
    export_files: dict[str, str] = Field(default_factory=dict)
    classification_bundle_id: str | None = None
    decision_id: str | None = None
    run_id: str | None = None
    created_at: UtcDateTime
    schema_version: str = "0.1.0"
