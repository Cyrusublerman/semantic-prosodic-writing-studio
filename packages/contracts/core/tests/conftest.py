from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from spws_contracts_core.digests import digest_json
from spws_contracts_core.envelope import PayloadDescriptor, PayloadKind
from spws_contracts_core.identifiers import new_uuid7
from spws_contracts_core.policy import (
    DeletionMode,
    DirectPolicySummary,
    PrivacyClass,
    PrivacyPolicy,
    RetentionClass,
    RetentionPolicy,
    TransmissionClass,
)
from spws_contracts_core.provenance import (
    ActivityReference,
    AgentReference,
    AgentType,
    DirectProvenanceSummary,
)
from spws_contracts_core.quality import ProcessingState


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 7, 17, 0, 0, tzinfo=UTC)


@pytest.fixture
def agent() -> AgentReference:
    return AgentReference(
        agent_id=new_uuid7(),
        agent_type=AgentType.PERSON,
        display_name="Test User",
    )


@pytest.fixture
def activity(now, agent) -> ActivityReference:
    return ActivityReference(
        activity_id=new_uuid7(),
        activity_type="spws.activity.ingest",
        status=ProcessingState.SUCCEEDED,
        started_at=now,
        ended_at=now + timedelta(seconds=1),
        responsible_agents=(agent,),
    )


@pytest.fixture
def provenance(agent, activity) -> DirectProvenanceSummary:
    return DirectProvenanceSummary(creator=agent, creation_activity=activity)


@pytest.fixture
def policy() -> DirectPolicySummary:
    return DirectPolicySummary(
        privacy=PrivacyPolicy(
            privacy_class=PrivacyClass.PRIVATE,
            transmission_class=TransmissionClass.LOCAL_ONLY,
        ),
        retention=RetentionPolicy(
            retention_class=RetentionClass.PROJECT_LIFETIME,
            deletion_mode=DeletionMode.TOMBSTONE_ONLY,
        ),
    )


@pytest.fixture
def payload() -> PayloadDescriptor:
    value = {"text": "example"}
    return PayloadDescriptor(
        payload_kind=PayloadKind.EMBEDDED,
        media_type="application/json",
        value=value,
        digest=digest_json(value),
    )
