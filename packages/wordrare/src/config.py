"""
Configuration management for WordRare.

Runtime databases, raw data, models, and logs live under XDG data dirs
outside both the SPWS and Library Git repositories.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _expand(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _xdg_data_home() -> Path:
    return _expand(os.environ.get("XDG_DATA_HOME", "~/.local/share"))


def _spws_wordrare_root() -> Path:
    override = os.environ.get("WORDRARE_STORAGE_PATH")
    if override:
        return _expand(override)
    return _xdg_data_home() / "spws" / "wordrare"


# Package-local read-only assets (form JSON specs) remain in the package.
PACKAGE_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = PACKAGE_DIR.parent  # packages/wordrare
FORMS_DIR = PACKAGE_ROOT / "data" / "forms"

# External runtime storage
STORAGE_ROOT = _spws_wordrare_root()
RAW_DATA_DIR = STORAGE_ROOT / "raw"
PROCESSED_DATA_DIR = STORAGE_ROOT / "processed"
DATABASE_DIR = STORAGE_ROOT / "databases"
LOGS_DIR = STORAGE_ROOT / "logs"
MODELS_DIR = _xdg_data_home() / "spws" / "models"

# Backward-compatible aliases used by existing modules
BASE_DIR = PACKAGE_ROOT
DATA_DIR = STORAGE_ROOT
REPORTS_DIR = STORAGE_ROOT / "reports"

for directory in [
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    DATABASE_DIR,
    LOGS_DIR,
    MODELS_DIR,
    REPORTS_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

# API Keys
WORDNIK_API_KEY = os.getenv("WORDNIK_API_KEY", "")
OXFORD_API_KEY = os.getenv("OXFORD_API_KEY", "")
MERRIAM_WEBSTER_API_KEY = os.getenv("MERRIAM_WEBSTER_API_KEY", "")

# Database
_default_db = DATABASE_DIR / "wordrare.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_default_db}")

# Data sources
PHRONTISTERY_URL = os.getenv("PHRONTISTERY_URL", "http://phrontistery.info/")
CMU_DICT_PATH = RAW_DATA_DIR / "cmudict-0.7b"
NGRAM_DATA_PATH = RAW_DATA_DIR / "ngrams"

# Embedding model (weights cached under MODELS_DIR / HF cache)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Generation defaults
DEFAULT_RARITY_BIAS = float(os.getenv("DEFAULT_RARITY_BIAS", "0.5"))
DEFAULT_FORM = os.getenv("DEFAULT_FORM", "sonnet")
MAX_REPAIR_ITERATIONS = int(os.getenv("MAX_REPAIR_ITERATIONS", "5"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "wordrare.log"

DEFAULT_CONSTRAINT_WEIGHTS = {
    "rhyme": 0.25,
    "meter": 0.25,
    "semantics": 0.20,
    "affect": 0.15,
    "coherence": 0.10,
    "style": 0.05,
}

DEFAULT_METRIC_WEIGHTS = {
    "R_rhyme": 0.20,
    "R_meter": 0.20,
    "R_semantic": 0.25,
    "R_depth": 0.15,
    "R_layers": 0.10,
    "R_variation": 0.10,
}
