import pytest
from pydantic import ValidationError

from spws_contracts_core.digests import digest_bytes, digest_json
from spws_contracts_core.envelope import PayloadDescriptor, PayloadKind


def test_embedded_payload_requires_digest():
    with pytest.raises(ValidationError):
        PayloadDescriptor(payload_kind=PayloadKind.EMBEDDED, value={"x": 1})


def test_object_store_payload_contract():
    payload = PayloadDescriptor(
        payload_kind=PayloadKind.OBJECT_STORE,
        media_type="application/octet-stream",
        location_reference="blob/abc",
        size_bytes=3,
        digest=digest_bytes(b"abc"),
    )
    assert payload.size_bytes == 3


def test_tombstone_rejects_content():
    with pytest.raises(ValidationError):
        PayloadDescriptor(
            payload_kind=PayloadKind.TOMBSTONE,
            value={"deleted": True},
            digest=digest_json({"deleted": True}),
        )


def test_embedded_payload_rejects_digest_mismatch():
    with pytest.raises(ValidationError):
        PayloadDescriptor(
            payload_kind=PayloadKind.EMBEDDED,
            media_type="application/json",
            value={"x": 1},
            digest=digest_json({"x": 2}),
        )
