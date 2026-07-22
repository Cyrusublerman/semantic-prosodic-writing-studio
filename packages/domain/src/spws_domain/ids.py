"""Short prefixed identifiers."""

from __future__ import annotations

from uuid import uuid4


def new_id(prefix: str) -> str:
    """Return ``{prefix}_{12-hex}`` from uuid4."""
    clean = prefix.strip().rstrip("_")
    if not clean:
        raise ValueError("prefix must be non-empty")
    return f"{clean}_{uuid4().hex[:12]}"
