"""Parse PKL markdown frontmatter as data only — never executable."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from spws_contracts_core.domain import PKLRelationship

from .. import frontmatter_lite as frontmatter
from ..policy import parse_privacy, parse_rights


@dataclass(frozen=True, slots=True)
class ParsedPKL:
    uid: str
    title: str
    object_type: str | None
    rights: str
    privacy: str
    body: str
    metadata: dict[str, Any]
    relationships: list[PKLRelationship] = field(default_factory=list)
    source_id: str | None = None


def resolve_identity(metadata: dict[str, Any]) -> str:
    uid = metadata.get("uid")
    if uid:
        return str(uid)
    legacy_id = metadata.get("id")
    if legacy_id:
        return str(legacy_id)
    raise ValueError("PKL document requires uid or id in frontmatter")


def _parse_relationships(raw: object | None) -> list[PKLRelationship]:
    if not raw:
        return []
    items: list[Any]
    if isinstance(raw, list):
        items = raw
    else:
        items = [raw]
    relationships: list[PKLRelationship] = []
    for item in items:
        if isinstance(item, PKLRelationship):
            relationships.append(item)
        elif isinstance(item, dict):
            relationships.append(PKLRelationship.model_validate(item))
        elif isinstance(item, str):
            relationships.append(PKLRelationship(type="related", target=item))
    return relationships


def parse_pkl_text(text: str) -> ParsedPKL:
    """Parse markdown with YAML frontmatter. Content is treated as plain text."""
    post = frontmatter.loads(text)
    metadata = dict(post.metadata or {})
    uid = resolve_identity(metadata)
    title = str(metadata.get("title") or uid)
    object_type = metadata.get("object_type")
    if object_type is not None:
        object_type = str(object_type)
    rights = parse_rights(metadata.get("rights"))
    privacy = parse_privacy(metadata.get("privacy"))
    relationships = _parse_relationships(metadata.get("relationships"))
    source_id = metadata.get("id")
    return ParsedPKL(
        uid=uid,
        title=title,
        object_type=object_type,
        rights=rights.value,
        privacy=privacy.value,
        body=post.content or "",
        metadata=metadata,
        relationships=relationships,
        source_id=str(source_id) if source_id else None,
    )


def parse_pkl_bytes(data: bytes) -> ParsedPKL:
    return parse_pkl_text(data.decode("utf-8"))
