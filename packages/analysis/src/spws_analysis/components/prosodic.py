"""Prosodic analyser: syllable / stress / IPA-coverage confidence."""

from __future__ import annotations

from typing import Any

from spws_contracts_core.domain import Annotation, StructuralScope, TextSpan
from spws_domain.ids import new_id

from ..poetry import analyze_poem

COMPONENT_ID = "prosodic"
COMPONENT_VERSION = "0.1.0"


def _ipa_coverage_confidence(text: str, engine: str) -> float:
    """Derive confidence from IPA / pronunciation coverage or rule-only engine."""
    if engine == "wordrare":
        tokens = [t for t in text.split() if t.strip()]
        if not tokens:
            return 0.4
        covered = 0
        try:
            from wordrare.database import WordRecord, get_session

            with get_session() as session:
                for token in tokens[:40]:
                    lemma = token.strip(".,;:!?\"'").lower()
                    if not lemma:
                        continue
                    row = session.query(WordRecord).filter(WordRecord.lemma == lemma).first()
                    if row is None:
                        continue
                    ipa = getattr(row, "ipa_us_cmu", None) or getattr(row, "ipa_dict", None)
                    if ipa:
                        covered += 1
            ratio = covered / float(len(tokens[:40]))
            return max(0.45, min(0.98, 0.5 + 0.48 * ratio))
        except Exception:
            return 0.85  # wordrare meter path without DB IPA → model confidence
    # Heuristic / rule-only
    return 0.5


def analyse_prosodic(
    text: str,
    *,
    source_id: str,
    config: Any | None = None,
) -> dict[str, Any]:
    _ = config
    poetry = analyze_poem(text)
    confidence = _ipa_coverage_confidence(text, poetry.engine)
    annotations: list[Annotation] = []
    warnings: list[str] = []
    if poetry.engine == "heuristic":
        warnings.append("prosodic: rule-only heuristic engine (no WordRare meter)")

    cursor = 0
    for line in poetry.lines:
        start = text.find(line.line_text, cursor)
        if start < 0:
            start = cursor
        end = start + len(line.line_text)
        cursor = end + 1
        span = TextSpan(start_char=start, end_char=end, quote=line.line_text)
        annotations.append(
            Annotation(
                annotation_id=new_id("ann"),
                source_object=source_id,
                scope=StructuralScope.LINE,
                location=span,
                feature="syllable_count",
                value=line.syllable_count,
                confidence=confidence,
                analyser=COMPONENT_ID,
                analyser_version=COMPONENT_VERSION,
            )
        )
        if line.stress_pattern:
            annotations.append(
                Annotation(
                    annotation_id=new_id("ann"),
                    source_object=source_id,
                    scope=StructuralScope.LINE,
                    location=span,
                    feature="stress_pattern",
                    value=line.stress_pattern,
                    confidence=max(0.0, confidence - 0.05),
                    analyser=COMPONENT_ID,
                    analyser_version=COMPONENT_VERSION,
                )
            )
        if line.foot_accuracy is not None:
            annotations.append(
                Annotation(
                    annotation_id=new_id("ann"),
                    source_object=source_id,
                    scope=StructuralScope.LINE,
                    location=span,
                    feature="foot_accuracy",
                    value=line.foot_accuracy,
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
            feature="prosody_engine",
            value=poetry.engine,
            confidence=confidence,
            analyser=COMPONENT_ID,
            analyser_version=COMPONENT_VERSION,
        )
    )
    return {
        "annotations": annotations,
        "structural_units": [],
        "component_id": COMPONENT_ID,
        "component_version": COMPONENT_VERSION,
        "field_confidence": {"syllable": confidence, "prosodic": confidence},
        "warnings": warnings,
        "poetry": poetry,
    }
