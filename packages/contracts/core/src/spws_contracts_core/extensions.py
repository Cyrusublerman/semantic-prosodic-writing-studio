from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import Field, JsonValue, model_validator

from .base import ContractModel
from .identifiers import new_uuid7
from .quality import Severity, WarningRecord
from .schema import SchemaReference

_EXTENSION_NAMESPACE_RE = re.compile(r"^x\.(?:[a-z0-9][a-z0-9-]*\.)+[a-z0-9][a-z0-9-]*$")
_RESERVED_KEYS = {
    "object_id",
    "version_id",
    "schema",
    "object_type",
    "parent_version_ids",
    "record_digest",
    "policy",
    "provenance",
}


class ExtensionRecord(ContractModel):
    namespace: str = Field(pattern=_EXTENSION_NAMESPACE_RE.pattern)
    schema_ref: SchemaReference = Field(alias="schema", serialization_alias="schema")
    critical: bool = False
    value: JsonValue

    @model_validator(mode="after")
    def prevent_core_override(self) -> "ExtensionRecord":
        if isinstance(self.value, Mapping) and _RESERVED_KEYS.intersection(self.value):
            raise ValueError("extension value attempts to override core fields")
        return self


def check_extensions(
    extensions: Iterable[ExtensionRecord], understood_namespaces: set[str] | frozenset[str]
) -> tuple[WarningRecord, ...]:
    warnings: list[WarningRecord] = []
    for extension in extensions:
        if extension.namespace in understood_namespaces:
            continue
        if extension.critical:
            raise ValueError(f"unknown critical extension: {extension.namespace}")
        warnings.append(
            WarningRecord(
                warning_id=new_uuid7(),
                code="COC-W-011",
                name="optional_extension_ignored",
                severity=Severity.INFO,
                scope=extension.namespace,
                message="Consumer retained but did not interpret a non-critical extension.",
            )
        )
    return tuple(warnings)
