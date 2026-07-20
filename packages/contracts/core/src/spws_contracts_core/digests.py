from __future__ import annotations

import hashlib
import math
from enum import StrEnum
from typing import Any, Mapping, Sequence

import rfc8785
from pydantic import Field, field_validator, model_validator

from .base import ContractModel

SAFE_JSON_INTEGER = 2**53 - 1
RECORD_PROJECTION_V1 = "urn:pkl:spws:digest-projection:core-record:1"


class DigestAlgorithm(StrEnum):
    SHA256 = "sha-256"


class DigestBasis(StrEnum):
    RAW_BYTES = "raw_bytes"
    UTF8_TEXT = "utf8_text"
    JCS_JSON = "jcs_json"
    RECORD_PROJECTION = "record_projection"


class CanonicalisationMethod(StrEnum):
    NONE = "none"
    UNICODE_PROFILE = "unicode_profile"
    RFC8785_JCS = "rfc8785_jcs"
    DOMAIN_PROJECTION = "domain_projection"


class VerificationState(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    MISMATCH = "mismatch"


class CanonicalisationRecord(ContractModel):
    method: CanonicalisationMethod
    version: str | None = None


class DigestRecord(ContractModel):
    algorithm: DigestAlgorithm = DigestAlgorithm.SHA256
    value: str = Field(pattern=r"^[0-9a-f]{64}$")
    basis: DigestBasis
    byte_length: int = Field(ge=0)
    media_type: str | None = Field(default=None, max_length=255)
    character_encoding: str | None = Field(default=None, max_length=64)
    canonicalisation: CanonicalisationRecord | None = None
    verification_state: VerificationState = VerificationState.UNVERIFIED

    @model_validator(mode="after")
    def validate_basis(self) -> "DigestRecord":
        if self.basis in {DigestBasis.JCS_JSON, DigestBasis.RECORD_PROJECTION}:
            if self.canonicalisation is None:
                raise ValueError("structured digest requires canonicalisation record")
        return self


def _validate_json_domain(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        if abs(value) > SAFE_JSON_INTEGER:
            raise ValueError(f"unsafe JSON integer at {path}")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite number at {path}")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"non-string JSON object key at {path}")
            _validate_json_domain(item, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_json_domain(item, f"{path}[{index}]")
        return
    raise ValueError(f"unsupported JSON value at {path}: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    _validate_json_domain(value)
    try:
        return rfc8785.dumps(value)
    except (rfc8785.CanonicalizationError, TypeError, ValueError) as exc:
        raise ValueError("RFC 8785 canonicalisation failed") from exc


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_bytes(data: bytes, *, media_type: str | None = None) -> DigestRecord:
    return DigestRecord(
        value=_sha256(data),
        basis=DigestBasis.RAW_BYTES,
        byte_length=len(data),
        media_type=media_type,
        canonicalisation=CanonicalisationRecord(method=CanonicalisationMethod.NONE),
        verification_state=VerificationState.VERIFIED,
    )


def digest_text(
    text: str,
    *,
    media_type: str = "text/plain",
    character_encoding: str = "utf-8",
    unicode_profile: str | None = None,
) -> DigestRecord:
    if character_encoding.lower() != "utf-8":
        raise ValueError("core text digests require UTF-8")
    data = text.encode("utf-8")
    canonicalisation = CanonicalisationRecord(
        method=CanonicalisationMethod.UNICODE_PROFILE if unicode_profile else CanonicalisationMethod.NONE,
        version=unicode_profile,
    )
    return DigestRecord(
        value=_sha256(data),
        basis=DigestBasis.UTF8_TEXT,
        byte_length=len(data),
        media_type=media_type,
        character_encoding="utf-8",
        canonicalisation=canonicalisation,
        verification_state=VerificationState.VERIFIED,
    )


def digest_json(value: Any, *, media_type: str = "application/json") -> DigestRecord:
    data = canonical_json_bytes(value)
    return DigestRecord(
        value=_sha256(data),
        basis=DigestBasis.JCS_JSON,
        byte_length=len(data),
        media_type=media_type,
        character_encoding="utf-8",
        canonicalisation=CanonicalisationRecord(
            method=CanonicalisationMethod.RFC8785_JCS, version="RFC8785"
        ),
        verification_state=VerificationState.VERIFIED,
    )


def digest_record_projection(value: Mapping[str, Any]) -> DigestRecord:
    projection = dict(value)
    projection["projection_id"] = RECORD_PROJECTION_V1
    data = canonical_json_bytes(projection)
    return DigestRecord(
        value=_sha256(data),
        basis=DigestBasis.RECORD_PROJECTION,
        byte_length=len(data),
        media_type="application/json",
        character_encoding="utf-8",
        canonicalisation=CanonicalisationRecord(
            method=CanonicalisationMethod.DOMAIN_PROJECTION,
            version=RECORD_PROJECTION_V1,
        ),
        verification_state=VerificationState.VERIFIED,
    )


def verify_digest(record: DigestRecord, data: bytes) -> bool:
    if record.algorithm is not DigestAlgorithm.SHA256:
        raise ValueError("unsupported digest algorithm")
    return _sha256(data) == record.value
