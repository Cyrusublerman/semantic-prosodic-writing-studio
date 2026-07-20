import unicodedata

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from spws_contracts_core.identifiers import new_uuid7
from spws_contracts_core.references import VersionReference
from spws_contracts_core.text import (
    MappingKind,
    MappingResult,
    RelocationRecord,
    RelocationResult,
    TextQuoteSelector,
    TextSpan,
    build_span_mapping,
    code_point_to_utf16_index,
    normalise_newlines,
    normalise_nfc,
    utf16_to_code_point_index,
)


@given(st.text())
def test_code_point_utf16_boundary_round_trip(text):
    for index in range(len(text) + 1):
        utf16 = code_point_to_utf16_index(text, index)
        assert utf16_to_code_point_index(text, utf16) == index


def test_utf16_surrogate_split_rejected():
    text = "a😀b"
    assert code_point_to_utf16_index(text, 2) == 3
    with pytest.raises(ValueError):
        utf16_to_code_point_index(text, 2)


def test_text_span_quote_validation():
    text = "alpha beta gamma"
    span = TextSpan(
        span_id="span-1",
        representation_id=new_uuid7(),
        representation_version=VersionReference(object_id=new_uuid7(), version_id=new_uuid7()),
        start=6,
        end=10,
        quote=TextQuoteSelector(exact="beta", prefix="alpha ", suffix=" gamma"),
    )
    span.validate_against(text)
    with pytest.raises(ValueError):
        span.model_copy(update={"quote": TextQuoteSelector(exact="wrong")}).validate_against(text)


def test_mapping_exact_and_bounded():
    source = "a\r\nb"
    target = normalise_newlines(source)
    mapping = build_span_mapping(
        source,
        target,
        mapping_id=new_uuid7(),
        source_representation_id=new_uuid7(),
        target_representation_id=new_uuid7(),
    )
    result, target_range = mapping.map_forward(0, 1)
    assert result is MappingResult.EXACT
    assert target_range == (0, 1)
    changed_result, changed_range = mapping.map_forward(1, 3)
    assert changed_result is MappingResult.BOUNDED
    assert changed_range is not None


def test_nfc_normalisation():
    source = "e\u0301"
    target = normalise_nfc(source)
    assert target == "é"
    assert unicodedata.is_normalized("NFC", target)


def test_relocation_result_contract():
    span = TextSpan(
        span_id="span-1",
        representation_id=new_uuid7(),
        representation_version=VersionReference(object_id=new_uuid7(), version_id=new_uuid7()),
        start=0,
        end=1,
    )
    record = RelocationRecord(
        source_span=span,
        target_representation_id=new_uuid7(),
        result=RelocationResult.UNIQUE,
        relocated_start=2,
        relocated_end=3,
    )
    assert record.relocated_start == 2
    with pytest.raises(ValidationError):
        RelocationRecord(
            source_span=span,
            target_representation_id=new_uuid7(),
            result=RelocationResult.AMBIGUOUS,
            candidate_ranges=((1, 2),),
        )
