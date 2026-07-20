from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from spws_contracts_core.digests import (
    CanonicalisationMethod,
    CanonicalisationRecord,
    DigestBasis,
    DigestRecord,
    digest_bytes,
    digest_json,
    digest_text,
    verify_digest,
)
from spws_contracts_core.envelope import CoreObjectEnvelope, ObjectState, PayloadDescriptor, PayloadKind
from spws_contracts_core.extensions import ExtensionRecord
from spws_contracts_core.identifiers import new_uuid7
from spws_contracts_core.policy import (
    AuthorityTier,
    ConstraintOperator,
    DeletionMode,
    DirectPolicySummary,
    DutyRecord,
    EvidenceRecord,
    PolicyConstraint,
    PolicyContext,
    PolicyDecision,
    PolicyDecisionOutcome,
    PolicyEffect,
    PrivacyClass,
    PrivacyPolicy,
    RetentionClass,
    RetentionPolicy,
    RightsAssertion,
    TransmissionClass,
    UsageRule,
    evaluate_policy,
)
from spws_contracts_core.provenance import (
    ActivityReference,
    ContributionRecord,
    DirectProvenanceSummary,
    ProvenanceRelation,
)
from spws_contracts_core.quality import (
    ConfidenceKind,
    ConfidenceRecord,
    FailureRecord,
    PresenceState,
    ProcessingState,
    QualifiedValue,
    ReviewState,
    Severity,
)
from spws_contracts_core.references import AgentReference, AgentType, ObjectReference, VersionReference
from spws_contracts_core.schema import SchemaReference, VersionRange
from spws_contracts_core.text import (
    MappingKind,
    RelocationRecord,
    RelocationResult,
    SpanMapSegment,
    SpanMapping,
    TextQuoteSelector,
    TextRepresentation,
    TextSpan,
    RepresentationType,
    code_point_to_utf16_index,
    text_representation_from_content,
    utf16_to_code_point_index,
)


def test_policy_rule_matching_filters_target_agent_purpose_and_time(now, agent):
    op = "spws.operation.quote"
    target = ObjectReference(object_id=new_uuid7())
    other_target = ObjectReference(object_id=new_uuid7())
    rule = UsageRule(
        rule_id=new_uuid7(),
        operation=op,
        effect=PolicyEffect.PERMIT,
        authority_tier=AuthorityTier.PROJECT_POLICY,
        target=target,
        agent=agent,
        purpose="criticism",
    )
    assert not evaluate_policy(
        (rule,), PolicyContext(operation=op, target=other_target, agent=agent, purpose="criticism", evaluated_at=now), decision_id=new_uuid7()
    ).allowed
    other_agent = AgentReference(agent_id=new_uuid7(), agent_type=AgentType.PERSON)
    assert not evaluate_policy(
        (rule,), PolicyContext(operation=op, target=target, agent=other_agent, purpose="criticism", evaluated_at=now), decision_id=new_uuid7()
    ).allowed
    assert not evaluate_policy(
        (rule,), PolicyContext(operation=op, target=target, agent=agent, purpose="research", evaluated_at=now), decision_id=new_uuid7()
    ).allowed


def test_constraint_operators(now):
    op = "spws.operation.quote"
    base = dict(rule_id=new_uuid7(), operation=op, effect=PolicyEffect.PERMIT, authority_tier=AuthorityTier.PROJECT_POLICY)
    cases = [
        (ConstraintOperator.EQUALS, 3, 3, True),
        (ConstraintOperator.NOT_EQUALS, 3, 4, True),
        (ConstraintOperator.IN, [1, 2], 2, True),
        (ConstraintOperator.NOT_IN, [1, 2], 3, True),
        (ConstraintOperator.GREATER_THAN_OR_EQUAL, 2, 3, True),
        (ConstraintOperator.CONTAINS, "x", "abcx", True),
    ]
    for index, (operator, expected, actual, allowed) in enumerate(cases):
        rule = UsageRule(
            **{**base, "rule_id": new_uuid7()},
            constraints=(PolicyConstraint(constraint_type="spws.constraint.use_count", operator=operator, value=expected),),
        )
        decision = evaluate_policy(
            (rule,),
            PolicyContext(operation=op, evaluated_at=now, attributes={"use_count": actual}),
            decision_id=new_uuid7(),
        )
        assert decision.allowed is allowed


def test_quality_additional_invariants():
    with pytest.raises(ValidationError):
        ConfidenceRecord(kind=ConfidenceKind.ORDINAL, value=1, method="x")
    with pytest.raises(ValidationError):
        QualifiedValue[str](presence=PresenceState.PRESENT)
    with pytest.raises(ValidationError):
        QualifiedValue[str](presence=PresenceState.AMBIGUOUS)
    with pytest.raises(ValidationError):
        FailureRecord(
            failure_id=new_uuid7(),
            code="COC-F-001",
            name="invalid_identifier",
            severity=Severity.INFO,
            scope="id",
        )


def test_text_representation_span_mapping_and_relocation_invariants():
    owner = VersionReference(object_id=new_uuid7(), version_id=new_uuid7())
    with pytest.raises(ValidationError):
        TextRepresentation(
            representation_id=new_uuid7(),
            owner_version=owner,
            representation_type=RepresentationType.DECODED_TEXT,
            media_type="text/plain",
            character_encoding="utf-8",
            code_point_length=1,
            content_digest=digest_bytes(b"x"),
        )
    span = TextSpan(
        span_id="s",
        representation_id=new_uuid7(),
        representation_version=owner,
        start=0,
        end=1,
        quote=TextQuoteSelector(exact="x", prefix="bad"),
    )
    with pytest.raises(ValueError):
        span.validate_against("x")
    with pytest.raises(ValidationError):
        SpanMapSegment(raw_start=0, raw_end=2, derived_start=0, derived_end=1, kind=MappingKind.EQUAL)
    with pytest.raises(ValidationError):
        SpanMapping(
            mapping_id=new_uuid7(),
            source_representation_id=new_uuid7(),
            target_representation_id=new_uuid7(),
            segments=(SpanMapSegment(raw_start=1, raw_end=1, derived_start=0, derived_end=1, kind=MappingKind.INSERT),),
            source_length=1,
            target_length=1,
        )
    with pytest.raises(ValidationError):
        RelocationRecord(
            source_span=span.model_copy(update={"quote": None}),
            target_representation_id=new_uuid7(),
            result=RelocationResult.UNIQUE,
            relocated_start=3,
            relocated_end=2,
        )
    with pytest.raises(ValueError):
        code_point_to_utf16_index("x", 2)
    with pytest.raises(ValueError):
        utf16_to_code_point_index("x", 2)
    rep = text_representation_from_content(
        representation_id=new_uuid7(),
        owner_version=owner,
        text="x",
        representation_type=RepresentationType.DECODED_TEXT,
    )
    assert rep.code_point_length == 1


def test_schema_range_and_uri_validation():
    with pytest.raises(ValidationError):
        SchemaReference(schema_id="relative/path", schema_version="1.0.0")
    with pytest.raises(ValidationError):
        VersionRange(minimum="2.0.0", maximum="1.0.0")


