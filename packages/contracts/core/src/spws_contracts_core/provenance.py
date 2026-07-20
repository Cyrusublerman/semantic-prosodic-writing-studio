from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from .base import ContractModel
from .identifiers import (
    ActivityId,
    ContributionId,
    RelationId,
    RunId,
    StepRunId,
)
from .quality import ProcessingState, ReviewState
from .references import AgentReference, AgentType, ObjectReference, VersionReference
from .registry import validate_registered
from .time import UtcDateTime


class ActivityReference(ContractModel):
    activity_id: ActivityId
    activity_type: str
    status: ProcessingState
    started_at: UtcDateTime
    ended_at: UtcDateTime | None = None
    responsible_agents: tuple[AgentReference, ...]
    run_id: RunId | None = None
    step_run_id: StepRunId | None = None
    component_version: str | None = Field(default=None, max_length=255)
    parameters_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("activity_type")
    @classmethod
    def activity_type_registered(cls, value: str) -> str:
        return validate_registered(value, "provenance.activity_types")

    @model_validator(mode="after")
    def validate_activity(self) -> "ActivityReference":
        if not self.responsible_agents:
            raise ValueError("activity requires at least one responsible agent")
        completed = {
            ProcessingState.SUCCEEDED,
            ProcessingState.PARTIALLY_SUCCEEDED,
            ProcessingState.FAILED,
            ProcessingState.CANCELLED,
            ProcessingState.TIMED_OUT,
            ProcessingState.SKIPPED,
        }
        if self.status in completed and self.ended_at is None:
            raise ValueError("completed activity requires ended_at")
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError("activity ended_at must not precede started_at")
        if self.step_run_id is not None and self.run_id is None:
            raise ValueError("step_run_id requires run_id")
        return self


class ProvenanceRelation(ContractModel):
    relation_id: RelationId
    relation_type: str
    subject: VersionReference
    object: VersionReference | ObjectReference
    activity_id: ActivityId | None = None
    entity_role: str | None = None
    method: str | None = Field(default=None, max_length=512)
    parameters_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source_span_ids: tuple[str, ...] = ()
    target_span_ids: tuple[str, ...] = ()
    review_state: ReviewState = ReviewState.UNREVIEWED

    @field_validator("relation_type")
    @classmethod
    def relation_type_registered(cls, value: str) -> str:
        return validate_registered(value, "provenance.relation_types")

    @field_validator("entity_role")
    @classmethod
    def entity_role_registered(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_registered(value, "provenance.entity_roles")

    @model_validator(mode="after")
    def reject_self_relation(self) -> "ProvenanceRelation":
        object_version = getattr(self.object, "version_id", None)
        if object_version is not None and object_version == self.subject.version_id:
            raise ValueError("provenance relation cannot point a version to itself")
        return self


class ContributionRecord(ContractModel):
    contribution_id: ContributionId
    role: str
    agent: AgentReference
    activity_id: ActivityId | None = None
    target: VersionReference
    sources: tuple[VersionReference, ...] = ()
    description: str | None = Field(default=None, max_length=2048)
    review_state: ReviewState = ReviewState.UNREVIEWED

    @field_validator("role")
    @classmethod
    def role_registered(cls, value: str) -> str:
        return validate_registered(value, "provenance.contribution_roles")


class DirectProvenanceSummary(ContractModel):
    creator: AgentReference
    creation_activity: ActivityReference
    direct_relations: tuple[ProvenanceRelation, ...] = ()
    contribution_records: tuple[ContributionRecord, ...] = ()
    full_provenance_records: tuple[ObjectReference, ...] = ()

    @model_validator(mode="after")
    def creator_must_be_responsible(self) -> "DirectProvenanceSummary":
        responsible = {agent.agent_id for agent in self.creation_activity.responsible_agents}
        if self.creator.agent_id not in responsible:
            raise ValueError("creator must be among creation activity responsible agents")
        return self
