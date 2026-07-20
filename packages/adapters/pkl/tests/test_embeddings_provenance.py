"""Embeddings retain model identity, source object, commit, digest, and offsets."""

from __future__ import annotations

from dataclasses import replace

from spws_contracts_core.domain import PrivacyState, RightsState
from spws_pkl_adapter.config import EmbeddingSettings
from spws_pkl_adapter.embeddings import EmbeddingChunk, EmbeddingStore
from spws_pkl_adapter.policy import allows_embeddings


def test_embedding_chunks_store_provenance(spws_config, indexer):
    indexer.build_full()
    config = replace(
        spws_config,
        embeddings=EmbeddingSettings(
            enabled=True,
            model_id="hash-fallback-test",
            model_version="0.0.1",
            require_lexical_gate=False,
        ),
    )
    store = EmbeddingStore(
        config.index_root / "embeddings",
        model_id=config.embeddings.model_id,
        model_version=config.embeddings.model_version,
    )
    chunk = EmbeddingChunk(
        uid="uid-alpha",
        commit_sha="deadbeef",
        content_digest="a" * 64,
        start_char=0,
        end_char=12,
        text="Alpha body",
    )
    store.store_chunks(
        uid="uid-alpha",
        commit_sha="deadbeef",
        content_digest="a" * 64,
        chunks=[(chunk, [0.0, 1.0, 0.0, 1.0])],
    )
    conn = store._connect()
    row = conn.execute("SELECT * FROM chunks WHERE uid = ?", ("uid-alpha",)).fetchone()
    conn.close()
    assert row is not None
    assert row["model_id"] == "hash-fallback-test"
    assert row["model_version"] == "0.0.1"
    assert row["commit_sha"] == "deadbeef"
    assert row["content_digest"] == "a" * 64
    assert row["start_char"] == 0
    assert row["end_char"] == 12


def test_private_material_blocked_from_embeddings(spws_config):
    decision = allows_embeddings(
        RightsState.PRIVATE,
        PrivacyState.PRIVATE,
        spws_config.policy,
    )
    assert decision.allowed is False
