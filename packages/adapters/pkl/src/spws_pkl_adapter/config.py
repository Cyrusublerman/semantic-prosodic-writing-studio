"""Load SPWS configuration from config/spws.toml with path expansion."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


def expand_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def xdg_cache_home() -> Path:
    return expand_path(os.environ.get("XDG_CACHE_HOME", "~/.cache"))


def find_config_path(start: Path | None = None) -> Path:
    override = os.environ.get("SPWS_CONFIG")
    if override:
        path = expand_path(override)
        if not path.is_file():
            raise FileNotFoundError(f"SPWS_CONFIG not found: {path}")
        return path

    cursor = (start or Path.cwd()).resolve()
    for candidate in [cursor, *cursor.parents]:
        config_file = candidate / "config" / "spws.toml"
        if config_file.is_file():
            return config_file
    raise FileNotFoundError("config/spws.toml not found; set SPWS_CONFIG")


@dataclass(frozen=True, slots=True)
class PklSettings:
    repository_path: Path
    read_mode: str
    write_mode: str
    cache_path: Path


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    data_root: Path
    workspace_path: Path
    manuscripts_path: Path
    runs_path: Path
    models_path: Path
    promotions_path: Path


@dataclass(frozen=True, slots=True)
class EmbeddingSettings:
    enabled: bool
    model_id: str
    model_version: str
    require_lexical_gate: bool
    debug_hash_embeddings: bool = False


@dataclass(frozen=True, slots=True)
class PolicySettings:
    fail_closed_on_unknown_rights: bool
    fail_closed_on_unknown_privacy: bool
    allow_working_tree_reads: bool
    allow_remote_git: bool


@dataclass(frozen=True, slots=True)
class SpwsConfig:
    config_path: Path
    monorepo_root: Path
    pkl: PklSettings
    runtime: RuntimeSettings
    embeddings: EmbeddingSettings
    policy: PolicySettings

    @property
    def index_root(self) -> Path:
        return self.pkl.cache_path

    @property
    def git_mirror_cache(self) -> Path:
        return xdg_cache_home() / "spws" / "pkl-git-mirrors"


def load_config(config_path: Path | None = None) -> SpwsConfig:
    path = expand_path(config_path) if config_path else find_config_path()
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    monorepo_root = path.parent.parent

    pkl_raw = raw.get("pkl", {})
    runtime_raw = raw.get("runtime", {})
    embeddings_raw = raw.get("embeddings", {})
    policy_raw = raw.get("policy", {})

    repo_path = pkl_raw.get("repository_path", "../Library")
    repo = expand_path(repo_path) if Path(repo_path).is_absolute() else expand_path(monorepo_root / repo_path)

    return SpwsConfig(
        config_path=path,
        monorepo_root=monorepo_root,
        pkl=PklSettings(
            repository_path=repo,
            read_mode=str(pkl_raw.get("read_mode", "snapshot")),
            write_mode=str(pkl_raw.get("write_mode", "promotion_only")),
            cache_path=expand_path(pkl_raw.get("cache_path", "~/.local/share/spws/pkl-index")),
        ),
        runtime=RuntimeSettings(
            data_root=expand_path(runtime_raw.get("data_root", "~/.local/share/spws")),
            workspace_path=expand_path(runtime_raw.get("workspace_path", "~/.local/share/spws/workspace")),
            manuscripts_path=expand_path(runtime_raw.get("manuscripts_path", "~/.local/share/spws/manuscripts")),
            runs_path=expand_path(runtime_raw.get("runs_path", "~/.local/share/spws/runs")),
            models_path=expand_path(runtime_raw.get("models_path", "~/.local/share/spws/models")),
            promotions_path=expand_path(runtime_raw.get("promotions_path", "~/.local/share/spws/promotions")),
        ),
        embeddings=EmbeddingSettings(
            enabled=bool(embeddings_raw.get("enabled", False)),
            model_id=str(embeddings_raw.get("model_id", "sentence-transformers/all-MiniLM-L6-v2")),
            model_version=str(embeddings_raw.get("model_version", "unspecified")),
            require_lexical_gate=bool(embeddings_raw.get("require_lexical_gate", True)),
            debug_hash_embeddings=bool(embeddings_raw.get("debug_hash_embeddings", False)),
        ),
        policy=PolicySettings(
            fail_closed_on_unknown_rights=bool(policy_raw.get("fail_closed_on_unknown_rights", True)),
            fail_closed_on_unknown_privacy=bool(policy_raw.get("fail_closed_on_unknown_privacy", True)),
            allow_working_tree_reads=bool(policy_raw.get("allow_working_tree_reads", True)),
            allow_remote_git=bool(policy_raw.get("allow_remote_git", False)),
        ),
    )
