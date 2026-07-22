"""Meaning-aware poetry revision and assist reword (span-bounded)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from spws_analysis import analyze_poem, diagnose_poem
from spws_contracts_core.domain import (
    Candidate,
    CandidateSet,
    CandidateStatus,
    EvaluationBundle,
    EvaluationResult,
    ManuscriptVersion,
    MeaningScale,
    RevisionOperation,
    RightsState,
    SimilarityQuery,
    TextSpan,
    normalize_rights_ingest,
    rights_allows_retrieval,
)
from spws_domain.ids import new_id

from .candidates import generate_candidates
from .evaluation import ALL_CRITERIA, build_evaluation_bundle


class RestrictedSourceError(RuntimeError):
    """Raised when a candidate quotes a source that fails rights retrieval policy."""


def _hit_rights(hit: dict[str, Any], config: Any) -> RightsState | None:
    """Resolve rights from hit payload or MeaningStore lookup."""
    raw = hit.get("rights")
    if raw is not None:
        return normalize_rights_ingest(raw)
    unit_id = hit.get("unit_id")
    if not unit_id or config is None:
        return None
    try:
        from spws_semantics import MeaningGauge

        gauge = MeaningGauge.from_config(config)
        unit = gauge.store.get_unit(str(unit_id))
        if unit is not None:
            return unit.rights
    except Exception:
        return None
    return None


def filter_restricted_source_hits(
    hits: list[dict[str, Any]],
    config: Any,
    *,
    raise_on_restricted: bool = False,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Drop hits whose provenance rights refuse retrieval; optionally raise."""
    kept: list[dict[str, Any]] = []
    warnings: list[str] = []
    for hit in hits:
        rights = _hit_rights(hit, config)
        if rights is not None and not rights_allows_retrieval(rights):
            msg = (
                f"refuse restricted source unit_id={hit.get('unit_id')} "
                f"rights={rights.value}"
            )
            warnings.append(msg)
            if raise_on_restricted:
                raise RestrictedSourceError(msg)
            continue
        kept.append(hit)
    return kept, warnings


def _meaning_neighbours(
    text: str,
    config: Any,
    limit: int = 5,
    max_chars: float | int | None = None,
) -> list[dict]:
    """Retrieve phrase/sentence neighbours. No demo seed; empty index → []."""
    if config is None:
        return []
    try:
        from spws_semantics import MeaningGauge

        gauge = MeaningGauge.from_config(config)
        if gauge.count() == 0:
            return []
        bound = int(max_chars) if max_chars is not None else max(40, int(1.3 * max(len(text), 1)))
        result = gauge.similar(
            SimilarityQuery(
                text=text,
                result_limit=max(limit * 3, limit),
                target_scales=[MeaningScale.PHRASE, MeaningScale.SENTENCE],
            )
        )
        hits: list[dict] = []
        for hit in result.hits:
            hit_text = (hit.text or "").strip()
            scale = hit.scale.value if hasattr(hit.scale, "value") else str(hit.scale)
            if scale not in {"phrase", "sentence"}:
                continue
            if "\n" in hit_text:
                continue
            if len(hit_text) > bound:
                continue
            hits.append(hit.model_dump(mode="json"))
            if len(hits) >= limit:
                break
        return hits
    except Exception:
        return []


def _rare_substitutions(line: str) -> list[tuple[str, str]]:
    """Method family A: rare-word / lexical substitutes via WordRare or fallback map."""
    try:
        from spws_wordrare_adapter import rare_reword_line

        revised = rare_reword_line(line)
        if revised and revised != line and "\n" not in revised:
            return [(line, revised)]
    except Exception:
        pass
    fallback = {
        "bright": "luminous",
        "dark": "umbrous",
        "quiet": "hushed",
        "river": "rivulet",
        "light": "radiance",
        "night": "gloaming",
        "wind": "zephyr",
        "heart": "spirit",
        "gold": "aureate",
        "grass": "sward",
        "earth": "terrain",
        "stories": "chronicles",
        "meadow": "lea",
        "blade": "shaft",
        "path": "track",
        "rain": "deluge",
        "willows": "osiers",
        "silver": "argent",
        "dusk": "gloaming",
        "leaves": "foliage",
        "soft": "mellifluous",
        "field": "lea",
        "hill": "knoll",
        "song": "canticle",
        "hour": "vigil",
        "cadence": "metre",
        "distant": "farthermost",
        "pastoral": "bucolic",
        "luminous": "effulgent",
        "rivulet": "rill",
    }
    words = line.split()
    out: list[tuple[str, str]] = []
    for i, word in enumerate(words):
        key = word.lower().strip(".,;:!?")
        if key in fallback:
            new_words = words.copy()
            punct = word[len(key) :] if len(word) > len(key) else ""
            new_words[i] = fallback[key] + punct
            revised = " ".join(new_words)
            if revised != line:
                out.append((line, revised))
            break
    if not out and words:
        # Deterministic last-resort rare_lexical family member (never silent empty).
        for i, word in enumerate(words):
            key = word.lower().strip(".,;:!?")
            if len(key) < 4 or key in {"along", "with", "that", "this", "from", "into", "over"}:
                continue
            new_words = words.copy()
            punct = word[len(key) :] if len(word) > len(key) else ""
            new_words[i] = ("aureate" if key != "aureate" else "umbrageous") + punct
            revised = " ".join(new_words)
            if revised != line:
                out.append((line, revised))
            break
    return out


def _cosine_retention(orig: str, revised: str, config: Any) -> tuple[float | None, str]:
    if config is None:
        return None, "inferred"
    try:
        from spws_semantics import MeaningGauge
        from spws_semantics.similarity import cosine

        gauge = MeaningGauge.from_config(config)
        a = gauge.embedder.encode(orig)
        b = gauge.embedder.encode(revised)
        return float(cosine(a, b)), "measured"
    except Exception:
        return None, "inferred"


def _syllable_delta(orig_line: str, revised_line: str) -> tuple[float, str]:
    try:
        orig_a = analyze_poem(orig_line)
        rev_a = analyze_poem(revised_line)
        o = orig_a.lines[0].syllable_count if orig_a.lines else len(orig_line.split())
        r = rev_a.lines[0].syllable_count if rev_a.lines else len(revised_line.split())
        return float(abs(r - o)), "measured"
    except Exception:
        return float(abs(len(revised_line.split()) - len(orig_line.split()))), "inferred"


def _rarity_delta(orig_line: str, revised_line: str) -> tuple[float, str]:
    try:
        from spws_wordrare_adapter import lexical_snapshot

        o = lexical_snapshot(orig_line)
        r = lexical_snapshot(revised_line)
        o_ratio = float(o.get("rare_hits", 0)) / max(float(o.get("content_tokens", 0)), 1.0)
        r_ratio = float(r.get("rare_hits", 0)) / max(float(r.get("content_tokens", 0)), 1.0)
        # Fallback signal when lexicon empty: unique/long-token density
        if o.get("known_in_lexicon", 0) == 0 and r.get("known_in_lexicon", 0) == 0:
            def density(text: str) -> float:
                toks = [t for t in text.split() if t.strip()]
                if not toks:
                    return 0.0
                longish = sum(1 for t in toks if len(t.strip(".,;:!?\"'")) >= 7)
                return longish / float(len(toks))

            return float(density(revised_line) - density(orig_line)), "inferred"
        return float(r_ratio - o_ratio), "measured"
    except Exception:
        return 0.0, "inferred"


def _line_span(text: str, line_index: int) -> TextSpan | None:
    lines = text.splitlines()
    if line_index < 0 or line_index >= len(lines):
        return None
    cursor = 0
    for index, line in enumerate(lines):
        start = text.find(line, cursor)
        if start < 0:
            start = cursor
        end = start + len(line)
        if index == line_index:
            return TextSpan(start_char=start, end_char=end, quote=line)
        cursor = end + 1
    return None


def _merge_line(text: str, line_index: int, new_line: str) -> str:
    lines = text.splitlines()
    if not lines:
        return new_line
    if line_index < 0 or line_index >= len(lines):
        raise IndexError(f"line_index {line_index} out of range for {len(lines)} lines")
    if "\n" in new_line:
        new_line = new_line.splitlines()[0]
    lines[line_index] = new_line
    return "\n".join(lines)


def _method_family_from_spec(generation_spec: Any | None) -> str | None:
    if generation_spec is None:
        return None
    if isinstance(generation_spec, dict):
        return generation_spec.get("method_family")
    return getattr(generation_spec, "method_family", None)


def revise_poetry(
    target: Path,
    *,
    brief: str = "improve diction",
    config: Any = None,
    diagnosis: Any | None = None,
    work_plan: dict | None = None,
    generation_spec: Any | None = None,
) -> dict:
    if work_plan is not None and not work_plan.get("confirmed"):
        raise RuntimeError("work plan not confirmed")

    from spws_orchestration.llm_socket import assert_method_family_allowed

    assert_method_family_allowed(_method_family_from_spec(generation_spec))

    text = Path(target).read_text(encoding="utf-8")
    analysis = analyze_poem(text)
    if diagnosis is None:
        diagnosis = diagnose_poem(text, analysis, annotations=None)
    if hasattr(diagnosis, "model_dump"):
        diag = diagnosis.model_dump(mode="json")
    elif isinstance(diagnosis, dict):
        diag = diagnosis
    else:
        raise TypeError("diagnosis must be RevisionDiagnosis or dict")

    target_idx = int(diag["target_line_index"])
    lines = text.splitlines()
    if target_idx < 0 or target_idx >= len(lines):
        target_idx = analysis.lines[0].line_index if analysis.lines else 0
    target_line = lines[target_idx] if lines else text
    span = _line_span(text, target_idx)
    max_chars = int(1.3 * max(len(target_line), 1))
    effective_brief = brief
    if diag.get("suggested_brief"):
        effective_brief = str(diag["suggested_brief"])

    pending_ops: list[dict[str, Any]] = []
    candidates: list[Candidate] = []

    # Family A: rare lexical on THAT line only
    for original, revised in _rare_substitutions(target_line):
        if "\n" in revised or len(revised) > max_chars:
            continue
        cand_id = new_id("cand")
        pending_ops.append(
            {
                "candidate_id": cand_id,
                "original_text": original,
                "revised_text": revised,
                "operation": "lexical_rare_substitute",
                "reason": f"brief={effective_brief}; method=rare_lexical",
                "default_improve": ["rarity", "diction"],
                "default_degrade": ["familiarity"],
            }
        )
        candidates.append(
            Candidate(
                candidate_id=cand_id,
                content=revised,
                method_family="rare_lexical",
                status=CandidateStatus.PROPOSED,
                line_index=target_idx,
                target_span=span,
                provenance_note="deterministic rare/lexical substitution",
            )
        )

    # Family B: neighbour phrase replace THAT line only
    neighbours_raw = _meaning_neighbours(target_line, config, limit=5, max_chars=max_chars)
    neighbours, rights_warnings = filter_restricted_source_hits(neighbours_raw, config)
    for hit in neighbours:
        seed = (hit.get("text") or "").strip()
        if not seed or seed == target_line or "\n" in seed or len(seed) > max_chars:
            continue
        cand_id = new_id("cand")
        pending_ops.append(
            {
                "candidate_id": cand_id,
                "original_text": target_line,
                "revised_text": seed,
                "operation": "fragment_informed_replace",
                "reason": f"brief={effective_brief}; method=fragment_informed",
                "default_improve": ["source_grounding", "theme_alignment"],
                "default_degrade": ["authorial_voice"],
            }
        )
        candidates.append(
            Candidate(
                candidate_id=cand_id,
                content=seed,
                method_family="fragment_informed",
                source_material=[hit.get("unit_id", "")],
                status=CandidateStatus.PROPOSED,
                line_index=target_idx,
                target_span=span,
                provenance_note="meaning-similar library/unit text",
            )
        )
        break  # one primary neighbour candidate is enough for the family

    # Fallback: legacy map on target line only
    if not candidates:
        legacy = generate_candidates(target_line, analyze_poem(target_line))
        for item in legacy:
            candidates.append(
                Candidate(
                    candidate_id=item.candidate_id,
                    content=item.revised_line,
                    method_family="legacy_lexical_map",
                    status=CandidateStatus.PROPOSED,
                    line_index=target_idx,
                    target_span=span,
                )
            )
            pending_ops.append(
                {
                    "candidate_id": item.candidate_id,
                    "original_text": target_line,
                    "revised_text": item.revised_line,
                    "operation": "legacy_lexical_map",
                    "reason": f"brief={effective_brief}; method=legacy_lexical_map",
                    "default_improve": ["diction"],
                    "default_degrade": [],
                }
            )

    evaluations: list[EvaluationResult] = []
    operations: list[RevisionOperation] = []
    ops_by_cand = {op["candidate_id"]: op for op in pending_ops}
    for cand in candidates:
        bundle_part, improve, degrade = build_evaluation_bundle(
            target_line,
            cand.content,
            work_plan=work_plan,
            config=config,
            grounding_refs=neighbours,
            subject_id=cand.candidate_id,
        )
        evaluations.extend(bundle_part.results)
        meta = ops_by_cand.get(
            cand.candidate_id,
            {
                "original_text": target_line,
                "revised_text": cand.content,
                "operation": cand.method_family,
                "reason": f"brief={effective_brief}",
                "default_improve": [],
                "default_degrade": [],
            },
        )
        predicted_improve = list(dict.fromkeys([*meta.get("default_improve", []), *improve]))
        predicted_degrade = list(dict.fromkeys([*meta.get("default_degrade", []), *degrade]))
        operations.append(
            RevisionOperation(
                operation_id=new_id("rop"),
                original_text=meta["original_text"],
                revised_text=meta["revised_text"],
                operation=meta["operation"],
                reason=meta["reason"],
                predicted_improvements=predicted_improve,
                predicted_degradations=predicted_degrade,
                candidate_id=cand.candidate_id,
                line_index=target_idx,
                target_span=span,
            )
        )

    manuscript = ManuscriptVersion(
        manuscript_id=new_id("ms"),
        version_id=new_id("msv"),
        text=text,
        parent_version_ids=[],
        created_at=datetime.now(UTC),
        provenance_map={"imported_from": str(target)},
        work_plan_id=(work_plan or {}).get("work_plan", {}).get("plan_id") if work_plan else None,
    )
    candidate_set = CandidateSet(
        set_id=new_id("cset"),
        target_scope="line",
        candidates=candidates,
    )
    eval_bundle = EvaluationBundle(
        bundle_id=new_id("eb"),
        subject_id=str(target),
        results=evaluations,
        created_at=datetime.now(UTC),
    )
    return {
        "brief": effective_brief,
        "target": str(target),
        "diagnosis": diag,
        "manuscript": manuscript.model_dump(mode="json"),
        "candidate_set": candidate_set.model_dump(mode="json"),
        "operations": [op.model_dump(mode="json") for op in operations],
        "evaluation": eval_bundle.model_dump(mode="json"),
        "evaluation_criteria": list(ALL_CRITERIA),
        "neighbours": neighbours,
        "warnings": rights_warnings,
        "status": "awaiting_human_decision",
        "method_families": sorted({c.method_family for c in candidates}),
        "target_line_index": target_idx,
    }


_ASSIST_MODES = frozenset({"rarefy", "ground_to_library", "meter_fit", "theme_align"})


def assist_reword(
    text: str,
    *,
    mode: str = "rarefy",
    config: Any = None,
) -> dict:
    """Inline reword assist — proposes candidates; never auto-applies. Span-bound rules.

    Modes: rarefy | ground_to_library | meter_fit | theme_align.
    """
    if mode not in _ASSIST_MODES:
        raise ValueError(
            f"unsupported assist mode {mode!r}; expected one of {sorted(_ASSIST_MODES)}"
        )
    # Treat input as a single selection span (no newlines allowed in replacements).
    selection = text.splitlines()[0] if "\n" in text else text
    max_chars = int(1.3 * max(len(selection), 1))
    candidates: list[dict] = []

    if mode in {"rarefy", "theme_align", "meter_fit"}:
        for original, revised in _rare_substitutions(selection):
            if "\n" in revised or len(revised) > max_chars:
                continue
            if mode == "meter_fit":
                delta, _ = _syllable_delta(selection, revised)
                if delta > 2:
                    continue
            candidates.append(
                {
                    "candidate_id": new_id("cand"),
                    "original": original,
                    "revised": revised,
                    "mode": mode,
                    "method_family": "rare_lexical",
                    "status": "proposed",
                }
            )

    if mode in {"ground_to_library", "theme_align", "meter_fit"}:
        for hit in _meaning_neighbours(selection, config, limit=3, max_chars=max_chars):
            revised = hit.get("text")
            if not revised or "\n" in revised or len(revised) > max_chars:
                continue
            if mode == "meter_fit":
                delta, _ = _syllable_delta(selection, revised)
                if delta > 2:
                    continue
            candidates.append(
                {
                    "candidate_id": new_id("cand"),
                    "original": selection,
                    "revised": revised,
                    "mode": mode,
                    "method_family": "fragment_informed",
                    "source_unit_id": hit.get("unit_id"),
                    "score": hit.get("score_combined"),
                    "status": "proposed",
                }
            )

    if not candidates:
        candidates.append(
            {
                "candidate_id": new_id("cand"),
                "original": selection,
                "revised": selection.strip(),
                "mode": mode,
                "method_family": "noop_normalise",
                "status": "proposed",
            }
        )
    return {
        "text": selection,
        "mode": mode,
        "candidates": candidates,
        "auto_apply": False,
        "supported_modes": sorted(_ASSIST_MODES),
        "note": "Human accept/reject required before manuscript change",
    }


def accept_candidate_to_manuscript(
    original_text: str,
    candidate_content: str,
    *,
    parent_version_id: str | None = None,
    line_index: int | None = None,
    manuscript_id: str | None = None,
) -> ManuscriptVersion:
    if line_index is not None:
        merged = _merge_line(original_text, line_index, candidate_content)
    else:
        merged = candidate_content
    return ManuscriptVersion(
        manuscript_id=manuscript_id or new_id("ms"),
        version_id=new_id("msv"),
        text=merged,
        parent_version_ids=[parent_version_id] if parent_version_id else [],
        accepted_change_ids=[f"accept-{uuid4().hex[:8]}"],
        created_at=datetime.now(UTC),
        provenance_map={"from_text": original_text[:200], "line_index": line_index},
    )
