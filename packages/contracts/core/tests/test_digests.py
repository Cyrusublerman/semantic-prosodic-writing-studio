import math

import pytest

from spws_contracts_core.digests import (
    RECORD_PROJECTION_V1,
    canonical_json_bytes,
    digest_bytes,
    digest_json,
    digest_record_projection,
    digest_text,
    verify_digest,
)


def test_rfc8785_and_sha256_known_value():
    data = canonical_json_bytes({"b": 2, "a": 1})
    assert data == b'{"a":1,"b":2}'
    record = digest_json({"b": 2, "a": 1})
    assert record.value == "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"


def test_unsafe_json_values_rejected():
    with pytest.raises(ValueError):
        canonical_json_bytes({"value": 2**53})
    with pytest.raises(ValueError):
        canonical_json_bytes({"value": math.inf})
    with pytest.raises(ValueError):
        canonical_json_bytes({1: "bad key"})


def test_raw_and_text_digests_are_representation_specific():
    raw = digest_bytes(b"abc")
    text = digest_text("abc")
    assert raw.value == text.value
    assert raw.basis != text.basis
    assert verify_digest(raw, b"abc")


def test_record_projection_injects_projection_id():
    record = digest_record_projection({"x": 1})
    assert record.canonicalisation.version == RECORD_PROJECTION_V1
