from __future__ import annotations

import difflib
import unicodedata

from pydantic import Field, model_validator

from .base import ContractModel
from .digests import digest_text
from .identifiers import MappingId, RepresentationId
from .references import VersionReference
from .text_types import (
    MappingKind, MappingResult, RelocationResult, RepresentationType,
    TextRepresentation, TextSpan,
)


class SpanMapSegment(ContractModel):
    raw_start: int = Field(ge=0)
    raw_end: int = Field(ge=0)
    derived_start: int = Field(ge=0)
    derived_end: int = Field(ge=0)
    kind: MappingKind

    @model_validator(mode="after")
    def validate_ranges(self) -> "SpanMapSegment":
        if self.raw_end < self.raw_start or self.derived_end < self.derived_start:
            raise ValueError("mapping segment ranges must be ordered")
        if self.kind is MappingKind.EQUAL and (
            self.raw_end - self.raw_start != self.derived_end - self.derived_start
        ):
            raise ValueError("equal mapping segment must preserve length")
        if self.kind is MappingKind.INSERT and self.raw_end != self.raw_start:
            raise ValueError("insert segment must have empty raw range")
        if self.kind is MappingKind.DELETE and self.derived_end != self.derived_start:
            raise ValueError("delete segment must have empty derived range")
        return self


class SpanMapping(ContractModel):
    mapping_id: MappingId
    source_representation_id: RepresentationId
    target_representation_id: RepresentationId
    segments: tuple[SpanMapSegment, ...]
    source_length: int = Field(ge=0)
    target_length: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_coverage_and_order(self) -> "SpanMapping":
        if not self.segments and (self.source_length or self.target_length):
            raise ValueError("non-empty representation requires mapping segments")
        previous_raw = previous_derived = 0
        for segment in self.segments:
            if segment.raw_start != previous_raw or segment.derived_start != previous_derived:
                raise ValueError("mapping segments must be contiguous and non-overlapping")
            previous_raw = segment.raw_end
            previous_derived = segment.derived_end
        if self.segments:
            if self.segments[0].raw_start != 0 or self.segments[0].derived_start != 0:
                raise ValueError("mapping must begin at both zero boundaries")
            if self.segments[-1].raw_end != self.source_length:
                raise ValueError("mapping does not cover source length")
            if self.segments[-1].derived_end != self.target_length:
                raise ValueError("mapping does not cover target length")
        return self

    def map_forward(self, start: int, end: int) -> tuple[MappingResult, tuple[int, int] | None]:
        if start < 0 or end < start or end > self.source_length:
            raise ValueError("invalid source range")
        overlaps = [
            segment
            for segment in self.segments
            if not (segment.raw_end <= start or segment.raw_start >= end)
            or (start == end and segment.raw_start <= start <= segment.raw_end)
        ]
        if not overlaps:
            return MappingResult.UNMAPPABLE, None
        if all(segment.kind is MappingKind.EQUAL for segment in overlaps):
            first = overlaps[0]
            last = overlaps[-1]
            mapped_start = first.derived_start + (start - first.raw_start)
            mapped_end = last.derived_start + (end - last.raw_start)
            return MappingResult.EXACT, (mapped_start, mapped_end)
        low = min(segment.derived_start for segment in overlaps)
        high = max(segment.derived_end for segment in overlaps)
        return MappingResult.BOUNDED, (low, high)


class RelocationRecord(ContractModel):
    source_span: TextSpan
    target_representation_id: RepresentationId
    result: RelocationResult
    relocated_start: int | None = Field(default=None, ge=0)
    relocated_end: int | None = Field(default=None, ge=0)
    candidate_ranges: tuple[tuple[int, int], ...] = ()
    explanation: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def validate_result_fields(self) -> "RelocationRecord":
        if self.result is RelocationResult.UNIQUE:
            if self.relocated_start is None or self.relocated_end is None:
                raise ValueError("unique relocation requires relocated range")
            if self.relocated_end < self.relocated_start:
                raise ValueError("relocated range must be ordered")
        elif self.relocated_start is not None or self.relocated_end is not None:
            raise ValueError("non-unique relocation must not claim a single range")
        if self.result is RelocationResult.AMBIGUOUS and len(self.candidate_ranges) < 2:
            raise ValueError("ambiguous relocation requires multiple candidates")
        if any(end < start for start, end in self.candidate_ranges):
            raise ValueError("candidate relocation ranges must be ordered")
        return self


def build_span_mapping(
    source: str,
    target: str,
    *,
    mapping_id: MappingId,
    source_representation_id: RepresentationId,
    target_representation_id: RepresentationId,
) -> SpanMapping:
    matcher = difflib.SequenceMatcher(a=source, b=target, autojunk=False)
    segments: list[SpanMapSegment] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        kind = {
            "equal": MappingKind.EQUAL,
            "replace": MappingKind.REPLACE,
            "delete": MappingKind.DELETE,
            "insert": MappingKind.INSERT,
        }[tag]
        segments.append(
            SpanMapSegment(
                raw_start=i1,
                raw_end=i2,
                derived_start=j1,
                derived_end=j2,
                kind=kind,
            )
        )
    return SpanMapping(
        mapping_id=mapping_id,
        source_representation_id=source_representation_id,
        target_representation_id=target_representation_id,
        segments=tuple(segments),
        source_length=len(source),
        target_length=len(target),
    )


def normalise_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalise_nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def text_representation_from_content(
    *,
    representation_id: RepresentationId,
    owner_version: VersionReference,
    text: str,
    representation_type: RepresentationType,
    normalisation_profile: str | None = None,
) -> TextRepresentation:
    return TextRepresentation(
        representation_id=representation_id,
        owner_version=owner_version,
        representation_type=representation_type,
        media_type="text/plain",
        character_encoding="utf-8",
        content_digest=digest_text(text, unicode_profile=normalisation_profile),
        code_point_length=len(text),
        byte_length=len(text.encode("utf-8")),
        normalisation_profile=normalisation_profile,
        runtime_unicode_version=unicodedata.unidata_version,
    )
