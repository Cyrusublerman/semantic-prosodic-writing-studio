"""Semantic analyser: theme / affect tags via MeaningGauge."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from spws_contracts_core.domain import Annotation, StructuralScope
from spws_domain.ids import new_id

COMPONENT_ID = "semantic"
COMPONENT_VERSION = "0.1.0"


def _build_meaning_gauge(config: Any | None):
    from spws_semantics import MeaningGauge

    if config is not None:
        return MeaningGauge.from_config(config)
    return MeaningGauge(
        Path(tempfile.gettempdir()) / "spws-meaning-analyse",
        debug_hash_embeddings=True,
        require_model=False,
    )


def analyse_semantic(
    text: str,
    *,
    source_id: str,
    config: Any | None = None,
) -> dict[str, Any]:
    annotations: list[Annotation] = []
    warnings: list[str] = []
    confidence = 0.0
    try:
        gauge = _build_meaning_gauge(config)
        profile = gauge.profile_text(text)
        # Model vs hash-embedding: derive from profile.confidence, never 0.7 constant.
        confidence = float(profile.confidence)
        if getattr(gauge, "debug_hash_embeddings", False) or getattr(
            getattr(gauge, "embedder", None), "debug_hash_embeddings", False
        ):
            # Hash embeddings → lower ceiling than real model
            confidence = min(confidence, 0.65) if confidence > 0 else 0.4
        annotations.append(
            Annotation(
                annotation_id=new_id("ann"),
                source_object=source_id,
                scope=StructuralScope.WORK,
                feature="theme_tags",
                value=profile.theme_tags,
                confidence=confidence,
                analyser=COMPONENT_ID,
                analyser_version=COMPONENT_VERSION,
            )
        )
        annotations.append(
            Annotation(
                annotation_id=new_id("ann"),
                source_object=source_id,
                scope=StructuralScope.WORK,
                feature="affect_tags",
                value=profile.affect_tags,
                confidence=confidence,
                analyser=COMPONENT_ID,
                analyser_version=COMPONENT_VERSION,
            )
        )
    except Exception as exc:
        warnings.append(f"semantic: {exc}")
        annotations.append(
            Annotation(
                annotation_id=new_id("ann"),
                source_object=source_id,
                feature="semantic_error",
                value=str(exc),
                confidence=0.0,
                analyser=COMPONENT_ID,
                analyser_version=COMPONENT_VERSION,
            )
        )
        confidence = 0.0

    return {
        "annotations": annotations,
        "structural_units": [],
        "component_id": COMPONENT_ID,
        "component_version": COMPONENT_VERSION,
        "field_confidence": {"semantic": confidence},
        "warnings": warnings,
    }
