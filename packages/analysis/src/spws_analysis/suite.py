"""Full analysis suite: fan-out across six components."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from spws_contracts_core.domain import AnalysisBundle, Annotation, StructuralUnit
from spws_domain.ids import new_id

from .components import COMPONENT_ANALYSERS
from .diagnosis import diagnose_poem


def _collect_disagreement_warnings(annotations: list[Annotation]) -> list[str]:
    """Preserve analyser disagreements as warnings (same feature, differing values)."""
    by_feature: dict[str, list[Annotation]] = {}
    for ann in annotations:
        by_feature.setdefault(ann.feature, []).append(ann)
    warnings: list[str] = []
    for feature, group in by_feature.items():
        if len(group) < 2:
            continue
        values = []
        for ann in group:
            try:
                values.append(repr(ann.value))
            except Exception:
                values.append(str(type(ann.value)))
        if len(set(values)) > 1:
            analysers = ", ".join(sorted({a.analyser for a in group}))
            warnings.append(
                f"disagreement on {feature} across [{analysers}]: {len(set(values))} distinct values"
            )
    return warnings


def analyse_document(
    text: str,
    *,
    kind: str = "poem",
    source_id: str | None = None,
    config: Any | None = None,
) -> dict:
    """Run analysis suite; fan out all six components into one AnalysisBundle."""
    source_id = source_id or f"src-{uuid4().hex[:12]}"
    annotations: list[Annotation] = []
    structural: list[StructuralUnit] = []
    component_versions: dict[str, str] = {"spws_analysis": "0.1.0"}
    field_confidence: dict[str, float | None] = {}
    warnings: list[str] = []
    poetry = None

    for name, analyser in COMPONENT_ANALYSERS.items():
        try:
            result = analyser(text, source_id=source_id, config=config)
        except Exception as exc:
            warnings.append(f"{name}: failed ({exc})")
            component_versions[name] = "error"
            continue
        component_versions[result.get("component_id", name)] = result.get(
            "component_version", "0.1.0"
        )
        for ann in result.get("annotations") or []:
            annotations.append(ann)
        for unit in result.get("structural_units") or []:
            structural.append(unit)
        for key, value in (result.get("field_confidence") or {}).items():
            field_confidence[key] = value
        warnings.extend(result.get("warnings") or [])
        if name == "prosodic" and result.get("poetry") is not None:
            poetry = result["poetry"]

    warnings.extend(_collect_disagreement_warnings(annotations))

    diagnosis = None
    if kind == "poem":
        if poetry is None:
            from .poetry import analyze_poem

            poetry = analyze_poem(text)
        if poetry.lines:
            diagnosis = diagnose_poem(text, poetry, annotations)

    bundle = AnalysisBundle(
        bundle_id=new_id("ab"),
        source_object_id=source_id,
        annotations=annotations,
        structural_units=structural,
        created_at=datetime.now(UTC),
        component_versions=component_versions,
        warnings=warnings,
    )
    return {
        "kind": kind,
        "bundle": bundle.model_dump(mode="json"),
        "poetry": poetry.model_dump(mode="json") if poetry else None,
        "diagnosis": diagnosis.model_dump(mode="json") if diagnosis else None,
        "field_confidence": field_confidence,
    }
