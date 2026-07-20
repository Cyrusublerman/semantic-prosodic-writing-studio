from __future__ import annotations

from datetime import UTC, datetime

from spws_contracts_core import InputPackage, RawSource, digest_text
from spws_contracts_core.domain import PrivacyState, RightsState
from spws_storage import WorkspaceStore


def test_input_package_requires_payload():
    try:
        InputPackage(
            package_id="inp-test",
            captured_at=datetime.now(UTC),
        )
        assert False, "expected validation error"
    except ValueError:
        pass


def test_raw_source_immutable_flag():
    package = InputPackage(
        package_id="inp-1",
        text="hello",
        captured_at=datetime.now(UTC),
    )
    digest = digest_text("hello")
    try:
        RawSource(
            source_id="raw-1",
            input_package_id=package.package_id,
            media_type="text/plain",
            text="hello",
            content_digest=digest,
            stored_at=datetime.now(UTC),
            storage_location="/tmp/x",
            rights=RightsState.PUBLIC,
            privacy=PrivacyState.PUBLIC,
            immutable=False,
        )
        assert False, "expected immutable enforcement"
    except ValueError:
        pass


def test_persist_input_package_roundtrip(spws_config, temp_workspace):
    store = WorkspaceStore(spws_config, workspace_root=temp_workspace["workspace"])
    package = InputPackage(
        package_id="inp-roundtrip",
        text="A line of verse",
        captured_at=datetime.now(UTC),
        rights=RightsState.PUBLIC,
        privacy=PrivacyState.INTERNAL,
    )
    raw = store.persist_input_package(package)
    assert raw.input_package_id == package.package_id
    assert raw.immutable is True
    assert store.blobs.exists(raw.content_digest.value)
    loaded = store.get_raw_source(raw.source_id)
    assert loaded.text == "A line of verse"
    store.close()
