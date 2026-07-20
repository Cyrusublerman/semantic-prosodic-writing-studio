from __future__ import annotations

from pydantic import Field, JsonValue, field_validator, model_validator

from .base import ContractModel
from .identifiers import AssertionId, DecisionId, RuleId
from .provenance import AgentReference
from .quality import ReviewState
from .references import ObjectReference
from .registry import validate_registered
from .time import TimeWindow, UtcDateTime
from .policy_types import (
    AuthorityTier, ConstraintOperator, DeletionMode, PolicyDecisionOutcome,
    PolicyEffect, PrivacyClass, RetentionClass, TransmissionClass,
)


class EvidenceRecord(ContractModel):
    source: ObjectReference
    description: str | None = Field(default=None, max_length=2048)
    verified: bool = False
    verified_at: UtcDateTime | None = None
    verifier: AgentReference | None = None

    @model_validator(mode="after")
    def verified_evidence_has_metadata(self) -> "EvidenceRecord":
        if self.verified and (self.verified_at is None or self.verifier is None):
            raise ValueError("verified evidence requires verified_at and verifier")
        return self


class RightsAssertion(ContractModel):
    assertion_id: AssertionId
    assertion_type: str
    issuer: AgentReference
    target: ObjectReference
    effect: PolicyEffect | None = None
    evidence: tuple[EvidenceRecord, ...] = ()
    jurisdiction: str | None = Field(default=None, max_length=255)
    effective_window: TimeWindow = TimeWindow()
    review_state: ReviewState = ReviewState.UNREVIEWED
    notes: str | None = Field(default=None, max_length=4096)

    @field_validator("assertion_type")
    @classmethod
    def assertion_type_registered(cls, value: str) -> str:
        return validate_registered(value, "rights.assertion_types")

    @model_validator(mode="after")
    def restriction_requires_effect(self) -> "RightsAssertion":
        if self.assertion_type in {
            "spws.rights.permission",
            "spws.rights.restriction",
            "spws.rights.withdrawal",
        } and self.effect is None:
            raise ValueError("permission/restriction/withdrawal assertion requires effect")
        return self


class PolicyConstraint(ContractModel):
    constraint_type: str
    operator: ConstraintOperator = ConstraintOperator.EQUALS
    value: JsonValue

    @field_validator("constraint_type")
    @classmethod
    def constraint_type_registered(cls, value: str) -> str:
        return validate_registered(value, "rights.constraint_types")


class DutyRecord(ContractModel):
    duty_type: str
    satisfied: bool = False
    evidence: tuple[EvidenceRecord, ...] = ()
    notes: str | None = Field(default=None, max_length=2048)

    @field_validator("duty_type")
    @classmethod
    def duty_type_registered(cls, value: str) -> str:
        return validate_registered(value, "rights.duties")

    @model_validator(mode="after")
    def satisfied_requires_evidence(self) -> "DutyRecord":
        if self.satisfied and not self.evidence:
            raise ValueError("satisfied duty requires evidence")
        return self


class UsageRule(ContractModel):
    rule_id: RuleId
    operation: str
    effect: PolicyEffect
    authority_tier: AuthorityTier
    target: ObjectReference | None = None
    agent: AgentReference | None = None
    purpose: str | None = Field(default=None, max_length=512)
    effective_window: TimeWindow = TimeWindow()
    constraints: tuple[PolicyConstraint, ...] = ()
    duties: tuple[DutyRecord, ...] = ()
    evidence: tuple[EvidenceRecord, ...] = ()
    source_assertions: tuple[AssertionId, ...] = ()
    override_lower_authority: bool = False
    explanation: str | None = Field(default=None, max_length=4096)

    @field_validator("operation")
    @classmethod
    def operation_registered(cls, value: str) -> str:
        return validate_registered(value, "rights.operations")

    @model_validator(mode="after")
    def prohibit_has_no_duties(self) -> "UsageRule":
        if self.effect is PolicyEffect.PROHIBIT and self.duties:
            raise ValueError("prohibition rule cannot carry permit duties")
        return self


class PolicyContext(ContractModel):
    operation: str
    target: ObjectReference | None = None
    agent: AgentReference | None = None
    purpose: str | None = None
    evaluated_at: UtcDateTime
    attributes: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("operation")
    @classmethod
    def operation_registered(cls, value: str) -> str:
        return validate_registered(value, "rights.operations")


class PolicyDecision(ContractModel):
    decision_id: DecisionId
    operation: str
    outcome: PolicyDecisionOutcome
    allowed: bool
    highest_authority_tier: AuthorityTier | None = None
    applied_rule_ids: tuple[RuleId, ...] = ()
    rejected_rule_ids: tuple[RuleId, ...] = ()
    unsatisfied_duties: tuple[str, ...] = ()
    explanation: str
    evaluated_at: UtcDateTime

    @field_validator("operation")
    @classmethod
    def operation_registered(cls, value: str) -> str:
        return validate_registered(value, "rights.operations")

    @model_validator(mode="after")
    def outcome_matches_allowed(self) -> "PolicyDecision":
        if self.allowed != (self.outcome is PolicyDecisionOutcome.PERMIT):
            raise ValueError("allowed flag must match permit outcome")
        return self


class PrivacyPolicy(ContractModel):
    privacy_class: PrivacyClass
    transmission_class: TransmissionClass
    consent_required: bool = False
    allowed_recipients: tuple[str, ...] = ()
    notes: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def validate_transmission(self) -> "PrivacyPolicy":
        if self.transmission_class is TransmissionClass.EXTERNAL_WITH_CONSENT and not self.consent_required:
            raise ValueError("external_with_consent requires consent_required")
        if self.transmission_class in {TransmissionClass.LOCAL_ONLY, TransmissionClass.BLOCKED} and self.allowed_recipients:
            raise ValueError("local_only/blocked policy cannot list external recipients")
        return self


class RetentionPolicy(ContractModel):
    retention_class: RetentionClass
    deletion_mode: DeletionMode
    delete_after: UtcDateTime | None = None
    legal_hold: bool = False
    hold_reference: ObjectReference | None = None
    notes: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def validate_retention(self) -> "RetentionPolicy":
        if self.retention_class is RetentionClass.UNTIL_DATE and self.delete_after is None:
            raise ValueError("until_date retention requires delete_after")
        if self.legal_hold or self.retention_class is RetentionClass.LEGAL_HOLD:
            if self.hold_reference is None:
                raise ValueError("legal hold requires hold_reference")
            if self.deletion_mode is not DeletionMode.BLOCKED_BY_HOLD:
                raise ValueError("legal hold requires blocked_by_hold deletion mode")
        elif self.deletion_mode is DeletionMode.BLOCKED_BY_HOLD:
            raise ValueError("blocked_by_hold requires legal hold")
        return self


class DirectPolicySummary(ContractModel):
    privacy: PrivacyPolicy
    retention: RetentionPolicy
    decisions: tuple[PolicyDecision, ...] = ()
    policy_bundle_refs: tuple[ObjectReference, ...] = ()

    @model_validator(mode="after")
    def validate_transmission_decisions(self) -> "DirectPolicySummary":
        blocked_ops = {
            "spws.operation.external_context",
            "spws.operation.external_transmission",
            "spws.operation.private_share",
            "spws.operation.public_share",
            "spws.operation.publish",
            "spws.operation.redistribute",
        }
        if self.privacy.transmission_class in {TransmissionClass.LOCAL_ONLY, TransmissionClass.BLOCKED}:
            for decision in self.decisions:
                if decision.operation in blocked_ops and decision.allowed:
                    raise ValueError("policy summary permits transmission forbidden by privacy policy")
        if self.retention.legal_hold or self.retention.retention_class is RetentionClass.LEGAL_HOLD:
            for decision in self.decisions:
                if decision.operation == "spws.operation.delete" and decision.allowed:
                    raise ValueError("policy summary permits deletion while legal hold is active")
        return self


