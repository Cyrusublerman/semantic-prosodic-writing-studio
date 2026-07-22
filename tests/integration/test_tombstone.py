"""D006: tombstone raw source — clear payload text, optional blob removal, keep audit row."""

from __future__ import annotations

import json
from pathlib import Path

from spws_ingestion import import_file
from spws_storage import WorkspaceStore, load_config, tombstone_raw_source


def test_tombstone_raw_source_keeps_audit_row(tmp_path: Path, temp_workspace, monkeypatch) -> None:
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    config = load_config(temp_workspace["config_path"])
    poem = tmp_path / "source.txt"
    poem.write_text("A quiet river under leaf shadow.\n", encoding="utf-8")

    package = import_file(poem)
    store = WorkspaceStore(config, workspace_root=temp_workspace["workspace"])
    raw = store.persist_input_package(package)
    assert raw.text
    blob_path = Path(raw.storage_location)
    assert blob_path.is_file()

    result = tombstone_raw_source(store, raw.source_id, remove_blob=True)
    assert result["tombstoned"] is True
    assert result["blob_removed"] is True
    assert not blob_path.exists()

    row = store._conn.execute(
        "SELECT payload_json FROM raw_sources WHERE source_id = ?",
        (raw.source_id,),
    ).fetchone()
    assert row is not None
    payload = json.loads(row["payload_json"])
    assert payload["tombstoned"] is True
    assert payload["text"] is None

    # Audit-resolvable via store; text cleared
    reloaded = store.get_raw_source(raw.source_id)
    assert reloaded.source_id == raw.source_id
    assert reloaded.text is None
    store.close()
