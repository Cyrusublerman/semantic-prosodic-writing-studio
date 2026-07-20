"""Minimal YAML-frontmatter parser (stdlib + PyYAML). Avoids python-frontmatter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class Post:
    metadata: dict[str, Any]
    content: str


def loads(text: str) -> Post:
    if not text.startswith("---"):
        return Post(metadata={}, content=text)
    parts = text.split("---", 2)
    if len(parts) < 3:
        return Post(metadata={}, content=text)
    meta_raw = parts[1]
    body = parts[2].lstrip("\n")
    metadata = yaml.safe_load(meta_raw) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return Post(metadata=metadata, content=body)
