from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from spws_contracts_core.identifiers import ObjectId, new_uuid7


def test_new_uuid7_is_rfc_uuid7():
    value = new_uuid7()
    assert value.version == 7
    assert value.variant == "specified in RFC 4122"


def test_identifier_alias_rejects_non_v7():
    adapter = TypeAdapter(ObjectId)
    with pytest.raises(ValidationError):
        adapter.validate_python(uuid4())


def test_json_wire_parses_uuid7_string():
    value = new_uuid7()
    adapter = TypeAdapter(ObjectId)
    assert adapter.validate_json(f'"{value}"') == value
