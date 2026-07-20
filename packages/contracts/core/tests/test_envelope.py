from pydantic import ValidationError
import pytest

from spws_contracts_core.envelope import CoreObjectEnvelope, ObjectState, PayloadDescriptor, PayloadKind
from spws_contracts_core.identifiers import new_uuid7
from spws_contracts_core.schema import SchemaReference
from spws_contracts_core.quality import ReviewState


def make_envelope(now, provenance, policy, payload, **updates):
    values = dict(
        schema=SchemaReference(
            schema_id="urn:pkl:spws:schema:contracts-core:core-object-envelope:0.1.0",
            schema_version="0.1.0",
        ),
        object_type="spws.object.raw_source",
        object_id=new_uuid7(),
        version_id=new_uuid7(),
        created_at=now,
        payload=payload,
        provenance=provenance,
        policy=policy,
    )
    values.update(updates)
    return CoreObjectEnvelope(**values)


def test_envelope_record_digest_is_stable(now, provenance, policy, payload):
    envelope = make_envelope(now, provenance, policy, payload)
    first = envelope.with_calculated_record_digest()
    second = envelope.with_calculated_record_digest()
    assert first.record_digest.value == second.record_digest.value
    assert first.verify_record_digest()


def test_record_digest_changes_with_semantic_field(now, provenance, policy, payload):
    envelope = make_envelope(now, provenance, policy, payload)
    changed = envelope.model_copy(update={"review_state": ReviewState.APPROVED})
    assert envelope.calculated_record_digest().value != changed.calculated_record_digest().value


def test_parent_versions_are_sorted_in_projection(now, provenance, policy, payload):
    parent_a, parent_b = new_uuid7(), new_uuid7()
    envelope = make_envelope(
        now,
        provenance,
        policy,
        payload,
        parent_version_ids=(parent_b, parent_a),
    )
    assert envelope.projection_v1()["parent_version_ids"] == sorted([str(parent_a), str(parent_b)])


def test_envelope_rejects_unregistered_object_type(now, provenance, policy, payload):
    with pytest.raises(ValidationError):
        make_envelope(now, provenance, policy, payload, object_type="spws.object.unknown")


def test_tombstone_has_no_payload(now, provenance, policy):
    envelope = make_envelope(
        now,
        provenance,
        policy,
        PayloadDescriptor(payload_kind=PayloadKind.TOMBSTONE),
        object_type="spws.object.tombstone",
        state=ObjectState.TOMBSTONED,
    )
    assert envelope.payload.payload_kind is PayloadKind.TOMBSTONE


def test_envelope_json_schema_is_draft_2020_12_compatible():
    schema = CoreObjectEnvelope.model_json_schema(mode="validation")
    assert "$defs" in schema
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
