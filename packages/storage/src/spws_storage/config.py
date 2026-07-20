from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass(frozen=True)
class SpwsConfig:
    repository_path: Path
    read_mode: str
    write_mode: str
    pkl_cache_path: Path
    data_root: Path
    workspace_path: Path
    manuscripts_path: Path
    runs_path: Path
    models_path: Path
    promotions_path: Path
    wordrare_storage_path: Path
    wordrare_database_filename: str
    fail_closed_on_unknown_rights: bool
    fail_closed_on_unknown_privacy: bool
    allow_working_tree_reads: bool
    allow_remote_git: bool

    @property
    def sqlite_path(self) -> Path:
        return self.workspace_path / "studio.sqlite3"

    @property
    def objects_path(self) -> Path:
        return self.workspace_path / "objects"

    @property
    def decisions_path(self) -> Path:
        return self.workspace_path / "decisions"


def _expand(path_text: str) -> Path:
    return Path(path_text).expanduser().resolve()


def _resolve_repo_path(config_dir: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate.resolve()
    return (config_dir / candidate).resolve()


def load_config(config_path: Path | None = None) -> SpwsConfig:
    root = Path(__file__).resolve().parents[4]
    env_path = os.environ.get("SPWS_CONFIG")
    path = config_path or (Path(env_path) if env_path else (root / "config" / "spws.toml"))
    with path.open("rb") as handle:
        data = tomllib.load(handle)

    pkl = data["pkl"]
    runtime = data["runtime"]
    wordrare = data["wordrare"]
    policy = data["policy"]
    return SpwsConfig(
        repository_path=_resolve_repo_path(path.parent, pkl["repository_path"]),
        read_mode=pkl["read_mode"],
        write_mode=pkl["write_mode"],
        pkl_cache_path=_expand(pkl["cache_path"]),
        data_root=_expand(runtime["data_root"]),
        workspace_path=_expand(runtime["workspace_path"]),
        manuscripts_path=_expand(runtime["manuscripts_path"]),
        runs_path=_expand(runtime["runs_path"]),
        models_path=_expand(runtime["models_path"]),
        promotions_path=_expand(runtime["promotions_path"]),
        wordrare_storage_path=_expand(wordrare["storage_path"]),
        wordrare_database_filename=wordrare["database_filename"],
        fail_closed_on_unknown_rights=policy["fail_closed_on_unknown_rights"],
        fail_closed_on_unknown_privacy=policy["fail_closed_on_unknown_privacy"],
        allow_working_tree_reads=policy["allow_working_tree_reads"],
        allow_remote_git=policy["allow_remote_git"],
    )
