from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Annotated
from urllib.parse import urlparse

from pydantic import AfterValidator, Field, model_validator
from typing_extensions import TypeAliasType

from .base import ContractModel

_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\."
    r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


def _validate_semver(value: str) -> str:
    if not _SEMVER_RE.fullmatch(value):
        raise ValueError("value must be a Semantic Versioning 2.0.0 string")
    return value


def _validate_absolute_uri(value: str) -> str:
    parsed = urlparse(value)
    if not parsed.scheme:
        raise ValueError("schema_id must be an absolute URI")
    if parsed.scheme == "urn" and not parsed.path:
        raise ValueError("URN must contain a namespace-specific string")
    return value


SemVer = TypeAliasType(
    "SemVer",
    Annotated[str, AfterValidator(_validate_semver), Field(pattern=_SEMVER_RE.pattern)],
)
AbsoluteUri = TypeAliasType("AbsoluteUri", Annotated[str, AfterValidator(_validate_absolute_uri)])


@dataclass(frozen=True)
class SemVerParts:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()


def parse_semver(value: str) -> SemVerParts:
    match = _SEMVER_RE.fullmatch(value)
    if match is None:
        raise ValueError("invalid semantic version")
    prerelease = tuple(match.group(4).split(".")) if match.group(4) else ()
    return SemVerParts(int(match.group(1)), int(match.group(2)), int(match.group(3)), prerelease)


def compare_semver(left: SemVerParts, right: SemVerParts) -> int:
    left_core = (left.major, left.minor, left.patch)
    right_core = (right.major, right.minor, right.patch)
    if left_core != right_core:
        return -1 if left_core < right_core else 1
    if not left.prerelease and not right.prerelease:
        return 0
    if not left.prerelease:
        return 1
    if not right.prerelease:
        return -1
    for a, b in zip(left.prerelease, right.prerelease):
        if a == b:
            continue
        a_numeric = a.isdigit()
        b_numeric = b.isdigit()
        if a_numeric and b_numeric:
            return -1 if int(a) < int(b) else 1
        if a_numeric != b_numeric:
            return -1 if a_numeric else 1
        return -1 if a < b else 1
    if len(left.prerelease) == len(right.prerelease):
        return 0
    return -1 if len(left.prerelease) < len(right.prerelease) else 1


class SchemaReference(ContractModel):
    schema_id: AbsoluteUri
    schema_version: SemVer
    schema_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_version_in_urn(self) -> "SchemaReference":
        if self.schema_id.startswith("urn:pkl:spws:schema:"):
            suffix = self.schema_id.rsplit(":", 1)[-1]
            if suffix != self.schema_version:
                raise ValueError("SPWS schema URN version must equal schema_version")
        return self


class VersionRange(ContractModel):
    minimum: SemVer | None = None
    maximum: SemVer | None = None
    include_minimum: bool = True
    include_maximum: bool = False
    required_major: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_bounds(self) -> "VersionRange":
        if self.minimum and self.maximum:
            if compare_semver(parse_semver(self.maximum), parse_semver(self.minimum)) < 0:
                raise ValueError("maximum version must not be lower than minimum")
        return self

    def contains(self, value: str) -> bool:
        candidate = parse_semver(_validate_semver(value))
        if self.required_major is not None and candidate.major != self.required_major:
            return False
        if self.minimum is not None:
            lower = parse_semver(self.minimum)
            comparison = compare_semver(candidate, lower)
            if comparison < 0 or (comparison == 0 and not self.include_minimum):
                return False
        if self.maximum is not None:
            upper = parse_semver(self.maximum)
            comparison = compare_semver(candidate, upper)
            if comparison > 0 or (comparison == 0 and not self.include_maximum):
                return False
        return True
