"""Fragment collage generation. Candidates are never auto-accepted."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from spws_contracts_core.domain import AuthorshipClass, MeaningScale, ManuscriptVersion
from spws_domain.ids import new_id


_MIN_ATOM_CHARS = 12


def build_collage_plan(
    theme: str,
    line_count: int = 3,
    work_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive a CollagePlan (slots + filters) from WorkPlan or defaults."""
    motif: list[str] = []
    constraints: list[str] = []
    if work_plan:
        spec = work_plan.get("work_specification") or {}
        motif = list(spec.get("motif_plan") or [])
        wp = work_plan.get("work_plan") or work_plan
        constraints = [c if isinstance(c, str) else str(c) for c in (wp.get("constraints") or [])]
        units = wp.get("structural_units") or []
        if units:
            line_count = max(line_count, len(units))
    slots = [
        {
            "slot_index": index,
            "role": "line",
            "filters": {
                "scales": [MeaningScale.PHRASE.value, MeaningScale.SENTENCE.value],
                "max_chars": 120,
                "min_chars": _MIN_ATOM_CHARS,
                "min_words": 2,
            },
            "motif_hint": motif[index % len(motif)] if motif else theme,
        }
        for index in range(line_count)
    ]
    return {
        "collage_plan_id": new_id("cplan"),
        "theme": theme,
        "line_count": line_count,
        "motif_plan": motif,
        "slots": slots,
        "constraints": constraints,
        "quotation_mode": "transform",
        "max_fragments_per_source": 2,
        "human_gate_required": True,
    }


def _flatten_hits(board: dict[str, Any]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for cluster_hits in board.get("clusters", {}).values():
        hits.extend(cluster_hits)
    hits.sort(key=lambda item: float(item.get("score_combined") or 0.0), reverse=True)
    return hits


def _usable_seed(text: str) -> str | None:
    seed = (text or "").strip().splitlines()[0].strip() if text else ""
    if len(seed) < _MIN_ATOM_CHARS:
        return None
    if len(seed.split()) < 2:
        return None
    return seed


def _theme_fit_score(poem_text: str, motif_plan: list[str], theme: str, config: Any) -> dict[str, Any]:
    """Centroid cosine of collage text vs motif/theme query. Measured when encoder available."""
    query = " ".join(motif_plan) if motif_plan else theme
    try:
        from spws_semantics import MeaningGauge

        gauge = MeaningGauge.from_config(config)
        q_vec = list(gauge.embedder.encode(query))
        t_vec = list(gauge.embedder.encode(poem_text or theme))
        dot = sum(a * b for a, b in zip(q_vec, t_vec))
        nq = sum(a * a for a in q_vec) ** 0.5
        nt = sum(b * b for b in t_vec) ** 0.5
        score = float(dot / ((nq * nt) or 1.0))
        return {"theme_fit": score, "theme_fit_label": "measured", "theme_query": query}
    except Exception:
        # Lexical fallback — still labelled inferred
        tokens = set(query.lower().split())
        body = set((poem_text or "").lower().split())
        overlap = len(tokens & body) / max(len(tokens), 1)
        return {"theme_fit": overlap, "theme_fit_label": "inferred", "theme_query": query}


def _optional_prosody_ok(seed: str, slot: dict[str, Any]) -> tuple[bool, str | None]:
    """Optional WordRare prosody filter from slot filters (syllable band / rhyme)."""
    filters = slot.get("filters") or {}
    syl_min = filters.get("min_syllables")
    syl_max = filters.get("max_syllables")
    rhyme_key = filters.get("rhyme_key")
    if syl_min is None and syl_max is None and not rhyme_key:
        return True, None
    try:
        from spws_wordrare_adapter import is_unsupported, syllable_stress_rhyme

        tokens = [t.strip(".,;:!?\"'").lower() for t in seed.split() if t.strip()]
        if not tokens:
            return False, "empty_tokens"
        total = 0
        for token in tokens:
            result = syllable_stress_rhyme(token)
            if is_unsupported(result):
                continue
            total += int(result.get("syllable_count") or 0)
            if rhyme_key and rhyme_key in (result.get("rhyme_keys") or []):
                rhyme_key = None  # satisfied
        if syl_min is not None and total < int(syl_min):
            return False, f"syllables<{syl_min}"
        if syl_max is not None and total > int(syl_max):
            return False, f"syllables>{syl_max}"
        if rhyme_key:
            return False, "rhyme_key_miss"
        return True, None
    except Exception:
        return True, None  # optional filter — degrade open


def _build_collage_evaluation(
    poem_text: str,
    theme: str,
    motif_plan: list[str],
    lines: list[dict[str, Any]],
    line_count: int,
    work_plan: dict[str, Any] | None,
    config: Any,
) -> dict[str, Any]:
    """Prefer Phase-4 EvaluationBundle; fall back to theme_fit + slot_fill."""
    theme_eval = _theme_fit_score(poem_text, motif_plan, theme, config)
    base_results = [
        {
            "criterion": "theme_fit",
            "measured_value": theme_eval["theme_fit"],
            "inferred_label": theme_eval["theme_fit_label"],
        },
        {
            "criterion": "slot_fill",
            "measured_value": len(lines) / max(line_count, 1),
            "inferred_label": "measured",
        },
    ]
    try:
        from spws_revision.evaluation import ALL_CRITERIA, build_evaluation_bundle

        bundle, _improve, _degrade = build_evaluation_bundle(
            theme,
            poem_text or theme,
            work_plan=work_plan,
            config=config,
            grounding_refs=[ln.get("source_unit_id") for ln in lines if ln.get("source_unit_id")],
            subject_id="collage",
        )
        results = [r.model_dump(mode="json") for r in bundle.results]
        # Keep theme_fit / slot_fill visible alongside D007 criteria.
        present = {r.get("criterion") for r in results}
        for item in base_results:
            if item["criterion"] not in present:
                results.append(item)
        return {
            "bundle_id": bundle.bundle_id,
            "results": results,
            "criteria": list(ALL_CRITERIA) + ["theme_fit", "slot_fill"],
        }
    except Exception:
        return {"results": base_results, "criteria": ["theme_fit", "slot_fill"]}


def generate_collage(
    theme: str,
    line_count: int = 3,
    config: Any | None = None,
    *,
    work_plan: dict[str, Any] | None = None,
    generation_spec: Any | None = None,
) -> dict[str, Any]:
    """Assemble a proposed fragment collage with constraint traces. Never auto-accepts."""
    if line_count < 1:
        raise ValueError("line_count must be >= 1")

    from spws_orchestration.llm_socket import assert_method_family_allowed

    method_family = None
    if isinstance(generation_spec, dict):
        method_family = generation_spec.get("method_family")
    elif generation_spec is not None:
        method_family = getattr(generation_spec, "method_family", None)
    assert_method_family_allowed(method_family)

    if config is None:
        from spws_storage import load_config

        config = load_config()

    collage_plan = build_collage_plan(theme, line_count=line_count, work_plan=work_plan)
    line_count = int(collage_plan["line_count"])
    max_per_source = int(collage_plan["max_fragments_per_source"])

    from spws_planning import build_source_board

    board = build_source_board(theme, config, allow_empty_fail=True, result_limit=max(20, line_count * 4))
    hits = [
        h
        for h in _flatten_hits(board)
        if h.get("scale") in {MeaningScale.PHRASE.value, MeaningScale.SENTENCE.value, "phrase", "sentence"}
        or h.get("scale") is None
    ]

    lines: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    constraint_trace: list[str] = []
    seen_objects: dict[str, int] = {}

    for hit in hits:
        if len(lines) >= line_count:
            break
        seed = _usable_seed(str(hit.get("text") or ""))
        if not seed:
            constraint_trace.append(f"reject:{hit.get('unit_id')}:atom_too_short")
            continue
        if len(seed) > 120:
            constraint_trace.append(f"reject:{hit.get('unit_id')}:atom_too_long")
            continue
        oid = str(hit.get("object_uid") or "")
        if oid and seen_objects.get(oid, 0) >= max_per_source:
            constraint_trace.append(f"reject:{hit.get('unit_id')}:diversity_cap")
            continue
        slot = collage_plan["slots"][len(lines)]
        prosody_ok, prosody_reason = _optional_prosody_ok(seed, slot)
        if not prosody_ok:
            constraint_trace.append(f"reject:{hit.get('unit_id')}:prosody:{prosody_reason}")
            continue
        span = hit.get("span")
        if span is None:
            # R2: every accepted line must carry a TextSpan; synthesise from seed when absent.
            span = {"start_char": 0, "end_char": len(seed), "quote": seed}
        elif isinstance(span, dict):
            span = {
                "start_char": int(span.get("start_char") or 0),
                "end_char": int(span.get("end_char") if span.get("end_char") is not None else len(seed)),
                "quote": span.get("quote") or seed,
                **{
                    k: v
                    for k, v in span.items()
                    if k not in {"start_char", "end_char", "quote"}
                },
            }
        entry = {
            "text": seed,
            "source_unit_id": hit.get("unit_id"),
            "object_uid": hit.get("object_uid"),
            "authorship": AuthorshipClass.EXTRACTED.value,
            "span": span,
            "slot_index": slot["slot_index"],
        }
        lines.append(entry)
        if oid:
            seen_objects[oid] = seen_objects.get(oid, 0) + 1
        provenance.append(
            {
                "line_index": len(lines) - 1,
                "source_unit_id": hit.get("unit_id"),
                "object_uid": hit.get("object_uid"),
                "score_combined": hit.get("score_combined"),
                "method": "similarity_hit",
                "span": span,
            }
        )
        constraint_trace.append(
            f"accept:{hit.get('unit_id')}:slot={len(lines) - 1}:"
            f"motif={slot.get('motif_hint')!r}:score={hit.get('score_combined')}"
        )

    underfilled = len(lines) < line_count
    if underfilled:
        constraint_trace.append(f"hard_fail:underfilled:{len(lines)}<{line_count}")

    poem_text = "\n".join(item["text"] for item in lines)
    evaluation = _build_collage_evaluation(
        poem_text,
        theme,
        list(collage_plan.get("motif_plan") or []),
        lines,
        line_count,
        work_plan,
        config,
    )
    theme_row = next((r for r in evaluation["results"] if r.get("criterion") == "theme_fit"), None)
    if theme_row and float(theme_row.get("measured_value") or 0) < 0.05 and poem_text.strip():
        constraint_trace.append(f"warn:theme_fit_low:{theme_row['measured_value']:.4f}")

    return {
        "collage_id": new_id("collage"),
        "collage_plan": collage_plan,
        "theme": theme,
        "text": poem_text,
        "lines": lines,
        "provenance": provenance,
        "constraint_trace": constraint_trace,
        "motif_plan": collage_plan.get("motif_plan") or [],
        "evaluation": evaluation,
        "method_family": "fragment_collage",
        "status": "proposed" if not underfilled else "failed_constraints",
        "auto_accepted": False,
        "human_gate_required": True,
        "warnings": list(board.get("warnings") or [])
        + (["underfilled_slots"] if underfilled else []),
    }


def accept_collage(
    collage: dict[str, Any],
    *,
    config: Any,
    decided_by: str = "human",
    rationale: str | None = None,
) -> dict[str, Any]:
    """Human gate: promote a proposed collage to a root ManuscriptVersion. Never silent."""
    if collage.get("status") == "failed_constraints":
        raise RuntimeError("cannot accept collage that failed hard constraints")
    if collage.get("auto_accepted"):
        raise RuntimeError("collage already marked auto_accepted — refuse silent path")
    text = str(collage.get("text") or "").strip()
    if not text:
        raise RuntimeError("empty collage cannot be accepted")

    from datetime import UTC, datetime

    from spws_storage.manuscripts import list_versions, save_manuscript

    # Root collage version: empty parents, no accepted_change_ids (child-rule).
    ms = ManuscriptVersion(
        manuscript_id=new_id("ms"),
        version_id=new_id("msv"),
        text=text,
        parent_version_ids=[],
        created_at=datetime.now(UTC),
        provenance_map={
            "collage_id": collage.get("collage_id"),
            "lines": collage.get("provenance") or [],
            "decided_by": decided_by,
            "rationale": rationale,
            "accepted_collage_id": collage.get("collage_id"),
        },
        accepted_change_ids=[],
    )
    path = save_manuscript(config, ms)
    listed = list_versions(config, ms.manuscript_id)
    db_versions = [v.model_dump(mode="json") for v in listed]
    return {
        "status": "accepted",
        "decision_kind": "accept",
        "manuscript": ms.model_dump(mode="json"),
        "manuscript_path": str(path),
        "manuscript_db_versions": db_versions,
        "collage_id": collage.get("collage_id"),
    }
