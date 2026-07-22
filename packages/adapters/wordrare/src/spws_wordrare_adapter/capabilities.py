"""WordRare capability protocols (D015).

Each method returns a result dict / LexicalRecord payload OR an explicit
``{"status": "unsupported", "capability": ...}`` — never silent None-as-success.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


def unsupported(capability: str, *, reason: str | None = None, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": "unsupported", "capability": capability}
    if reason:
        payload["reason"] = reason
    payload.update(extra)
    return payload


def is_unsupported(result: Any) -> bool:
    return isinstance(result, dict) and result.get("status") == "unsupported"


@runtime_checkable
class LexicalCapability(Protocol):
    def lexical_record(self, lemma: str, *, dialect: str = "en-AU") -> dict[str, Any]: ...

    def rarity(self, lemma: str) -> dict[str, Any]: ...


@runtime_checkable
class ProsodyCapability(Protocol):
    def pronunciation(self, lemma: str, *, dialect: str = "en-AU") -> dict[str, Any]: ...

    def syllable_stress_rhyme(self, lemma: str) -> dict[str, Any]: ...


@runtime_checkable
class FormScaffoldCapability(Protocol):
    def form_scaffold(self, form_id: str) -> dict[str, Any]: ...

    def list_forms(self) -> dict[str, Any]: ...


@runtime_checkable
class ConstrainedSearchCapability(Protocol):
    def constrained_search(
        self,
        *,
        lemma: str | None = None,
        rhyme_key: str | None = None,
        syllable_count: int | None = None,
        min_rarity: float | None = None,
        max_rarity: float | None = None,
        limit: int = 5,
    ) -> dict[str, Any]: ...


@runtime_checkable
class ProsodicRepairCapability(Protocol):
    def diagnose_line(self, line: str, target_spec: dict[str, Any] | None = None) -> dict[str, Any]: ...

    def repair_line(self, line: str, target_spec: dict[str, Any] | None = None) -> dict[str, Any]: ...


class DisabledCapability:
    """Null object: every call returns explicit unsupported (replaceability proof)."""

    def __init__(self, capability: str, reason: str = "disabled") -> None:
        self.capability = capability
        self.reason = reason

    def __getattr__(self, name: str):
        def _call(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            return unsupported(self.capability, reason=self.reason, method=name)

        return _call
