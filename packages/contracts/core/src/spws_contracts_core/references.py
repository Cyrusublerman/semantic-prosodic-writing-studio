from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, Field, model_validator
from typing_extensions import TypeAliasType

from .base import ContractModel
from .identifiers import AgentId, ObjectId, VersionId
from .schema import AbsoluteUri


def _validate_registered_identifier_shape(value: str) -> str:
    if not value or value != value.lower():
        raise ValueError("identifier must be non-empty lower-case ASCII")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789.-_")
    if any(character not in allowed for character in value):
        raise ValueError("identifier contains unsupported characters")
    return value


RegisteredIdentifier = TypeAliasType(
    "RegisteredIdentifier", Annotated[str, AfterValidator(_validate_registered_identifier_shape)]
)


class ResolutionState(StrEnum):
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


class ExternalIdentifier(ContractModel):
    namespace: RegisteredIdentifier
    value: str = Field(min_length=1, max_length=2048)
    uri: AbsoluteUri | None = None
    resolution_state: ResolutionState = ResolutionState.UNRESOLVED


class AgentType(StrEnum):
    PERSON = "person"
    ORGANISATION = "organisation"
    SOFTWARE_COMPONENT = "software_component"
    MODEL = "model"
    SERVICE = "service"
    SYSTEM = "system"


class AgentReference(ContractModel):
    agent_id: AgentId
    agent_type: AgentType
    display_name: str | None = Field(default=None, max_length=512)
    version: str | None = Field(default=None, max_length=255)
    external_identifiers: tuple[ExternalIdentifier, ...] = ()


class ObjectReference(ContractModel):
    object_id: ObjectId
    object_type: RegisteredIdentifier | None = None
    version_id: VersionId | None = None
    uri: AbsoluteUri | None = None
    external_identifiers: tuple[ExternalIdentifier, ...] = ()
    digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class VersionReference(ContractModel):
    object_id: ObjectId
    version_id: VersionId
    object_type: RegisteredIdentifier | None = None
    digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    def as_object_reference(self) -> ObjectReference:
        return ObjectReference(
            object_id=self.object_id,
            version_id=self.version_id,
            object_type=self.object_type,
            digest=self.digest,
        )


class ReferenceSet(ContractModel):
    references: tuple[VersionReference, ...] = ()

    @model_validator(mode="after")
    def require_unique_versions(self) -> "ReferenceSet":
        values = [item.version_id for item in self.references]
        if len(values) != len(set(values)):
            raise ValueError("reference set contains duplicate version IDs")
        return self
