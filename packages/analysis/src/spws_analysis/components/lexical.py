"""Lexical analyser: rarity / lexicon coverage annotations."""

from __future__ import annotations

from typing import Any

from spws_contracts_core.domain import Annotation, StructuralScope
from spws_domain.ids import new_id

COMPONENT_ID = "lexical"
COMPONENT_VERSION = "0.1.0"


def analyse_lexical(
    text: str,
    *,
    source_id: str,
    config: Any | None = None,
) -> dict[str, Any]:
    _ = config
    annotations: list[Annotation] = []
    snap: dict[str, Any] = {}
    coverage = 0.0
    confidence = 0.2
    warnings: list[str] = []
    try:
        from spws_wordrare_adapter import lexical_snapshot

        snap = lexical_snapshot(text)
        content = int(snap.get("content_tokens") or 0)
        known = int(snap.get("known_in_lexicon") or 0)
        # Confidence from lexicon coverage, never a constant 0.7.
        coverage = (known / float(content)) if content > 0 else 0.0
        if known == 0:
            confidence = 0.35  # rule-only / empty lexicon prior
        else:
            confidence = max(0.15, min(0.95, 0.25 + 0.7 * coverage))
    except Exception as exc:
        snap = {"error": str(exc)}
        warnings.append(f"lexical: {exc}")
        confidence = 0.2

    annotations.append(
        Annotation(
            annotation_id=new_id("ann"),
            source_object=source_id,
            scope=StructuralScope.WORK,
            feature="lexical_snapshot",
            value=snap,
            confidence=float(confidence),
            analyser=COMPONENT_ID,
            analyser_version=COMPONENT_VERSION,
        )
    )
    annotations.append(
        Annotation(
            annotation_id=new_id("ann"),
            source_object=source_id,
            scope=StructuralScope.WORK,
            feature="lexicon_coverage",
            value=coverage,
            confidence=float(confidence),
            analyser=COMPONENT_ID,
            analyser_version=COMPONENT_VERSION,
        )
    )
    return {
        "annotations": annotations,
        "structural_units": [],
        "component_id": COMPONENT_ID,
        "component_version": COMPONENT_VERSION,
        "field_confidence": {"lexical": float(confidence)},
        "warnings": warnings,
    }
