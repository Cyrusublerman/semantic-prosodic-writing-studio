"""Adapter behaviour against a pinned local Library snapshot when available."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from spws_contracts_core.domain import PKLQuery
from spws_pkl_adapter import index_repository, query_index


@pytest.mark.pinned_snapshot
def test_index_pinned_library_snapshot(tmp_path: Path):
    library = Path(os.environ.get("PKL_LIBRARY_PATH", Path.home() / "Projects/pkl-system/Library"))
    if not library.is_dir() or not (library / ".git").exists():
        pytest.skip("Library checkout not available")

    sha = subprocess.check_output(
        ["git", "-C", str(library), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    cache = tmp_path / "pkl-index"
    manifest = index_repository(library, commit=sha, cache_path=cache)
    assert manifest["commit_sha"] == sha
    assert manifest["record_count"] > 0

    hits = query_index(PKLQuery(text="writing", result_limit=5), cache)
    # Policy may filter many private objects; zero hits is acceptable if all excluded.
    assert isinstance(hits, list)
    for hit in hits:
        assert hit.commit == sha
        assert hit.object_uid
        assert hit.digest.value
        assert hit.reproducible is True
