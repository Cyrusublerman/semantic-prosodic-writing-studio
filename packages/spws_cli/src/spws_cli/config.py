from __future__ import annotations

from pathlib import Path

from spws_storage import load_config


def project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def load_spws_config(config_path: Path | None = None):
    if config_path is None:
        config_path = project_root() / "config" / "spws.toml"
    return load_config(config_path)
