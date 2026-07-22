"""SPWS workspace storage outside version control."""

from .config import SpwsConfig, load_config
from .manuscripts import (
    list_versions,
    load_manuscript,
    load_work_plan,
    save_manuscript,
    save_revision_decision,
    save_work_plan,
)
from .tombstone import tombstone_raw_source
from .workspace import WorkspaceStore

__all__ = [
    "SpwsConfig",
    "WorkspaceStore",
    "list_versions",
    "load_config",
    "load_manuscript",
    "load_work_plan",
    "save_manuscript",
    "save_revision_decision",
    "save_work_plan",
    "tombstone_raw_source",
]
