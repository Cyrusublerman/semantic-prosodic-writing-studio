from __future__ import annotations

import subprocess
import textwrap
from datetime import UTC, datetime
from pathlib import Path

import pytest

from spws_contracts_core.digests import digest_text
from spws_contracts_core.domain import (
    PKLPromotionBundle,
    PromotionOperation,
    ProvenanceStamp,
    RightsState,
    PrivacyState,
)
from spws_pkl_adapter.config import SpwsConfig, load_config
from spws_pkl_adapter.indexer.indexer import PKLIndexer


def _write_library_doc(path: Path, *, uid: str, legacy_id: str | None = None, title: str, body: str, rights: str = "public", privacy: str = "public", object_type: str = "note") -> None:
    id_line = f'id: "{legacy_id}"\n' if legacy_id else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        textwrap.dedent(
            f"""\
            ---
            uid: "{uid}"
            {id_line}title: "{title}"
            object_type: "{object_type}"
            rights: {rights}
            privacy: {privacy}
            ---

            {body}
            """
        ),
        encoding="utf-8",
    )


@pytest.fixture
def temp_library(tmp_path: Path) -> Path:
    root = tmp_path / "Library"
    _write_library_doc(root / "alpha.md", uid="uid-alpha", title="Alpha", body="Alpha body about rivers.")
    _write_library_doc(root / "nested" / "beta.md", uid="uid-beta", legacy_id="legacy-beta", title="Beta", body="Beta body about mountains.")
    _write_library_doc(
        root / "secret.md",
        uid="uid-secret",
        title="Secret",
        body="Hidden content.",
        rights="unknown",
        privacy="unknown",
    )
    return root


@pytest.fixture
def git_library(temp_library: Path) -> Path:
    subprocess.run(["git", "init"], cwd=temp_library, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_library, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=temp_library, check=True)
    subprocess.run(["git", "add", "."], cwd=temp_library, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=temp_library, check=True)
    return temp_library


@pytest.fixture
def spws_config(tmp_path: Path, git_library: Path) -> SpwsConfig:
    config_path = tmp_path / "spws.toml"
    index_path = tmp_path / "pkl-index"
    promotions_path = tmp_path / "promotions"
    config_path.write_text(
        textwrap.dedent(
            f"""\
            [pkl]
            repository_path = "{git_library}"
            read_mode = "snapshot"
            write_mode = "promotion_only"
            cache_path = "{index_path}"

            [runtime]
            data_root = "{tmp_path / 'data'}"
            workspace_path = "{tmp_path / 'workspace'}"
            manuscripts_path = "{tmp_path / 'manuscripts'}"
            runs_path = "{tmp_path / 'runs'}"
            models_path = "{tmp_path / 'models'}"
            promotions_path = "{promotions_path}"

            [embeddings]
            enabled = false
            model_id = "test-model"
            model_version = "0"
            require_lexical_gate = true

            [policy]
            fail_closed_on_unknown_rights = true
            fail_closed_on_unknown_privacy = true
            allow_working_tree_reads = true
            allow_remote_git = false
            """
        ),
        encoding="utf-8",
    )
    return load_config(config_path)


@pytest.fixture
def indexer(spws_config: SpwsConfig) -> PKLIndexer:
    return PKLIndexer(spws_config)


@pytest.fixture
def promotion_bundle(spws_config: SpwsConfig) -> PKLPromotionBundle:
    now = datetime.now(tz=UTC)
    provenance = ProvenanceStamp(
        repository_identity=str(spws_config.pkl.repository_path),
        commit_sha="deadbeef",
        object_uid="uid-alpha",
        relative_path="alpha.md",
        content_digest=digest_text("Alpha body about rivers."),
        extracted_at=now,
        rights=RightsState.PUBLIC,
        privacy=PrivacyState.PUBLIC,
    )
    return PKLPromotionBundle(
        bundle_id="bundle-test-001",
        operation=PromotionOperation.UPDATE,
        target_uid="uid-alpha",
        proposed_content={"title": "Alpha revised", "body": "Updated alpha body."},
        originating_run_id="run-test",
        provenance=provenance,
        confidence=0.8,
        rights_assessment=RightsState.PUBLIC,
        privacy_assessment=PrivacyState.PUBLIC,
        created_at=now,
    )
