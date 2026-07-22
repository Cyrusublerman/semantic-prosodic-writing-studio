"""Phase 2: hybrid BlobStore + SQLite manuscript versions."""

from __future__ import annotations

from datetime import UTC, datetime

from spws_contracts_core.domain import ManuscriptVersion
from spws_storage import (
    WorkspaceStore,
    list_versions,
    load_manuscript,
    save_manuscript,
)
from spws_domain.ids import new_id


def test_save_parent_child_query_by_manuscript_id(spws_config, temp_workspace) -> None:
    store = WorkspaceStore(spws_config, workspace_root=temp_workspace["workspace"])
    manuscript_id = new_id("ms")
    parent = ManuscriptVersion(
        manuscript_id=manuscript_id,
        version_id=new_id("msv"),
        text="Line one of the parent draft.\nLine two stays quiet.",
        parent_version_ids=[],
        created_at=datetime.now(UTC),
        provenance_map={"role": "root"},
    )
    parent_path = save_manuscript(spws_config, parent)
    assert parent_path.is_file()

    child = ManuscriptVersion(
        manuscript_id=manuscript_id,
        version_id=new_id("msv"),
        text="Line one of the revised draft.\nLine two stays quiet.",
        parent_version_ids=[parent.version_id],
        accepted_change_ids=["accept-test"],
        created_at=datetime.now(UTC),
        provenance_map={"role": "child"},
    )
    save_manuscript(spws_config, child)

    versions = list_versions(spws_config, manuscript_id)
    ids = {v.version_id for v in versions}
    assert parent.version_id in ids
    assert child.version_id in ids
    assert len(versions) >= 2

    loaded = load_manuscript(config=spws_config, version_id=child.version_id)
    assert loaded.manuscript_id == manuscript_id
    assert loaded.parent_version_ids == [parent.version_id]
    assert "revised" in loaded.text

    # Blob exists for both digests
    assert store.blobs.exists(
        store._conn.execute(
            "SELECT content_digest FROM manuscript_versions WHERE version_id = ?",
            (parent.version_id,),
        ).fetchone()[0]
    )
    child_digest = store._conn.execute(
        "SELECT content_digest FROM manuscript_versions WHERE version_id = ?",
        (child.version_id,),
    ).fetchone()[0]
    assert store.blobs.exists(child_digest)
    store.close()


def test_child_without_parents_rejected(spws_config) -> None:
    bad = ManuscriptVersion(
        manuscript_id=new_id("ms"),
        version_id=new_id("msv"),
        text="orphan child",
        parent_version_ids=[],
        accepted_change_ids=["accept-x"],
        created_at=datetime.now(UTC),
    )
    try:
        save_manuscript(spws_config, bad)
        raised = False
    except ValueError:
        raised = True
    assert raised
