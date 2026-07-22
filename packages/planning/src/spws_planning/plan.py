"""Create serialisable WorkSpecification + WorkPlan from a brief."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from spws_contracts_core.domain import (
    StructuralScope,
    StructuralUnit,
    StudioConstraint,
    WorkPlan,
    WorkSpecification,
)
from spws_domain.ids import new_id

_WORD_RE = re.compile(r"[A-Za-z']+")
_POETRY_FORMS = {"haiku", "sonnet", "tanka", "limerick", "villanelle", "blank_verse", "free_verse"}


def _motif_plan(brief: str) -> list[str]:
    words = [m.group(0).lower() for m in _WORD_RE.finditer(brief)]
    stop = {"a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with"}
    motifs: list[str] = []
    seen: set[str] = set()
    for word in words:
        if word in stop or len(word) < 3 or word in seen:
            continue
        seen.add(word)
        motifs.append(word)
        if len(motifs) >= 8:
            break
    return motifs or (["theme"] if not brief.strip() else [brief.strip()[:40]])


def _line_count(form: str) -> int:
    normalised = form.strip().lower()
    if normalised == "haiku":
        return 3
    if normalised == "sonnet":
        return 14
    return 4


def _as_diagnosis_dict(diagnosis: Any | None) -> dict[str, Any] | None:
    if diagnosis is None:
        return None
    if hasattr(diagnosis, "model_dump"):
        return diagnosis.model_dump(mode="json")
    if isinstance(diagnosis, dict):
        return diagnosis
    return None


def create_work_plan(
    brief: str,
    form: str = "haiku",
    diagnosis: Any | None = None,
) -> dict[str, Any]:
    """Return serialisable WorkSpecification and WorkPlan for ``form``.

    When ``diagnosis`` is provided, attach its suggested_brief and measured constraints.
    """
    form_key = form.strip().lower() or "haiku"
    line_count = _line_count(form_key)
    diag = _as_diagnosis_dict(diagnosis)
    effective_brief = brief.strip()
    if diag and diag.get("suggested_brief"):
        effective_brief = str(diag["suggested_brief"])
    motifs = _motif_plan(effective_brief or brief)
    spec_id = new_id("wspec")
    plan_id = new_id("wplan")

    constraints_meta = ["semantic_retention:soft"]
    if form_key in _POETRY_FORMS:
        constraints_meta.append("meter:soft")
    if diag:
        constraints_meta.append(f"diagnosis:{diag.get('problem_type', 'diction')}")
        constraints_meta.append("length_bound:soft")

    spec = WorkSpecification(
        spec_id=spec_id,
        mode="poetry_generation" if not diag else "poetry_revision",
        purpose=effective_brief or None,
        subject=(brief.strip() or None),
        form=form_key,
        motif_plan=motifs,
        constraints=constraints_meta,
        machine_assistance_policy={"auto_accept": False},
    )

    structural_units: list[StructuralUnit] = []
    for index in range(line_count):
        structural_units.append(
            StructuralUnit(
                unit_id=new_id("sunit"),
                scope=StructuralScope.LINE,
                text=None,
                ordinal=index,
            )
        )

    plan_constraints = [
        StudioConstraint(
            constraint_id=new_id("cstr"),
            target_scope="work",
            constraint_type="semantic_retention",
            hard=False,
            measurement_method="embedding_cosine",
            weight=1.0,
            evidence=[effective_brief] if effective_brief else [],
        )
    ]
    if form_key in _POETRY_FORMS:
        plan_constraints.append(
            StudioConstraint(
                constraint_id=new_id("cstr"),
                target_scope="line",
                constraint_type="meter",
                hard=False,
                measurement_method="syllable_delta",
                weight=0.8,
            )
        )
    if diag:
        plan_constraints.append(
            StudioConstraint(
                constraint_id=new_id("cstr"),
                target_scope="line",
                constraint_type="length_bound",
                hard=True,
                measurement_method="char_ratio_1_3",
                tolerance=1.3,
                weight=1.0,
                evidence=[f"target_line_index={diag.get('target_line_index')}"],
            )
        )

    plan = WorkPlan(
        plan_id=plan_id,
        work_spec_id=spec_id,
        structural_units=structural_units,
        constraints=plan_constraints,
        unresolved_decisions=["human_review_required", "plan_confirm_required"],
    )
    return {
        "work_specification": spec.model_dump(mode="json"),
        "work_plan": plan.model_dump(mode="json"),
        "brief": effective_brief,
        "diagnosis": diag,
        "confirmed": False,
        "confirmed_at": None,
    }


def confirm_work_plan(plan: dict[str, Any], *, confirmed: bool) -> dict[str, Any]:
    """Mark plan confirmed (ISO UTC). Refuse revise paths without confirmed=true."""
    out = dict(plan)
    if not confirmed:
        out["confirmed"] = False
        out["confirmed_at"] = None
        unresolved = list(out.get("work_plan", {}).get("unresolved_decisions") or [])
        if "plan_confirm_required" not in unresolved:
            unresolved.append("plan_confirm_required")
        if "work_plan" in out and isinstance(out["work_plan"], dict):
            out["work_plan"] = dict(out["work_plan"])
            out["work_plan"]["unresolved_decisions"] = unresolved
        return out
    out["confirmed"] = True
    out["confirmed_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    if "work_plan" in out and isinstance(out["work_plan"], dict):
        wp = dict(out["work_plan"])
        unresolved = [u for u in (wp.get("unresolved_decisions") or []) if u != "plan_confirm_required"]
        wp["unresolved_decisions"] = unresolved
        out["work_plan"] = wp
    return out


def save_plan(plan: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def load_plan(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
