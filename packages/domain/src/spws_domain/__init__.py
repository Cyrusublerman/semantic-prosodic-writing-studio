"""SPWS domain helpers."""

from .ids import new_id
from .invariants import (
    ImmutableRawSourceError,
    assert_immutable_flag,
    assert_immutable_raw_source,
    assert_raw_source_digest_matches,
    assert_raw_source_text_unchanged,
    forbid_raw_source_mutation,
)
from .spans import make_span, map_domain_span_to_dict, span_from_offsets

__all__ = [
    "ImmutableRawSourceError",
    "assert_immutable_flag",
    "assert_immutable_raw_source",
    "assert_raw_source_digest_matches",
    "assert_raw_source_text_unchanged",
    "forbid_raw_source_mutation",
    "make_span",
    "map_domain_span_to_dict",
    "new_id",
    "span_from_offsets",
]
