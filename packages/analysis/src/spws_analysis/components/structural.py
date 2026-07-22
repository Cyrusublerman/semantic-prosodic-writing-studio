"""Structural analyser: work / line StructuralUnit tree."""

from __future__ import annotations

from typing import Any

from spws_contracts_core.domain import (
    Annotation,
    StructuralScope,
    StructuralUnit,
    TextSpan,
)
from spws_domain.ids import new_id

COMPONENT_ID = "structural"
COMPONENT_VERSION = "0.1.0"


def _structural_units(text: str, source_id: str) -> list[StructuralUnit]:
    units: list[StructuralUnit] = []
    work_id = new_id("su")
    units.append(
        StructuralUnit(
            unit_id=work_id,
            scope=StructuralScope.WORK,
            text=text,
            source_object_id=source_id,
            ordinal=0,
        )
    )
    lines = text.splitlines() or [text]
    child_ids: list[str] = []
    cursor = 0
    for index, line in enumerate(lines):
        start = text.find(line, cursor)
        if start < 0:
            start = cursor
        end = start + len(line)
        cursor = end + 1
        uid = new_id("su")
        child_ids.append(uid)
        units.append(
            StructuralUnit(
                unit_id=uid,
                scope=StructuralScope.LINE if "\n" in text else StructuralScope.SENTENCE,
                text=line,
                span=TextSpan(start_char=start, end_char=end, quote=line),
                parent_id=work_id,
                source_object_id=source_id,
                ordinal=index,
            )
        )
    units[0] = units[0].model_copy(update={"child_ids": child_ids})
    return units


def analyse_structural(
    text: str,
    *,
    source_id: str,
    config: Any | None = None,
) -> dict[str, Any]:
    _ = config
    units = _structural_units(text, source_id)
    line_count = max(0, len(units) - 1)
    # Deterministic structure → high rule confidence (not 0.7).
    confidence = 0.95 if text.strip() else 0.3
    annotations = [
        Annotation(
            annotation_id=new_id("ann"),
            source_object=source_id,
            scope=StructuralScope.WORK,
            feature="line_count",
            value=line_count,
            confidence=confidence,
            analyser=COMPONENT_ID,
            analyser_version=COMPONENT_VERSION,
        )
    ]
    return {
        "annotations": annotations,
        "structural_units": units,
        "component_id": COMPONENT_ID,
        "component_version": COMPONENT_VERSION,
        "field_confidence": {"structural": confidence},
        "warnings": [],
    }
