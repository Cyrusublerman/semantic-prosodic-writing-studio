from __future__ import annotations

import re

from spws_contracts_core import PKLResult

from .models import EvidenceRef, LineAnnotation, PoetryAnalysisResult

_VOWEL_RE = re.compile(r"[aeiouyAEIOUY]+")


def _heuristic_syllables(word: str) -> int:
    word = re.sub(r"[^a-zA-Z']", "", word)
    if not word:
        return 0
    groups = _VOWEL_RE.findall(word.lower())
    count = len(groups)
    if word.lower().endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def _heuristic_stress(word: str) -> str:
    syllables = _heuristic_syllables(word)
    if syllables <= 1:
        return "1"
    return "0" + ("01" * (syllables - 1))[: syllables - 1] + "1"


def _line_heuristics(line: str) -> tuple[int, str]:
    words = line.split()
    syllables = sum(_heuristic_syllables(word) for word in words)
    stress = "".join(_heuristic_stress(word) for word in words)
    return syllables, stress


def _attach_evidence(line: str, pkl_results: list[PKLResult]) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    lowered = line.lower()
    for result in pkl_results:
        quote = result.relevant_span.quote if result.relevant_span else None
        haystack = " ".join(filter(None, [result.title, result.summary, quote])).lower()
        if not haystack:
            continue
        if any(token in haystack for token in lowered.split() if len(token) > 3):
            refs.append(
                EvidenceRef(
                    object_uid=result.object_uid,
                    title=result.title,
                    span_quote=quote,
                    confidence=result.confidence,
                )
            )
    return refs


def _analyze_with_wordrare(lines: list[str]) -> tuple[list[LineAnnotation], str] | None:
    try:
        from wordrare.forms import MeterEngine
    except Exception:
        return None
    try:
        engine = MeterEngine()
    except Exception:
        return None

    annotations: list[LineAnnotation] = []
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            analysis = engine.analyze_line(line, "iambic_pentameter")
        except Exception:
            return None
        annotations.append(
            LineAnnotation(
                line_index=index,
                line_text=line,
                syllable_count=analysis.syllable_count,
                stress_pattern=analysis.stress_pattern,
                meter_name=analysis.meter_match,
                foot_accuracy=analysis.foot_accuracy,
                notes=["wordrare"],
            )
        )
    if not annotations:
        return None
    return annotations, "wordrare"


def analyze_poem(text: str, pkl_results: list[PKLResult] | None = None) -> PoetryAnalysisResult:
    pkl_results = pkl_results or []
    lines = text.strip().splitlines()
    wordrare_result = _analyze_with_wordrare(lines)
    annotations: list[LineAnnotation] = []

    if wordrare_result is not None:
        base_annotations, engine = wordrare_result
        for item in base_annotations:
            evidence = _attach_evidence(item.line_text, pkl_results)
            annotations.append(
                LineAnnotation(
                    line_index=item.line_index,
                    line_text=item.line_text,
                    syllable_count=item.syllable_count,
                    stress_pattern=item.stress_pattern,
                    meter_name=item.meter_name,
                    foot_accuracy=item.foot_accuracy,
                    notes=item.notes,
                    evidence=evidence,
                )
            )
    else:
        engine = "heuristic"
        for index, line in enumerate(lines):
            if not line.strip():
                continue
            syllables, stress = _line_heuristics(line)
            annotations.append(
                LineAnnotation(
                    line_index=index,
                    line_text=line,
                    syllable_count=syllables,
                    stress_pattern=stress,
                    meter_name="unknown",
                    foot_accuracy=None,
                    notes=["heuristic_syllable_stress"],
                    evidence=_attach_evidence(line, pkl_results),
                )
            )

    return PoetryAnalysisResult(
        text=text,
        lines=annotations,
        engine=engine,
        pkl_evidence_count=sum(len(line.evidence) for line in annotations),
    )
