"""Deterministic English unitisation into MeaningUnits with spans."""

from __future__ import annotations

import hashlib
import re
import uuid

from spws_contracts_core.digests import digest_text
from spws_contracts_core.domain import MeaningScale, MeaningUnit, PrivacyState, RightsState, TextSpan

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'])|(?<=\n)\s*(?=\S)")
_WORD_RE = re.compile(r"[A-Za-z']+")


def _unit_id(scale: str, start: int, end: int, text: str) -> str:
    digest = hashlib.sha256(f"{scale}:{start}:{end}:{text}".encode()).hexdigest()[:12]
    return f"mu-{digest}"


def _span(text: str, start: int, end: int) -> TextSpan:
    return TextSpan(start_char=start, end_char=end, quote=text[start:end])


def unitise_paragraphs(text: str, *, source_object_id: str | None = None) -> list[MeaningUnit]:
    units: list[MeaningUnit] = []
    if not text:
        return units
    parts = re.split(r"\n\s*\n+", text)
    cursor = 0
    for part in parts:
        idx = text.find(part, cursor)
        if idx < 0:
            continue
        start, end = idx, idx + len(part)
        cursor = end
        stripped = part.strip()
        if not stripped:
            continue
        # adjust to stripped bounds within original
        inner = text.find(stripped, start)
        units.append(
            MeaningUnit(
                unit_id=_unit_id("paragraph", inner, inner + len(stripped), stripped),
                scale=MeaningScale.PARAGRAPH,
                text=stripped,
                span=_span(text, inner, inner + len(stripped)),
                source_object_id=source_object_id,
                content_digest=digest_text(stripped),
            )
        )
    if not units and text.strip():
        stripped = text.strip()
        start = text.find(stripped)
        units.append(
            MeaningUnit(
                unit_id=_unit_id("paragraph", start, start + len(stripped), stripped),
                scale=MeaningScale.PARAGRAPH,
                text=stripped,
                span=_span(text, start, start + len(stripped)),
                source_object_id=source_object_id,
                content_digest=digest_text(stripped),
            )
        )
    return units


def unitise_sentences(text: str, *, source_object_id: str | None = None, parent_unit_id: str | None = None) -> list[MeaningUnit]:
    units: list[MeaningUnit] = []
    if not text.strip():
        return units
    # Prefer newline-delimited poetic lines when present
    if "\n" in text.strip() and text.count("\n") >= 1:
        cursor = 0
        for line in text.splitlines():
            idx = text.find(line, cursor)
            if idx < 0:
                continue
            cursor = idx + len(line)
            stripped = line.strip()
            if not stripped:
                continue
            inner = text.find(stripped, idx)
            units.append(
                MeaningUnit(
                    unit_id=_unit_id("sentence", inner, inner + len(stripped), stripped),
                    scale=MeaningScale.SENTENCE,
                    text=stripped,
                    span=_span(text, inner, inner + len(stripped)),
                    source_object_id=source_object_id,
                    parent_unit_id=parent_unit_id,
                    content_digest=digest_text(stripped),
                )
            )
        return units

    cursor = 0
    remainder = text
    offset = 0
    while remainder.strip():
        match = _SENTENCE_SPLIT.search(remainder)
        if match:
            chunk = remainder[: match.start()]
            next_start = match.end()
        else:
            chunk = remainder
            next_start = len(remainder)
        stripped = chunk.strip()
        if stripped:
            inner = text.find(stripped, offset)
            if inner < 0:
                inner = offset
            units.append(
                MeaningUnit(
                    unit_id=_unit_id("sentence", inner, inner + len(stripped), stripped),
                    scale=MeaningScale.SENTENCE,
                    text=stripped,
                    span=_span(text, inner, inner + len(stripped)),
                    source_object_id=source_object_id,
                    parent_unit_id=parent_unit_id,
                    content_digest=digest_text(stripped),
                )
            )
        offset += next_start
        remainder = remainder[next_start:]
        if not match:
            break
    return units


def unitise_phrases(text: str, *, source_object_id: str | None = None, max_chars: int = 80) -> list[MeaningUnit]:
    """Split into short collage-friendly phrase units by punctuation/clauses."""
    units: list[MeaningUnit] = []
    pieces = re.split(r"[,;:—–]|\s+-\s+", text)
    cursor = 0
    for piece in pieces:
        idx = text.find(piece, cursor)
        if idx < 0:
            continue
        cursor = idx + len(piece)
        stripped = piece.strip()
        if len(stripped) < 3:
            continue
        if len(stripped) > max_chars:
            # further chunk by words
            words = stripped.split()
            buf: list[str] = []
            buf_start = text.find(stripped, idx)
            running = buf_start if buf_start >= 0 else idx
            for word in words:
                trial = (" ".join(buf + [word])).strip()
                if len(trial) > max_chars and buf:
                    chunk = " ".join(buf)
                    start = text.find(chunk, max(running, 0))
                    if start < 0:
                        start = max(running, 0)
                    units.append(
                        MeaningUnit(
                            unit_id=_unit_id("phrase", start, start + len(chunk), chunk),
                            scale=MeaningScale.PHRASE,
                            text=chunk,
                            span=_span(text, start, start + len(chunk)),
                            source_object_id=source_object_id,
                            content_digest=digest_text(chunk),
                        )
                    )
                    running = start + len(chunk)
                    buf = [word]
                else:
                    buf.append(word)
            if buf:
                chunk = " ".join(buf)
                start = text.find(chunk, max(running, 0))
                if start < 0:
                    start = max(running, 0)
                units.append(
                    MeaningUnit(
                        unit_id=_unit_id("phrase", start, start + len(chunk), chunk),
                        scale=MeaningScale.PHRASE,
                        text=chunk,
                        span=_span(text, start, start + len(chunk)),
                        source_object_id=source_object_id,
                        content_digest=digest_text(chunk),
                    )
                )
            continue
        inner = text.find(stripped, idx)
        if inner < 0:
            continue
        units.append(
            MeaningUnit(
                unit_id=_unit_id("phrase", inner, inner + len(stripped), stripped),
                scale=MeaningScale.PHRASE,
                text=stripped,
                span=_span(text, inner, inner + len(stripped)),
                source_object_id=source_object_id,
                content_digest=digest_text(stripped),
            )
        )
    return units


def unitise_words(text: str, *, source_object_id: str | None = None) -> list[MeaningUnit]:
    units: list[MeaningUnit] = []
    for match in _WORD_RE.finditer(text):
        token = match.group(0)
        if len(token) < 3:
            continue
        start, end = match.span()
        units.append(
            MeaningUnit(
                unit_id=_unit_id("word", start, end, token.lower()),
                scale=MeaningScale.WORD,
                text=token.lower(),
                span=_span(text, start, end),
                source_object_id=source_object_id,
                content_digest=digest_text(token.lower()),
            )
        )
    return units


def unitise_text(
    text: str,
    *,
    source_object_id: str | None = None,
    scales: list[MeaningScale] | None = None,
    object_uid: str | None = None,
    commit_sha: str | None = None,
    rights: RightsState = RightsState.UNKNOWN,
    privacy: PrivacyState = PrivacyState.UNKNOWN,
) -> list[MeaningUnit]:
    """Unitise text into the requested scales (default: paragraph, sentence, phrase)."""
    wanted = set(scales or [MeaningScale.PARAGRAPH, MeaningScale.SENTENCE, MeaningScale.PHRASE])
    units: list[MeaningUnit] = []
    if MeaningScale.PARAGRAPH in wanted:
        units.extend(unitise_paragraphs(text, source_object_id=source_object_id))
    if MeaningScale.SENTENCE in wanted:
        units.extend(unitise_sentences(text, source_object_id=source_object_id))
    if MeaningScale.PHRASE in wanted:
        units.extend(unitise_phrases(text, source_object_id=source_object_id))
    if MeaningScale.WORD in wanted:
        units.extend(unitise_words(text, source_object_id=source_object_id))
    enriched: list[MeaningUnit] = []
    for unit in units:
        enriched.append(
            unit.model_copy(
                update={
                    "object_uid": object_uid,
                    "commit_sha": commit_sha,
                    "rights": rights,
                    "privacy": privacy,
                    "source_object_id": source_object_id or unit.source_object_id,
                }
            )
        )
    return enriched


def new_source_id() -> str:
    return f"src-{uuid.uuid4().hex[:12]}"
