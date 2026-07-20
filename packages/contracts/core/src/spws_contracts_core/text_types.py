from __future__ import annotations

from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from .base import ContractModel
from .digests import DigestRecord
from .identifiers import RepresentationId
from .references import VersionReference
from .registry import validate_registered


class RepresentationType(StrEnum):
    RAW_BYTES = "raw_bytes"
    DECODED_TEXT = "decoded_text"
    NORMALISED_TEXT = "normalised_text"
    RENDERED_TEXT = "rendered_text"
    TOKEN_SEQUENCE = "token_sequence"
    STRUCTURED_JSON = "structured_json"


class MappingKind(StrEnum):
    EQUAL = "equal"
    REPLACE = "replace"
    INSERT = "insert"
    DELETE = "delete"
    REORDER = "reorder"
    UNKNOWN = "unknown"


class MappingResult(StrEnum):
    EXACT = "exact"
    BOUNDED = "bounded"
    AMBIGUOUS = "ambiguous"
    UNMAPPABLE = "unmappable"


class RelocationResult(StrEnum):
    UNIQUE = "unique"
    AMBIGUOUS = "ambiguous"
    MISSING = "missing"
    INVALID_SOURCE = "invalid_source"
    REPRESENTATION_MISMATCH = "representation_mismatch"


class TextRepresentation(ContractModel):
    representation_id: RepresentationId
    owner_version: VersionReference
    representation_type: RepresentationType
    media_type: str = Field(min_length=1, max_length=255)
    character_encoding: str | None = Field(default=None, max_length=64)
    content_digest: DigestRecord
    code_point_length: int | None = Field(default=None, ge=0)
    byte_length: int | None = Field(default=None, ge=0)
    normalisation_profile: str | None = None
    segmentation_profile: str | None = None
    runtime_unicode_version: str | None = Field(default=None, max_length=64)

    @field_validator("normalisation_profile")
    @classmethod
    def normalisation_registered(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_registered(value, "text.normalisation_profiles")

    @field_validator("segmentation_profile")
    @classmethod
    def segmentation_registered(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_registered(value, "text.segmentation_profiles")

    @model_validator(mode="after")
    def text_requires_lengths(self) -> "TextRepresentation":
        if self.representation_type in {
            RepresentationType.DECODED_TEXT,
            RepresentationType.NORMALISED_TEXT,
            RepresentationType.RENDERED_TEXT,
        }:
            if self.character_encoding is None or self.code_point_length is None:
                raise ValueError("text representation requires encoding and code-point length")
            if self.content_digest.basis.value != "utf8_text":
                raise ValueError("text representation requires UTF-8 text digest")
        elif self.representation_type is RepresentationType.RAW_BYTES:
            if self.content_digest.basis.value != "raw_bytes":
                raise ValueError("raw byte representation requires raw-bytes digest")
        elif self.representation_type is RepresentationType.STRUCTURED_JSON:
            if self.content_digest.basis.value != "jcs_json":
                raise ValueError("structured JSON representation requires JCS digest")
        return self


class TextQuoteSelector(ContractModel):
    exact: str = Field(min_length=1)
    prefix: str | None = None
    suffix: str | None = None


class TextSpan(ContractModel):
    span_id: str = Field(min_length=1, max_length=255)
    representation_id: RepresentationId
    representation_version: VersionReference
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    coordinate_profile: str = "unicode-code-point-zero-based-half-open-v1"
    quote: TextQuoteSelector | None = None
    runtime_unicode_version: str | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "TextSpan":
        if self.end < self.start:
            raise ValueError("span end must not precede start")
        return self

    def validate_against(self, text: str) -> None:
        if self.end > len(text):
            raise ValueError("span exceeds text length")
        if self.quote is not None:
            selected = text[self.start : self.end]
            if selected != self.quote.exact:
                raise ValueError("span exact quote does not match text")
            if self.quote.prefix is not None:
                actual = text[max(0, self.start - len(self.quote.prefix)) : self.start]
                if actual != self.quote.prefix:
                    raise ValueError("span prefix does not match text")
            if self.quote.suffix is not None:
                actual = text[self.end : self.end + len(self.quote.suffix)]
                if actual != self.quote.suffix:
                    raise ValueError("span suffix does not match text")


