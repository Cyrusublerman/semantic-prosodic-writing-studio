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


def test_digest_record_and_helpers_reject_invalid_domains():
    with pytest.raises(ValidationError):
        DigestRecord(value="0" * 64, basis=DigestBasis.JCS_JSON, byte_length=1)
    with pytest.raises(ValueError):
        digest_text("x", character_encoding="utf-16")
    with pytest.raises(ValueError):
        digest_json({"x": object()})
    assert not verify_digest(digest_bytes(b"a"), b"b")


def test_payload_kind_exclusion_rules():
    with pytest.raises(ValidationError):
        PayloadDescriptor(
            payload_kind=PayloadKind.EMBEDDED,
            value="x",
            digest=digest_text("x"),
            location_reference="bad",
        )
    with pytest.raises(ValidationError):
        PayloadDescriptor(payload_kind=PayloadKind.OBJECT_STORE, location_reference="x")
    with pytest.raises(ValidationError):
        PayloadDescriptor(
            payload_kind=PayloadKind.OBJECT_STORE,
            location_reference="x",
            size_bytes=1,
            digest=digest_bytes(b"x"),
            value="x",
        )
    with pytest.raises(ValidationError):
        PayloadDescriptor(payload_kind=PayloadKind.EXTERNAL)
    with pytest.raises(ValidationError):
        PayloadDescriptor(payload_kind=PayloadKind.EXTERNAL, uri="https://example.com", value="x")


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


def test_envelope_identity_parent_and_tombstone_invariants(now, provenance, policy, payload):
    same = new_uuid7()
    with pytest.raises(ValidationError):
        _envelope(now, provenance, policy, payload, object_id=same, version_id=same)
    parent = new_uuid7()
    with pytest.raises(ValidationError):
        _envelope(now, provenance, policy, payload, parent_version_ids=(parent, parent))
    version = new_uuid7()
    with pytest.raises(ValidationError):
        _envelope(now, provenance, policy, payload, version_id=version, parent_version_ids=(version,))
    with pytest.raises(ValidationError):
        _envelope(now, provenance, policy, payload, state=ObjectState.TOMBSTONED)
    with pytest.raises(ValidationError):
        _envelope(
            now,
            provenance,
            policy,
            payload,
            object_type="spws.object.tombstone",
            state=ObjectState.TOMBSTONED,
        )


