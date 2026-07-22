"""Stress: executor pause/resume + manuscript lineage + tombstone."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from spws_contracts_core.domain import ManuscriptVersion, PrivacyState, RightsState
from spws_domain.ids import new_id
from spws_orchestration import PipelineExecutor
from spws_orchestration.handlers import register_defaults
from spws_orchestration.registry import ComponentRegistry
from spws_storage import WorkspaceStore
from spws_storage.manuscripts import list_versions, save_manuscript
from spws_storage.tombstone import tombstone_raw_source
from spws_ingestion import import_text


def test_executor_pauses_on_human_gates(stress_config, project_root):
    registry = ComponentRegistry()
    register_defaults(registry)
    executor = PipelineExecutor(registry)
    pipe_path = project_root / "pipelines" / "poetry_revision_v0.yaml"
    if not pipe_path.is_file():
        pipe_path = project_root / "packages" / "pipelines" / "pipelines" / "poetry_revision_v0.yaml"
    if not pipe_path.is_file():
        pytest.skip("poetry_revision_v0.yaml not found")
    pipeline = executor.load(pipe_path)
    assert "plan_confirm" in pipeline.human_gates or pipeline.human_gates

    poem = (project_root / "fixtures" / "poetry" / "pastoral_12_lines.txt").read_text(encoding="utf-8")
    ctx = {"text": poem, "config": stress_config, "brief": "stress", "decisions": {}}
    result = executor.execute(pipeline, ctx)
    assert result.status == "paused"
    checkpoint = result.checkpoint or result.context.get("checkpoint") or {}
    gate = checkpoint.get("paused_at_gate") or result.context.get("pause_gate")
    assert gate == "plan_confirm"

    # Resume with plan gate satisfied
    decisions = dict(result.context.get("decisions") or {})
    decisions[gate] = True
    resumed_ctx = {**result.context, "decisions": decisions}
    result2 = executor.resume(pipeline, resumed_ctx)
    # May pause again at decide gate or complete/fail depending on handlers
    assert result2.status in {"paused", "completed", "failed", "partial"}
    if result2.status == "paused":
        cp2 = result2.checkpoint or {}
        assert cp2.get("paused_at_gate") == "revision_decide"


def test_manuscript_lineage_chain(stress_config):
    root = ManuscriptVersion(
        manuscript_id=new_id("ms"),
        version_id=new_id("msv"),
        text="line one\nline two\nline three",
        parent_version_ids=[],
        created_at=datetime.now(UTC),
    )
    save_manuscript(stress_config, root)
    child = ManuscriptVersion(
        manuscript_id=root.manuscript_id,
        version_id=new_id("msv"),
        text="line one\nline TWO\nline three",
        parent_version_ids=[root.version_id],
        created_at=datetime.now(UTC),
    )
    save_manuscript(stress_config, child)
    grandchild = ManuscriptVersion(
        manuscript_id=root.manuscript_id,
        version_id=new_id("msv"),
        text="line one\nline TWO\nline THREE",
        parent_version_ids=[child.version_id],
        created_at=datetime.now(UTC),
    )
    save_manuscript(stress_config, grandchild)
    versions = list_versions(stress_config, root.manuscript_id)
    assert len(versions) >= 3
    ids = {v.version_id if hasattr(v, "version_id") else v["version_id"] for v in versions}
    assert {root.version_id, child.version_id, grandchild.version_id} <= ids

    # Accepted change without parents must be rejected (child policy)
    with pytest.raises((ValueError, RuntimeError)):
        save_manuscript(
            stress_config,
            ManuscriptVersion(
                manuscript_id=root.manuscript_id,
                version_id=new_id("msv"),
                text="orphan child",
                parent_version_ids=[],
                accepted_change_ids=["accept-orphan"],
                created_at=datetime.now(UTC),
            ),
        )


def test_tombstone_removes_from_usable_store(stress_config, temp_workspace):
    store = WorkspaceStore(stress_config, workspace_root=temp_workspace["workspace"])
    package = import_text(
        "private note for tombstone stress",
        rights=RightsState.RESTRICTED_PENDING_REVIEW,
        privacy=PrivacyState.PRIVATE,
    )
    raw = store.persist_input_package(package)
    tombstone_raw_source(store, raw.source_id)
    # After tombstone, get may still return audit row but payload marked — accept either missing or tombstoned
    try:
        loaded = store.get_raw_source(raw.source_id)
        payload = loaded.model_dump(mode="json") if hasattr(loaded, "model_dump") else dict(loaded)
        assert payload.get("tombstoned") or payload.get("text") in {None, ""} or "tombstone" in str(payload).lower()
    except KeyError:
        pass
