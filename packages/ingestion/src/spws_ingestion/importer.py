from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import frontmatter

from spws_contracts_core import InputPackage
from spws_contracts_core.domain import PrivacyState, RightsState


def _utc_now() -> datetime:
    return datetime.now(UTC)


def import_text(
    text: str,
    *,
    source_label: str | None = None,
    media_type: str = "text/plain",
    rights: RightsState = RightsState.UNKNOWN,
    privacy: PrivacyState = PrivacyState.UNKNOWN,
    user_metadata: dict | None = None,
) -> InputPackage:
    return InputPackage(
        package_id=f"inp-{uuid4().hex[:12]}",
        media_type=media_type,
        text=text,
        source_label=source_label,
        captured_at=_utc_now(),
        rights=rights,
        privacy=privacy,
        user_metadata=user_metadata or {},
    )


def _enum_value(enum_cls, raw, default):
    try:
        return enum_cls(str(raw))
    except ValueError:
        return default


def import_markdown(path: Path) -> InputPackage:
    raw = path.read_text(encoding="utf-8")
    post = frontmatter.loads(raw)
    body = post.content.strip()
    metadata = dict(post.metadata)
    title = metadata.get("title")
    label = title or path.name
    return InputPackage(
        package_id=f"inp-{uuid4().hex[:12]}",
        media_type="text/markdown",
        text=body,
        source_label=str(path),
        captured_at=_utc_now(),
        rights=_enum_value(RightsState, metadata.get("rights", RightsState.UNKNOWN.value), RightsState.UNKNOWN),
        privacy=_enum_value(PrivacyState, metadata.get("privacy", PrivacyState.UNKNOWN.value), PrivacyState.UNKNOWN),
        user_metadata={"frontmatter": metadata, "path": str(path)},
    )


def import_file(path: Path) -> InputPackage:
    path = path.resolve()
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return import_markdown(path)
    text = path.read_text(encoding="utf-8")
    return import_text(text, source_label=str(path), media_type="text/plain")
