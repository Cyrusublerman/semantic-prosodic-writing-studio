import pytest
from pydantic import ValidationError

from spws_contracts_core.schema import SchemaReference, VersionRange, parse_semver


def test_schema_reference_urn_version_matches():
    ref = SchemaReference(
        schema_id="urn:pkl:spws:schema:contracts-core:object-reference:1.0.0",
        schema_version="1.0.0",
    )
    assert ref.schema_version == "1.0.0"


def test_schema_reference_rejects_mismatched_urn_version():
    with pytest.raises(ValidationError):
        SchemaReference(
            schema_id="urn:pkl:spws:schema:contracts-core:object-reference:1.0.0",
            schema_version="1.1.0",
        )


def test_version_range_major_and_bounds():
    constraint = VersionRange(minimum="1.2.0", maximum="2.0.0", required_major=1)
    assert constraint.contains("1.2.0")
    assert constraint.contains("1.9.9")
    assert not constraint.contains("2.0.0")
    assert not constraint.contains("1.1.9")


def test_semver_parser_rejects_leading_zero():
    with pytest.raises(ValueError):
        parse_semver("01.0.0")


def test_semver_prerelease_ordering():
    constraint = VersionRange(minimum="1.0.0-alpha", maximum="1.0.0", include_maximum=True)
    assert constraint.contains("1.0.0-alpha.1")
    assert constraint.contains("1.0.0")
    assert not constraint.contains("0.9.9")
