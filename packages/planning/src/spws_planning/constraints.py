"""Checkable WorkPlan constraints: retention, meter, length."""

from __future__ import annotations

from typing import Any


def check_semantic_retention(orig: str, revised: str, gauge: Any) -> dict[str, Any]:
    """Cosine similarity between original and revised via gauge.embedder when available."""
    label = "semantic_retention"
    try:
        from spws_semantics.similarity import cosine

        embedder = getattr(gauge, "embedder", None)
        if embedder is None:
            return {"ok": False, "measured": 0.0, "label": label, "inferred_label": "inferred"}
        a = embedder.encode(orig)
        b = embedder.encode(revised)
        score = float(cosine(a, b))
        return {
            "ok": score >= 0.55,
            "measured": score,
            "label": label,
            "inferred_label": "measured",
        }
    except Exception as exc:
        return {
            "ok": False,
            "measured": 0.0,
            "label": label,
            "inferred_label": "inferred",
            "error": str(exc),
        }


def check_meter_delta(
    orig_syllables: int,
    revised_syllables: int,
    *,
    max_delta: int = 2,
) -> dict[str, Any]:
    delta = abs(int(revised_syllables) - int(orig_syllables))
    return {
        "ok": delta <= max_delta,
        "measured": float(delta),
        "label": "meter_delta",
        "inferred_label": "measured",
    }


def check_length_bound(
    orig: str,
    revised: str,
    *,
    max_ratio: float = 1.3,
) -> dict[str, Any]:
    base = max(len(orig), 1)
    ratio = len(revised) / float(base)
    return {
        "ok": ratio <= max_ratio and "\n" not in revised,
        "measured": float(ratio),
        "label": "length_bound",
        "inferred_label": "measured",
    }
