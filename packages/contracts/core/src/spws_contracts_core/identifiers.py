from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator
from typing_extensions import TypeAliasType
from uuid_utils import uuid7 as _uuid7


def _validate_uuid7(value: UUID) -> UUID:
    if not isinstance(value, UUID):
        raise TypeError("identifier must be a uuid.UUID")
    if value.version != 7:
        raise ValueError("identifier must be UUID version 7")
    if value.variant != "specified in RFC 4122":
        raise ValueError("identifier must use the RFC variant")
    return value


UUID7 = TypeAliasType("UUID7", Annotated[UUID, AfterValidator(_validate_uuid7)])
ObjectId = TypeAliasType("ObjectId", UUID7)
VersionId = TypeAliasType("VersionId", UUID7)
ActivityId = TypeAliasType("ActivityId", UUID7)
AgentId = TypeAliasType("AgentId", UUID7)
RunId = TypeAliasType("RunId", UUID7)
StepRunId = TypeAliasType("StepRunId", UUID7)
RelationId = TypeAliasType("RelationId", UUID7)
ContributionId = TypeAliasType("ContributionId", UUID7)
ReviewId = TypeAliasType("ReviewId", UUID7)
RuleId = TypeAliasType("RuleId", UUID7)
AssertionId = TypeAliasType("AssertionId", UUID7)
DecisionId = TypeAliasType("DecisionId", UUID7)
RepresentationId = TypeAliasType("RepresentationId", UUID7)
MappingId = TypeAliasType("MappingId", UUID7)
WarningId = TypeAliasType("WarningId", UUID7)
FailureId = TypeAliasType("FailureId", UUID7)


def new_uuid7() -> UUID:
    """Mint a UUIDv7 and return the standard-library UUID type."""

    return UUID(str(_uuid7()))
