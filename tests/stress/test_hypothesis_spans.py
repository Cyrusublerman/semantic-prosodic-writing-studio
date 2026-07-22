"""Property stress: unicode/span offsets stay coherent under random poems."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings, strategies as st

from spws_analysis import analyse_document


_printable = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    min_size=1,
    max_size=40,
)


@given(
    lines=st.lists(_printable, min_size=2, max_size=12),
)
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_random_poem_analysis_spans_in_bounds(stress_config, lines):
    poem = "\n".join(lines)
    if not poem.strip():
        return
    suite = analyse_document(poem, kind="poem", config=stress_config)
    bundle = suite["bundle"]
    if hasattr(bundle, "model_dump"):
        bundle = bundle.model_dump(mode="json")
    for ann in bundle.get("annotations") or []:
        loc = ann.get("location") or {}
        start, end = loc.get("start_char"), loc.get("end_char")
        if start is None or end is None:
            continue
        assert 0 <= int(start) <= int(end) <= len(poem)
