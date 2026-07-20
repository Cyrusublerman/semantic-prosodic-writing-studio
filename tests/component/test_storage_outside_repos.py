from __future__ import annotations

from datetime import UTC, datetime

from spws_contracts_core import InputPackage
from spws_storage import WorkspaceStore


def test_workspace_outside_git_repo(spws_config, temp_workspace, project_root):
    store = WorkspaceStore(spws_config, workspace_root=temp_workspace["workspace"])
    assert not store.workspace_inside_repo(project_root)
    assert store.config.workspace_path.resolve() == temp_workspace["workspace"].resolve()
    assert (temp_workspace["workspace"] / "objects").exists()
    assert (temp_workspace["workspace"] / "studio.sqlite3").exists()

    package = InputPackage(
        package_id="inp-outside",
        text="stored outside git",
        captured_at=datetime.now(UTC),
    )
    raw = store.persist_input_package(package)
    blob_path = store.config.objects_path / raw.content_digest.value[:2] / raw.content_digest.value[2:]
    assert blob_path.exists()
    assert project_root not in blob_path.parents
    store.close()
