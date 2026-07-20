"""Convenience facade used by the SPWS CLI and vertical-slice demos."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from spws_contracts_core.domain import PKLPromotionBundle, PKLQuery, PKLResult, ReadMode

from .config import SpwsConfig, load_config
from .indexer.indexer import IndexManifest, PKLIndexer
from .promotion.promotion import PromotionExporter
from .retriever.retriever import PKLRetriever
from .snapshot.snapshot import SnapshotReader


def _config_with(
    *,
    repository_path: Path | None = None,
    cache_path: Path | None = None,
    promotions_path: Path | None = None,
    read_mode: str | None = None,
) -> SpwsConfig:
    base = load_config()
    pkl = base.pkl
    runtime = base.runtime
    if repository_path is not None:
        pkl = replace(pkl, repository_path=repository_path.resolve())
    if cache_path is not None:
        pkl = replace(pkl, cache_path=cache_path.resolve())
    if read_mode is not None:
        pkl = replace(pkl, read_mode=read_mode)
    if promotions_path is not None:
        runtime = replace(runtime, promotions_path=promotions_path.resolve())
    return replace(base, pkl=pkl, runtime=runtime)


def index_repository(
    source: Path,
    *,
    commit: str | None = None,
    cache_path: Path | None = None,
) -> dict[str, Any]:
    """Index a git repository or a fixture directory into the runtime cache."""
    source = source.resolve()
    is_git = (source / ".git").exists()
    read_mode = "snapshot" if is_git and commit else ("working_tree" if is_git else "filesystem")
    config = _config_with(
        repository_path=source,
        cache_path=cache_path,
        read_mode=read_mode,
    )
    indexer = PKLIndexer(config)
    if commit and is_git:
        # Force snapshot at commit by temporarily adjusting reader via config
        config = _config_with(
            repository_path=source,
            cache_path=cache_path,
            read_mode="snapshot",
        )
        indexer = PKLIndexer(config)
        reader = SnapshotReader(source, read_mode=ReadMode.SNAPSHOT, commit=commit)
        # Rebuild using explicit commit through a patched reader
        indexer._reader = lambda commit_arg=None: SnapshotReader(  # type: ignore[method-assign]
            source,
            read_mode=ReadMode.SNAPSHOT,
            commit=commit or commit_arg,
        )
        _ = reader
    manifest: IndexManifest = indexer.build_full()
    return {
        "schema_version": manifest.schema_version,
        "repo_identity": manifest.repo_identity,
        "commit_sha": manifest.commit_sha,
        "read_mode": manifest.read_mode,
        "built_at": manifest.built_at,
        "record_count": manifest.record_count,
        "excluded_count": manifest.excluded_count,
    }


def query_index(query: PKLQuery, cache_path: Path | None = None) -> list[PKLResult]:
    config = _config_with(cache_path=cache_path)
    return PKLRetriever(config).query(query)


def export_bundle(bundle: PKLPromotionBundle, promotions_path: Path | None = None) -> Path:
    config = _config_with(promotions_path=promotions_path)
    return PromotionExporter(config).export_bundle(bundle)


def validate_bundle(bundle: PKLPromotionBundle | Path | dict[str, Any]) -> PKLPromotionBundle:
    # ContractModel is strict for Python objects; JSON wire uses model_validate_json.
    if isinstance(bundle, Path):
        path = bundle
        if path.is_dir():
            path = path / "bundle.json"
        model = PKLPromotionBundle.model_validate_json(path.read_text(encoding="utf-8"))
    elif isinstance(bundle, dict):
        model = PKLPromotionBundle.model_validate_json(json.dumps(bundle))
    else:
        model = bundle
    config = load_config()
    return PromotionExporter(config).validate_bundle(model)
