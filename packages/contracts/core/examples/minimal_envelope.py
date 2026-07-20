from datetime import UTC, datetime, timedelta

from spws_contracts_core import (
    ActivityReference,
    AgentReference,
    AgentType,
    CoreObjectEnvelope,
    DeletionMode,
    DirectPolicySummary,
    DirectProvenanceSummary,
    PayloadDescriptor,
    PayloadKind,
    PrivacyClass,
    PrivacyPolicy,
    ProcessingState,
    RetentionClass,
    RetentionPolicy,
    SchemaReference,
    TransmissionClass,
    digest_json,
    new_uuid7,
)

now = datetime.now(UTC)
agent = AgentReference(agent_id=new_uuid7(), agent_type=AgentType.PERSON, display_name="Writer")
activity = ActivityReference(
    activity_id=new_uuid7(),
    activity_type="spws.activity.ingest",
    status=ProcessingState.SUCCEEDED,
    started_at=now,
    ended_at=now + timedelta(milliseconds=1),
    responsible_agents=(agent,),
)
payload_value = {"text": "A line enters the studio."}

envelope = CoreObjectEnvelope(
    schema=SchemaReference(
        schema_id="urn:pkl:spws:schema:contracts-core:core-object-envelope:0.1.0",
        schema_version="0.1.0",
    ),
    object_type="spws.object.raw_source",
    object_id=new_uuid7(),
    version_id=new_uuid7(),
    created_at=now,
    payload=PayloadDescriptor(
        payload_kind=PayloadKind.EMBEDDED,
        media_type="application/json",
        value=payload_value,
        digest=digest_json(payload_value),
    ),
    provenance=DirectProvenanceSummary(creator=agent, creation_activity=activity),
    policy=DirectPolicySummary(
        privacy=PrivacyPolicy(
            privacy_class=PrivacyClass.PRIVATE,
            transmission_class=TransmissionClass.LOCAL_ONLY,
        ),
        retention=RetentionPolicy(
            retention_class=RetentionClass.PROJECT_LIFETIME,
            deletion_mode=DeletionMode.TOMBSTONE_ONLY,
        ),
    ),
).with_calculated_record_digest()

print(envelope.model_dump_json(indent=2, by_alias=True))
