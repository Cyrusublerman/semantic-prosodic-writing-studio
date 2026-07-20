from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any

_REGISTRY_PARTS = (
    "meta.json", "provenance.json", "rights.json", "states.json",
    "codes.json", "text_repro.json",
)


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    directory = files("spws_contracts_core").joinpath("data/registry")
    registry: dict[str, Any] = {}
    for name in _REGISTRY_PARTS:
        part = json.loads(directory.joinpath(name).read_text(encoding="utf-8"))
        overlap = registry.keys() & part.keys()
        if overlap:
            raise ValueError(f"duplicate registry section(s): {sorted(overlap)}")
        registry.update(part)
    return registry


def values_for(path: str) -> frozenset[str]:
    node: Any = load_registry()
    for part in path.split("."):
        node = node[part]
    if not isinstance(node, list):
        raise TypeError(f"registry path {path!r} is not a list")
    if node and isinstance(node[0], dict):
        raise TypeError(f"registry path {path!r} contains records, not strings")
    return frozenset(node)


def validate_registered(value: str, path: str) -> str:
    if value not in values_for(path):
        raise ValueError(f"{value!r} is not registered under {path}")
    return value


def warning_definition(code: str) -> dict[str, Any]:
    for item in load_registry()["warning_codes"]:
        if item["code"] == code:
            return item
    raise ValueError(f"unregistered warning code {code!r}")


def failure_definition(code: str) -> dict[str, Any]:
    for item in load_registry()["failure_codes"]:
        if item["code"] == code:
            return item
    raise ValueError(f"unregistered failure code {code!r}")
