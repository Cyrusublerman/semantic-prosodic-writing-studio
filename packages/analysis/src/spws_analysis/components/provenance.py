"""Provenance analyser: source identity / digest stubs for the draft."""

from __future__ import annotations

import hashlib
from typing import Any

from spws_contracts_core.domain import Annotation, StructuralScope
from spws_domain.ids import new_id

COMPONENT_ID = "provenance"
COMPONENT_VERSION = "0.1.0"


def analyse_provenance(
    text: str,
    *,
    source_id: str,
    config: Any | None = None,
) -> dict[str, Any]:
    _ = config
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    # Deterministic hash of provided text → high confidence; unknown external provenance → lower.
    confidence = 0.9 if source_id else 0.55
    annotations = [
        Annotation(
            annotation_id=new_id("ann"),
            source_object=source_id,
            scope=StructuralScope.WORK,
            feature="content_sha256",
            value=digest,
            confidence=confidence,
            analyser=COMPONENT_ID,
            analyser_version=COMPONENT_VERSION,
        ),
        Annotation(
            annotation_id=new_id("ann"),
            source_object=source_id,
            scope=StructuralScope.WORK,
            feature="source_object_id",
            value=source_id,
            confidence=confidence,
            analyser=COMPONENT_ID,
            analyser_version=COMPONENT_VERSION,
        ),
    ]
    return {
        "annotations": annotations,
        "structural_units": [],
        "component_id": COMPONENT_ID,
        "component_version": COMPONENT_VERSION,
        "field_confidence": {"provenance": confidence},
        "warnings": [],
    }
