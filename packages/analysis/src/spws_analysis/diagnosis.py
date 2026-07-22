"""Revision diagnosis: pick a bounded worst-line problem from analysis."""

from __future__ import annotations

from statistics import median
from typing import Any, Literal

from pydantic import Field

from spws_contracts_core.base import ContractModel
from spws_contracts_core.domain import Annotation, TextSpan
from spws_domain.ids import new_id

from .models import LineAnnotation, PoetryAnalysisResult

ProblemType = Literal["meter_break", "rarity_gap", "theme_drift", "repetition", "diction"]


class RevisionDiagnosis(ContractModel):
    diagnosis_id: str
    target_line_index: int = Field(ge=0)
    target_span: TextSpan | None = None
    problem_type: ProblemType
    evidence_annotation_ids: list[str] = Field(default_factory=list)
    suggested_brief: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    measured_values: dict[str, Any] = Field(default_factory=dict)


def _line_span(text: str, line_index: int, line_text: str) -> TextSpan | None:
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
            return TextSpan(start_char=start, end_char=end, quote=line_text)
        cursor = end + 1
    return None


def _ann_value(annotations: list[Annotation] | list[dict] | None, feature: str) -> Any | None:
    if not annotations:
        return None
    for ann in annotations:
        feat = ann.feature if hasattr(ann, "feature") else ann.get("feature")
        if feat == feature:
            return ann.value if hasattr(ann, "value") else ann.get("value")
    return None


def _rarity_for_line(line_text: str, annotations: list[Annotation] | list[dict] | None) -> float | None:
    if not annotations:
        return None
    for ann in annotations:
        feature = ann.feature if hasattr(ann, "feature") else ann.get("feature")
        if feature != "lexical_snapshot":
            continue
        value = ann.value if hasattr(ann, "value") else ann.get("value")
        if not isinstance(value, dict):
            continue
        content = int(value.get("content_tokens") or 0)
        rare = int(value.get("rare_hits") or 0)
        if content <= 0:
            return 0.0
        tokens = [t for t in line_text.split() if len(t.strip(".,;:!?\"'")) > 2]
        if not tokens:
            return float(rare) / float(content)
        return float(rare) / float(content)
    return None


def _syllable_deviation(lines: list[LineAnnotation]) -> dict[int, float]:
    counts = [line.syllable_count for line in lines]
    if not counts:
        return {}
    centre = float(median(counts))
    return {line.line_index: abs(float(line.syllable_count) - centre) for line in lines}


def _repetition_signal(
    lines: list[LineAnnotation],
    annotations: list[Annotation] | list[dict] | None,
) -> tuple[LineAnnotation, dict[str, Any], float] | None:
    metrics = _ann_value(annotations, "repetition_metrics")
    if not isinstance(metrics, dict):
        # Local fallback measurement
        from collections import Counter
        import re

        word_re = re.compile(r"[A-Za-z']+")
        all_tokens = [m.group(0).lower() for line in lines for m in word_re.finditer(line.line_text)]
        counts = Counter(t for t in all_tokens if len(t) > 2)
        if not counts:
            return None
        max_freq = max(counts.values())
        ratio = sum(n - 1 for n in counts.values() if n > 1) / float(max(len(all_tokens), 1))
        metrics = {
            "max_token_freq": max_freq,
            "repetition_ratio": ratio,
            "line_echo_score": 0.0,
            "repeated_tokens": [t for t, n in counts.most_common(5) if n >= 2],
        }

    ratio = float(metrics.get("repetition_ratio") or 0.0)
    echo = float(metrics.get("line_echo_score") or 0.0)
    max_freq = int(metrics.get("max_token_freq") or 0)
    if ratio < 0.12 and echo < 0.35 and max_freq < 3:
        return None

    # Pick the line with most repeated-token density
    repeated = set(metrics.get("repeated_tokens") or [])
    best: LineAnnotation | None = None
    best_score = -1.0
    for line in lines:
        tokens = [t.lower().strip(".,;:!?\"'") for t in line.line_text.split() if t.strip()]
        if not tokens:
            continue
        score = sum(1 for t in tokens if t in repeated) / float(len(tokens))
        # Also boost near-duplicate lines
        for other in lines:
            if other.line_index == line.line_index:
                continue
            if other.line_text.strip().lower() == line.line_text.strip().lower():
                score += 0.5
        if score > best_score:
            best_score = score
            best = line
    if best is None:
        best = lines[0]
    measured = {
        "repetition_ratio": ratio,
        "line_echo_score": echo,
        "max_token_freq": max_freq,
        "line_repetition_score": best_score,
        "selection": "repetition_metrics",
    }
    confidence = min(0.9, 0.5 + ratio + 0.3 * echo)
    return best, measured, confidence


def _theme_drift_signal(
    lines: list[LineAnnotation],
    annotations: list[Annotation] | list[dict] | None,
) -> tuple[LineAnnotation, dict[str, Any], float] | None:
    themes = _ann_value(annotations, "theme_tags")
    if not themes:
        return None
    if isinstance(themes, dict):
        theme_keys = [str(k).lower() for k in themes.keys()]
    elif isinstance(themes, list):
        theme_keys = [str(t).lower() for t in themes]
    else:
        theme_keys = [str(themes).lower()]
    if not theme_keys:
        return None

    # Score each line by overlap with theme tokens; lowest overlap = drift
    scored: list[tuple[LineAnnotation, float]] = []
    for line in lines:
        tokens = {t.lower().strip(".,;:!?\"'") for t in line.line_text.split() if len(t) > 2}
        if not tokens:
            continue
        overlap = sum(1 for key in theme_keys if any(key in tok or tok in key for tok in tokens))
        scored.append((line, overlap / float(max(len(theme_keys), 1))))
    if not scored:
        return None
    overlaps = [s for _, s in scored]
    if max(overlaps) - min(overlaps) < 0.25 and min(overlaps) > 0.0:
        # Not enough measured drift
        return None
    worst, score = min(scored, key=lambda item: item[1])
    if score > 0.35:
        return None
    measured = {
        "theme_overlap": score,
        "theme_tags": theme_keys[:8],
        "selection": "theme_drift",
    }
    return worst, measured, 0.6


def _pick_worst_line(
    lines: list[LineAnnotation],
    annotations: list[Annotation] | list[dict] | None,
) -> tuple[LineAnnotation, ProblemType, dict[str, Any], float]:
    if not lines:
        raise ValueError("diagnose_poem requires at least one analysed line")

    # Priority 1: strong repetition from measured metrics
    rep = _repetition_signal(lines, annotations)
    if rep is not None:
        worst, measured, confidence = rep
        if float(measured.get("repetition_ratio") or 0) >= 0.15 or float(
            measured.get("line_echo_score") or 0
        ) >= 0.4 or int(measured.get("max_token_freq") or 0) >= 4:
            return worst, "repetition", measured, confidence

    # Priority 2: meter
    measured: dict[str, Any] = {}
    with_foot = [line for line in lines if line.foot_accuracy is not None]
    if with_foot:
        worst = min(with_foot, key=lambda line: float(line.foot_accuracy or 0.0))
        measured = {
            "foot_accuracy": worst.foot_accuracy,
            "syllable_count": worst.syllable_count,
            "selection": "lowest_foot_accuracy",
        }
        confidence = 0.85
        problem: ProblemType = "meter_break"
        return worst, problem, measured, confidence

    deviations = _syllable_deviation(lines)
    if deviations and max(deviations.values()) > 0:
        worst_idx = max(deviations, key=deviations.get)  # type: ignore[arg-type]
        worst = next(line for line in lines if line.line_index == worst_idx)
        measured = {
            "syllable_count": worst.syllable_count,
            "syllable_deviation": deviations[worst_idx],
            "selection": "syllable_deviation",
        }
        confidence = 0.75
        return worst, "meter_break", measured, confidence

    # Priority 3: theme drift from measured theme overlap
    drift = _theme_drift_signal(lines, annotations)
    if drift is not None:
        worst, measured, confidence = drift
        return worst, "theme_drift", measured, confidence

    # Milder repetition still reportable
    if rep is not None:
        worst, measured, confidence = rep
        return worst, "repetition", measured, confidence

    # Fallback: rarity / diction
    rarity_scores: list[tuple[LineAnnotation, float]] = []
    for line in lines:
        rarity = _rarity_for_line(line.line_text, annotations)
        if rarity is not None:
            rarity_scores.append((line, rarity))
    if rarity_scores:
        worst, rarity = min(rarity_scores, key=lambda item: item[1])
        measured = {
            "rarity_ratio": rarity,
            "syllable_count": worst.syllable_count,
            "char_len": len(worst.line_text),
            "selection": "lowest_rarity",
        }
        return worst, "rarity_gap", measured, 0.55

    worst = max(lines, key=lambda line: (len(line.line_text), line.syllable_count))
    measured = {
        "syllable_count": worst.syllable_count,
        "char_len": len(worst.line_text),
        "selection": "longest_line",
    }
    return worst, "diction", measured, 0.45


def _evidence_ids(
    target_index: int,
    annotations: list[Annotation] | list[dict] | None,
) -> list[str]:
    if not annotations:
        return []
    ids: list[str] = []
    for ann in annotations:
        if hasattr(ann, "annotation_id"):
            aid = ann.annotation_id
            feature = ann.feature
            scope = getattr(ann, "scope", None)
        else:
            aid = ann.get("annotation_id")
            feature = ann.get("feature")
            scope = ann.get("scope")
        if not aid:
            continue
        if feature in {
            "syllable_count",
            "stress_pattern",
            "lexical_snapshot",
            "theme_tags",
            "affect_tags",
            "repetition_metrics",
            "motif_tokens",
        }:
            if scope in {None, "work", "line"} or feature in {
                "lexical_snapshot",
                "theme_tags",
                "affect_tags",
                "repetition_metrics",
            }:
                ids.append(str(aid))
        if len(ids) >= 8:
            break
    _ = target_index
    return ids


def _suggested_brief(problem: ProblemType, line: LineAnnotation) -> str:
    snippets = {
        "meter_break": f"Repair meter on line {line.line_index} (syllables={line.syllable_count})",
        "rarity_gap": f"Raise lexical rarity on line {line.line_index} without breaking sense",
        "theme_drift": f"Realign theme on line {line.line_index}",
        "repetition": f"Reduce repetition on line {line.line_index}",
        "diction": f"Improve diction on line {line.line_index}",
    }
    return snippets[problem]


def diagnose_poem(
    text: str,
    analysis_result_from_analyze_poem: PoetryAnalysisResult | dict[str, Any],
    annotations: list[Annotation] | list[dict] | None = None,
) -> RevisionDiagnosis:
    """Pick the worst line and emit a bounded RevisionDiagnosis."""
    if isinstance(analysis_result_from_analyze_poem, dict):
        analysis = PoetryAnalysisResult.model_validate(analysis_result_from_analyze_poem)
    else:
        analysis = analysis_result_from_analyze_poem

    worst, problem, measured, confidence = _pick_worst_line(analysis.lines, annotations)
    span = _line_span(text, worst.line_index, worst.line_text)
    evidence = _evidence_ids(worst.line_index, annotations)
    return RevisionDiagnosis(
        diagnosis_id=new_id("diag"),
        target_line_index=worst.line_index,
        target_span=span,
        problem_type=problem,
        evidence_annotation_ids=evidence,
        suggested_brief=_suggested_brief(problem, worst),
        confidence=confidence,
        measured_values=measured,
    )
