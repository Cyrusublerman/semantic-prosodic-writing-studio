"""Component manifests and runtime registry."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field


class ComponentManifest(BaseModel):
    component_id: str
    component_version: str
    functional_category: str
    capabilities: list[str] = Field(default_factory=list)
    accepted_contracts: list[str] = Field(default_factory=list)
    produced_contracts: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=lambda: ["en"])
    dialects: list[str] = Field(default_factory=list)
    determinism: str = "deterministic"
    dependencies: list[str] = Field(default_factory=list)
    data_and_model_versions: dict[str, str] = Field(default_factory=dict)
    rights_and_privacy_behaviour: str = "fail_closed"
    resource_limits: dict[str, Any] = Field(default_factory=dict)
    failure_modes: list[str] = Field(default_factory=list)


ComponentHandler = Callable[..., dict[str, Any]]


class ComponentRegistry:
    """In-memory registry of component manifests and handlers."""

    def __init__(self) -> None:
        self._entries: dict[str, tuple[ComponentManifest, ComponentHandler]] = {}

    def register(self, manifest: ComponentManifest, handler: ComponentHandler) -> None:
        if not callable(handler):
            raise TypeError("handler must be callable")
        self._entries[manifest.component_id] = (manifest, handler)

    def get(self, component_id: str) -> tuple[ComponentManifest, ComponentHandler]:
        try:
            return self._entries[component_id]
        except KeyError as exc:
            raise KeyError(f"unknown component_id: {component_id}") from exc

    def list_by_capability(self, cap: str) -> list[ComponentManifest]:
        return [
            manifest
            for manifest, _ in self._entries.values()
            if cap in manifest.capabilities
        ]

    def __contains__(self, component_id: str) -> bool:
        return component_id in self._entries

    def __len__(self) -> int:
        return len(self._entries)
