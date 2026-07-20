from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, JsonValue, field_validator, model_validator

from .base import ContractModel
from .digests import DigestBasis, DigestRecord, digest_record_projection
from .extensions import ExtensionRecord, check_extensions
from .identifiers import ObjectId, VersionId
from .policy import DirectPolicySummary
from .provenance import DirectProvenanceSummary
from .quality import FailureRecord, ReviewRecord, ReviewState, WarningRecord
from .references import RegisteredIdentifier
from .registry import validate_registered
from .schema import AbsoluteUri, SchemaReference
from .time import UtcDateTime, format_rfc3339_utc


class ObjectState(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    INVALIDATED = "invalidated"
    TOMBSTONED = "tombstoned"


class PayloadKind(StrEnum):
    EMBEDDED = "embedded"
    OBJECT_STORE = "object_store"
    EXTERNAL = "external"
    TOMBSTONE = "tombstone"


class PayloadDescriptor(ContractModel):
    payload_kind: PayloadKind
    media_type: str | None = Field(default=None, max_length=255)
    value: JsonValue | None = None
    location_reference: str | None = Field(default=None, max_length=2048)
    uri: AbsoluteUri | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    digest: DigestRecord | None = None

    @model_validator(mode="after")
    def validate_payload_kind(self) -> "PayloadDescriptor":
        if self.payload_kind is PayloadKind.EMBEDDED:
            if self.value is None or self.digest is None:
                raise ValueError("embedded payload requires value and digest")
            if self.location_reference is not None or self.uri is not None:
                raise ValueError("embedded payload cannot use location or URI")
            from .digests import DigestBasis, digest_json, digest_text
            if self.digest.basis is DigestBasis.JCS_JSON:
                if digest_json(self.value).value != self.digest.value:
                    raise ValueError("embedded JSON payload digest mismatch")
            elif self.digest.basis is DigestBasis.UTF8_TEXT:
                if not isinstance(self.value, str):
                    raise ValueError("UTF-8 text digest requires embedded string value")
                if digest_text(self.value).value != self.digest.value:
                    raise ValueError("embedded text payload digest mismatch")
        elif self.payload_kind is PayloadKind.OBJECT_STORE:
            if self.location_reference is None or self.digest is None or self.size_bytes is None:
                raise ValueError("object-store payload requires location, digest and size")
            if self.value is not None or self.uri is not None:
                raise ValueError("object-store payload cannot embed value or external URI")
        elif self.payload_kind is PayloadKind.EXTERNAL:
            if self.uri is None:
                raise ValueError("external payload requires URI")
            if self.value is not None or self.location_reference is not None:
                raise ValueError("external payload cannot embed value or local location")
        elif self.payload_kind is PayloadKind.TOMBSTONE:
            if any(
                item is not None
                for item in (self.value, self.location_reference, self.uri, self.size_bytes, self.digest)
            ):
                raise ValueError("tombstone payload must contain no payload data")
        return self


class CoreObjectEnvelope(ContractModel):
    schema_ref: SchemaReference = Field(alias="schema", serialization_alias="schema")
    object_type: RegisteredIdentifier
    object_id: ObjectId
    version_id: VersionId
    parent_version_ids: tuple[VersionId, ...] = ()
    state: ObjectState = ObjectState.ACTIVE
    created_at: UtcDateTime
    payload: PayloadDescriptor
    provenance: DirectProvenanceSummary
    policy: DirectPolicySummary
    review_state: ReviewState = ReviewState.UNREVIEWED
    reviews: tuple[ReviewRecord, ...] = ()
    warnings: tuple[WarningRecord, ...] = ()
    failures: tuple[FailureRecord, ...] = ()
    extensions: tuple[ExtensionRecord, ...] = ()
    record_digest: DigestRecord | None = None

    @field_validator("object_type")
    @classmethod
    def object_type_registered(cls, value: str) -> str:
        return validate_registered(value, "object_types")

    @model_validator(mode="after")
    def validate_identity_and_state(self) -> "CoreObjectEnvelope":
        if self.object_id == self.version_id:
            raise ValueError("object_id and version_id must be distinct")
        if len(self.parent_version_ids) != len(set(self.parent_version_ids)):
            raise ValueError("parent_version_ids must be unique")
        if self.version_id in self.parent_version_ids:
            raise ValueError("version cannot be its own parent")
        if self.state is ObjectState.TOMBSTONED:
            if self.object_type != "spws.object.tombstone":
                raise ValueError("tombstoned envelope must use tombstone object type")
            if self.payload.payload_kind is not PayloadKind.TOMBSTONE:
                raise ValueError("tombstoned envelope must contain tombstone payload")
        if self.record_digest is not None and self.record_digest.basis is not DigestBasis.RECORD_PROJECTION:
            raise ValueError("record_digest must use record_projection basis")
        for relation in self.provenance.direct_relations:
            if relation.subject.version_id != self.version_id:
                raise ValueError("direct provenance relation subject must be this envelope version")
        for contribution in self.provenance.contribution_records:
            if contribution.target.version_id != self.version_id:
                raise ValueError("contribution target must be this envelope version")
        return self

    def check_extensions(self, understood_namespaces: set[str] | frozenset[str]) -> tuple[WarningRecord, ...]:
        return check_extensions(self.extensions, understood_namespaces)

    def projection_v1(self) -> dict[str, Any]:
        critical_extensions = sorted(
            (
                extension.model_dump(mode="json", exclude_none=True, by_alias=True)
                for extension in self.extensions
                if extension.critical
            ),
            key=lambda item: item["namespace"],
        )
        warnings = sorted(
            (item.model_dump(mode="json", exclude_none=True) for item in self.warnings),
            key=lambda item: (item["code"], item["warning_id"]),
        )
        failures = sorted(
            (item.model_dump(mode="json", exclude_none=True) for item in self.failures),
            key=lambda item: (item["code"], item["failure_id"]),
        )
        reviews = sorted(
            (item.model_dump(mode="json", exclude_none=True) for item in self.reviews),
            key=lambda item: item["review_id"],
        )
        provenance = self.provenance.model_dump(mode="json", exclude_none=True)
        policy = self.policy.model_dump(mode="json", exclude_none=True)
        return {
            "schema": self.schema_ref.model_dump(mode="json", exclude_none=True),
            "object_type": self.object_type,
            "object_id": str(self.object_id),
            "version_id": str(self.version_id),
            "parent_version_ids": sorted(str(value) for value in self.parent_version_ids),
            "state": self.state.value,
            "created_at": format_rfc3339_utc(self.created_at),
            "creating_agent": provenance["creator"],
            "creation_activity": provenance["creation_activity"],
            "payload": self.payload.model_dump(mode="json", exclude_none=True),
            "provenance": provenance,
            "policy": policy,
            "review_state": self.review_state.value,
            "reviews": reviews,
            "warnings": warnings,
            "failures": failures,
            "critical_extensions": critical_extensions,
        }

    def calculated_record_digest(self) -> DigestRecord:
        return digest_record_projection(self.projection_v1())

    def with_calculated_record_digest(self) -> "CoreObjectEnvelope":
        return self.model_copy(update={"record_digest": self.calculated_record_digest()})

    def verify_record_digest(self) -> bool:
        return self.record_digest is not None and self.record_digest.value == self.calculated_record_digest().value
