"""Repetition / motif density analyser."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from spws_contracts_core.domain import Annotation, StructuralScope
from spws_domain.ids import new_id

COMPONENT_ID = "repetition_motif"
COMPONENT_VERSION = "0.1.0"

_WORD_RE = re.compile(r"[A-Za-z']+")


def _line_token_overlap(lines: list[str]) -> dict[str, Any]:
    tokenised = [[m.group(0).lower() for m in _WORD_RE.finditer(line)] for line in lines]
    content = [t for line in tokenised for t in line if len(t) > 2]
    counts = Counter(content)
    if not content:
        return {
            "max_token_freq": 0,
            "repeated_tokens": [],
            "repetition_ratio": 0.0,
            "line_echo_score": 0.0,
        }
    max_freq = max(counts.values())
    repeated = [tok for tok, n in counts.most_common(12) if n >= 2]
    repetition_ratio = sum(n - 1 for n in counts.values() if n > 1) / float(len(content))

    # Adjacent-line echo: share of tokens also in previous line
    echoes: list[float] = []
    for i in range(1, len(tokenised)):
        prev = set(tokenised[i - 1])
        cur = tokenised[i]
        if not cur:
            continue
        shared = sum(1 for t in cur if t in prev)
        echoes.append(shared / float(len(cur)))
    line_echo = sum(echoes) / float(len(echoes)) if echoes else 0.0
    return {
        "max_token_freq": max_freq,
        "repeated_tokens": repeated,
        "repetition_ratio": float(repetition_ratio),
        "line_echo_score": float(line_echo),
    }


def analyse_repetition_motif(
    text: str,
    *,
    source_id: str,
    config: Any | None = None,
) -> dict[str, Any]:
    _ = config
    lines = [ln for ln in text.splitlines() if ln.strip()]
    metrics = _line_token_overlap(lines)
    # Rule-based measurement → confidence from signal strength, not constant.
    signal = max(metrics["repetition_ratio"], metrics["line_echo_score"])
    confidence = max(0.4, min(0.92, 0.45 + 0.5 * signal))
    annotations = [
        Annotation(
            annotation_id=new_id("ann"),
            source_object=source_id,
            scope=StructuralScope.WORK,
            feature="repetition_metrics",
            value=metrics,
            confidence=confidence,
            analyser=COMPONENT_ID,
            analyser_version=COMPONENT_VERSION,
        )
    ]
    if metrics["repeated_tokens"]:
        annotations.append(
            Annotation(
                annotation_id=new_id("ann"),
                source_object=source_id,
                scope=StructuralScope.WORK,
                feature="motif_tokens",
                value=metrics["repeated_tokens"][:8],
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
        "field_confidence": {"repetition": confidence},
        "warnings": [],
        "metrics": metrics,
    }
