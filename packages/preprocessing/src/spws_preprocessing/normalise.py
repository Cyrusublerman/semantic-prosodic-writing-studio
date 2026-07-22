"""Deterministic text normalisation for retained sources."""

from __future__ import annotations

from spws_contracts_core.domain import NormalisedSource
from spws_domain.ids import new_id


def normalise_text(text: str) -> tuple[str, list[str]]:
    """Collapse ``\\r\\n``, strip trailing spaces per line; keep content."""
    trace: list[str] = []
    working = text
    if "\r\n" in working or "\r" in working:
        working = working.replace("\r\n", "\n").replace("\r", "\n")
        trace.append("collapse_crlf")
    lines = working.split("\n")
    stripped_lines = [line.rstrip(" \t") for line in lines]
    if stripped_lines != lines:
        trace.append("strip_trailing_spaces")
        working = "\n".join(stripped_lines)
    else:
        working = "\n".join(lines)
    return working, trace


def build_normalised_source(source_id: str, text: str) -> NormalisedSource:
    normalised, transform_trace = normalise_text(text)
    return NormalisedSource(
        normalised_id=new_id("norm"),
        source_object_id=source_id,
        text=normalised,
        transform_trace=transform_trace,
    )
