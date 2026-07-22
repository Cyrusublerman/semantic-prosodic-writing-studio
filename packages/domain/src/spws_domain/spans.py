"""TextSpan helpers over spws_contracts_core.domain.TextSpan."""

from __future__ import annotations

from typing import Any

from spws_contracts_core.domain import TextSpan


def make_span(text: str, start: int, end: int) -> TextSpan:
    quote = text[start:end]
    return TextSpan(start_char=start, end_char=end, quote=quote)


def span_from_offsets(text: str, start: int, end: int) -> TextSpan:
    """Alias for make_span; validates offsets against text length."""
    if start < 0 or end < start or end > len(text):
        raise ValueError(
            f"invalid span offsets start={start} end={end} for text length {len(text)}"
        )
    return make_span(text, start, end)


def map_domain_span_to_dict(span: TextSpan) -> dict[str, Any]:
    """Serialize a TextSpan to a plain dict."""
    return span.model_dump()
