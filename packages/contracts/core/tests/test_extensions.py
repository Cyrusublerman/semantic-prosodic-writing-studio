import pytest
from pydantic import ValidationError

from spws_contracts_core.extensions import ExtensionRecord, check_extensions
from spws_contracts_core.schema import SchemaReference


def schema_ref():
    return SchemaReference(
        schema_id="urn:pkl:spws:schema:extension:test-extension:1.0.0",
        schema_version="1.0.0",
    )


def test_unknown_noncritical_extension_returns_warning():
    extension = ExtensionRecord(
        namespace="x.example.test",
        schema=schema_ref(),
        critical=False,
        value={"feature": True},
    )
    warnings = check_extensions((extension,), frozenset())
    assert warnings[0].code == "COC-W-011"


def test_unknown_critical_extension_rejected():
    extension = ExtensionRecord(
        namespace="x.example.test",
        schema=schema_ref(),
        critical=True,
        value={"feature": True},
    )
    with pytest.raises(ValueError):
        check_extensions((extension,), frozenset())


def test_extension_cannot_override_core_fields():
    with pytest.raises(ValidationError):
        ExtensionRecord(
            namespace="x.example.test",
            schema=schema_ref(),
            value={"object_id": "bad"},
        )
