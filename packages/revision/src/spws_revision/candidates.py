from __future__ import annotations

import hashlib

from spws_analysis import PoetryAnalysisResult

from .models import RevisionCandidate

_LEXICAL_MAP = {
    "bright": "luminous",
    "dark": "shadowed",
    "walk": "wander",
    "love": "devotion",
    "night": "twilight",
    "day": "morning",
    "wind": "breeze",
    "sea": "ocean",
    "heart": "spirit",
    "old": "ancient",
}


def _candidate_id(line_index: int, original: str, revised: str) -> str:
    digest = hashlib.sha256(f"{line_index}:{original}:{revised}".encode()).hexdigest()[:12]
    return f"cand-{digest}"


def generate_candidates(text: str, analysis: PoetryAnalysisResult) -> list[RevisionCandidate]:
    lines = text.splitlines()
    candidates: list[RevisionCandidate] = []
    for annotation in analysis.lines:
        original = annotation.line_text
        revised = original
        changed = False
        lowered = original.lower()
        for source, target in sorted(_LEXICAL_MAP.items()):
            if source in lowered.split():
                revised = " ".join(
                    target if token.lower().strip(".,;:!?") == source else token
                    for token in original.split()
                )
                changed = True
                break
        if not changed and annotation.syllable_count > 10:
            words = original.split()
            if len(words) > 4:
                revised = " ".join(words[:-1])
                changed = True
        if changed and revised != original:
            candidates.append(
                RevisionCandidate(
                    candidate_id=_candidate_id(annotation.line_index, original, revised),
                    line_index=annotation.line_index,
                    kind="lexical_substitution" if revised.split() != original.split() else "line_variant",
                    original_line=original,
                    revised_line=revised,
                    rationale="Deterministic lexical substitution or trim for meter balance",
                )
            )
    if not candidates and lines:
        first = lines[0]
        revised = first.replace("  ", " ").strip()
        if revised != first:
            candidates.append(
                RevisionCandidate(
                    candidate_id=_candidate_id(0, first, revised),
                    line_index=0,
                    kind="line_variant",
                    original_line=first,
                    revised_line=revised,
                    rationale="Whitespace normalization variant",
                )
            )
    return candidates


def apply_decision(text: str, candidates: list[RevisionCandidate], candidate_ids: list[str]) -> str:
    lookup = {item.candidate_id: item for item in candidates}
    lines = text.splitlines()
    for candidate_id in candidate_ids:
        candidate = lookup[candidate_id]
        if 0 <= candidate.line_index < len(lines):
            lines[candidate.line_index] = candidate.revised_line
    return "\n".join(lines)
