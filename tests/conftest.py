"""
Pytest configuration and fixtures for SPWS runtime packages.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

PACKAGE_SRC_DIRS = [
    ROOT / "packages" / "contracts" / "core" / "src",
    ROOT / "packages" / "storage" / "src",
    ROOT / "packages" / "ingestion" / "src",
    ROOT / "packages" / "analysis" / "src",
    ROOT / "packages" / "revision" / "src",
    ROOT / "packages" / "adapters" / "pkl" / "src",
    ROOT / "packages" / "spws_cli" / "src",
    ROOT / "packages" / "wordrare" / "src",
]

for path in PACKAGE_SRC_DIRS:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


@pytest.fixture(scope="session")
def project_root() -> Path:
    return ROOT


@pytest.fixture
def temp_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "spws-workspace"
    cache = tmp_path / "pkl-cache"
    promotions = tmp_path / "promotions"
    for path in (workspace, cache, promotions):
        path.mkdir(parents=True)

    config_path = tmp_path / "spws.toml"
    config_path.write_text(
        f"""
[pkl]
repository_path = "{(ROOT / 'fixtures' / 'pkl').as_posix()}"
read_mode = "snapshot"
write_mode = "promotion_only"
cache_path = "{cache.as_posix()}"

[runtime]
data_root = "{workspace.as_posix()}"
workspace_path = "{workspace.as_posix()}"
manuscripts_path = "{(workspace / 'manuscripts').as_posix()}"
runs_path = "{(workspace / 'runs').as_posix()}"
models_path = "{(workspace / 'models').as_posix()}"
promotions_path = "{promotions.as_posix()}"

[wordrare]
storage_path = "{(workspace / 'wordrare').as_posix()}"
database_filename = "wordrare.db"

[embeddings]
enabled = false
model_id = "sentence-transformers/all-MiniLM-L6-v2"
model_version = "unspecified"
require_lexical_gate = true

[policy]
fail_closed_on_unknown_rights = true
fail_closed_on_unknown_privacy = true
allow_working_tree_reads = true
allow_remote_git = false
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("SPWS_CONFIG", str(config_path))
    return {"workspace": workspace, "cache": cache, "promotions": promotions, "config_path": config_path}


@pytest.fixture
def spws_config(temp_workspace):
    from spws_storage import load_config

    return load_config(temp_workspace["config_path"])
