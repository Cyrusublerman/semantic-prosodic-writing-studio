from datetime import timedelta

import pytest
from pydantic import ValidationError

from spws_contracts_core.identifiers import new_uuid7
from spws_contracts_core.provenance import (
    ActivityReference,
    AgentReference,
    AgentType,
    ContributionRecord,
    DirectProvenanceSummary,
    ProvenanceRelation,
)
from spws_contracts_core.quality import ProcessingState, ReviewState
from spws_contracts_core.references import VersionReference


def test_completed_activity_requires_end_time(now, agent):
    with pytest.raises(ValidationError):
        ActivityReference(
            activity_id=new_uuid7(),
            activity_type="spws.activity.analyse",
            status=ProcessingState.SUCCEEDED,
            started_at=now,
            responsible_agents=(agent,),
        )


def test_activity_rejects_unknown_type(now, agent):
    with pytest.raises(ValidationError):
        ActivityReference(
            activity_id=new_uuid7(),
            activity_type="spws.activity.unknown",
            status=ProcessingState.RUNNING,
            started_at=now,
            responsible_agents=(agent,),
        )


def test_direct_provenance_creator_must_be_responsible(activity):
    other = AgentReference(agent_id=new_uuid7(), agent_type=AgentType.PERSON)
    with pytest.raises(ValidationError):
        DirectProvenanceSummary(creator=other, creation_activity=activity)


def test_relation_and_contribution_use_registered_vocabularies(agent, activity):
    subject = VersionReference(object_id=new_uuid7(), version_id=new_uuid7())
    source = VersionReference(object_id=new_uuid7(), version_id=new_uuid7())
    relation = ProvenanceRelation(
        relation_id=new_uuid7(),
        relation_type="spws.prov.derived_from",
        subject=subject,
        object=source,
        activity_id=activity.activity_id,
        entity_role="spws.role.primary_input",
        review_state=ReviewState.MACHINE_CHECKED,
    )
    contribution = ContributionRecord(
        contribution_id=new_uuid7(),
        role="spws.contribution.user_original",
        agent=agent,
        activity_id=activity.activity_id,
        target=subject,
    )
    assert relation.object.version_id == source.version_id
    assert contribution.target == subject


def test_relation_rejects_self_reference():
    value = VersionReference(object_id=new_uuid7(), version_id=new_uuid7())
    with pytest.raises(ValidationError):
        ProvenanceRelation(
            relation_id=new_uuid7(),
            relation_type="spws.prov.derived_from",
            subject=value,
            object=value,
        )
