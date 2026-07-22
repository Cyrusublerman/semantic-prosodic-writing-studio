"""Helpers that enforce RawSource immutability invariants."""

from __future__ import annotations

from typing import Any

from spws_contracts_core.domain import RawSource
from spws_contracts_core.digests import digest_text


class ImmutableRawSourceError(ValueError):
    """Raised when a RawSource immutability invariant is violated."""


def assert_immutable_flag(source: RawSource) -> None:
    if not source.immutable:
        raise ImmutableRawSourceError(
            f"RawSource {source.source_id} must have immutable=True"
        )


def assert_raw_source_text_unchanged(source: RawSource, original_text: str) -> None:
    """Ensure retained text still matches the supplied original payload."""
    assert_immutable_flag(source)
    if source.text is None:
        raise ImmutableRawSourceError(
            f"RawSource {source.source_id} has no text payload to compare"
        )
    if source.text != original_text:
        raise ImmutableRawSourceError(
            f"RawSource {source.source_id} text diverged from original"
        )


def assert_raw_source_digest_matches(source: RawSource) -> None:
    """Recompute text digest and require equality with the stored digest."""
    assert_immutable_flag(source)
    if source.text is None:
        raise ImmutableRawSourceError(
            f"RawSource {source.source_id} has no text for digest check"
        )
    current = digest_text(source.text)
    if current.algorithm != source.content_digest.algorithm:
        raise ImmutableRawSourceError(
            f"RawSource {source.source_id} digest algorithm mismatch: "
            f"{current.algorithm} != {source.content_digest.algorithm}"
        )
    if current.value != source.content_digest.value:
        raise ImmutableRawSourceError(
            f"RawSource {source.source_id} content digest mismatch"
        )


def assert_immutable_raw_source(
    source: RawSource,
    *,
    original_text: str | None = None,
    check_digest: bool = True,
) -> None:
    """
    Fail closed if RawSource immutability invariants do not hold.

    Always checks ``immutable``. Optionally compares ``original_text`` and
    recomputes the content digest when ``check_digest`` is true and text exists.
    """
    assert_immutable_flag(source)
    if original_text is not None:
        assert_raw_source_text_unchanged(source, original_text)
    if check_digest and source.text is not None:
        assert_raw_source_digest_matches(source)


def forbid_raw_source_mutation(source: RawSource, field: str, new_value: Any) -> None:
    """Raise if a caller attempts to replace a protected RawSource field."""
    assert_immutable_flag(source)
    protected = {
        "source_id",
        "input_package_id",
        "text",
        "content_digest",
        "storage_location",
        "media_type",
        "encoding",
    }
    if field in protected:
        current = getattr(source, field, None)
        if new_value != current:
            raise ImmutableRawSourceError(
                f"cannot mutate RawSource.{field} on immutable source {source.source_id}"
            )
