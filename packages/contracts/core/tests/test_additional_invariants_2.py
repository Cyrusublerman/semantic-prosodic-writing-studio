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


def _envelope(now, provenance, policy, payload, **updates):
    data = {
        "schema": SchemaReference(
            schema_id="urn:pkl:spws:schema:contracts-core:core-object-envelope:0.1.0",
            schema_version="0.1.0",
        ),
        "object_type": "spws.object.raw_source",
        "object_id": new_uuid7(),
        "version_id": new_uuid7(),
        "created_at": now,
        "payload": payload,
        "provenance": provenance,
        "policy": policy,
    }
    data.update(updates)
    return CoreObjectEnvelope(**data)


def test_envelope_provenance_and_record_digest_invariants(now, agent, activity, policy, payload):
    own_version = new_uuid7()
    other = VersionReference(object_id=new_uuid7(), version_id=new_uuid7())
    relation = ProvenanceRelation(
        relation_id=new_uuid7(),
        relation_type="spws.prov.derived_from",
        subject=other,
        object=VersionReference(object_id=new_uuid7(), version_id=new_uuid7()),
    )
    provenance = DirectProvenanceSummary(
        creator=agent,
        creation_activity=activity,
        direct_relations=(relation,),
    )
    with pytest.raises(ValidationError):
        _envelope(now, provenance, policy, payload, version_id=own_version)
    wrong_digest = digest_json({"x": 1})
    with pytest.raises(ValidationError):
        _envelope(now, DirectProvenanceSummary(creator=agent, creation_activity=activity), policy, payload, record_digest=wrong_digest)


def test_activity_and_provenance_edge_invariants(now, agent):
    with pytest.raises(ValidationError):
        ActivityReference(
            activity_id=new_uuid7(),
            activity_type="spws.activity.ingest",
            status=ProcessingState.RUNNING,
            started_at=now,
            responsible_agents=(),
        )
    with pytest.raises(ValidationError):
        ActivityReference(
            activity_id=new_uuid7(),
            activity_type="spws.activity.ingest",
            status=ProcessingState.SUCCEEDED,
            started_at=now,
            ended_at=now - timedelta(seconds=1),
            responsible_agents=(agent,),
        )
    with pytest.raises(ValidationError):
        ActivityReference(
            activity_id=new_uuid7(),
            activity_type="spws.activity.ingest",
            status=ProcessingState.RUNNING,
            started_at=now,
            responsible_agents=(agent,),
            step_run_id=new_uuid7(),
        )
    subject = VersionReference(object_id=new_uuid7(), version_id=new_uuid7())
    with pytest.raises(ValidationError):
        ProvenanceRelation(
            relation_id=new_uuid7(),
            relation_type="spws.prov.nope",
            subject=subject,
            object=VersionReference(object_id=new_uuid7(), version_id=new_uuid7()),
        )
    with pytest.raises(ValidationError):
        ContributionRecord(
            contribution_id=new_uuid7(),
            role="spws.contribution.nope",
            agent=agent,
            target=subject,
        )


def test_rights_evidence_duty_and_rule_invariants(now, agent):
    target = ObjectReference(object_id=new_uuid7())
    with pytest.raises(ValidationError):
        EvidenceRecord(source=target, verified=True)
    with pytest.raises(ValidationError):
        RightsAssertion(
            assertion_id=new_uuid7(),
            assertion_type="spws.rights.permission",
            issuer=agent,
            target=target,
        )
    with pytest.raises(ValidationError):
        DutyRecord(duty_type="spws.duty.attribute", satisfied=True)
    with pytest.raises(ValidationError):
        UsageRule(
            rule_id=new_uuid7(),
            operation="spws.operation.publish",
            effect=PolicyEffect.PROHIBIT,
            authority_tier=AuthorityTier.PROJECT_POLICY,
            duties=(DutyRecord(duty_type="spws.duty.attribute"),),
        )
    with pytest.raises(ValidationError):
        PolicyDecision(
            decision_id=new_uuid7(),
            operation="spws.operation.publish",
            outcome=PolicyDecisionOutcome.DENY,
            allowed=True,
            explanation="bad",
            evaluated_at=now,
        )


def test_direct_policy_summary_rejects_privacy_and_hold_conflicts(now):
    allowed_transmission = PolicyDecision(
        decision_id=new_uuid7(),
        operation="spws.operation.publish",
        outcome=PolicyDecisionOutcome.PERMIT,
        allowed=True,
        explanation="allowed",
        evaluated_at=now,
    )
    with pytest.raises(ValidationError):
        DirectPolicySummary(
            privacy=PrivacyPolicy(
                privacy_class=PrivacyClass.PRIVATE,
                transmission_class=TransmissionClass.LOCAL_ONLY,
            ),
            retention=RetentionPolicy(
                retention_class=RetentionClass.INDEFINITE,
                deletion_mode=DeletionMode.TOMBSTONE_ONLY,
            ),
            decisions=(allowed_transmission,),
        )
    hold_ref = ObjectReference(object_id=new_uuid7())
    allowed_delete = allowed_transmission.model_copy(
        update={"operation": "spws.operation.delete"}
    )
    with pytest.raises(ValidationError):
        DirectPolicySummary(
            privacy=PrivacyPolicy(
                privacy_class=PrivacyClass.PRIVATE,
                transmission_class=TransmissionClass.LOCAL_ONLY,
            ),
            retention=RetentionPolicy(
                retention_class=RetentionClass.LEGAL_HOLD,
                deletion_mode=DeletionMode.BLOCKED_BY_HOLD,
                legal_hold=True,
                hold_reference=hold_ref,
            ),
            decisions=(allowed_delete,),
        )


