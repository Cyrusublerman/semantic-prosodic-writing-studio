"""D006: tombstone retained raw sources while keeping audit rows."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


_TOMBSTONE_KEYS = frozenset({"tombstoned", "tombstoned_at", "blob_removed"})


def tombstone_raw_source(
    store: Any,
    source_id: str,
    *,
    remove_blob: bool = True,
) -> dict[str, Any]:
    """Mark a raw source tombstoned: clear text, optionally delete blob, keep audit row.

    The SQLite ``raw_sources`` row remains so provenance/audit can still resolve the id.
    """
    row = store._conn.execute(
        "SELECT payload_json, storage_location, content_digest FROM raw_sources WHERE source_id = ?",
        (source_id,),
    ).fetchone()
    if row is None:
        raise KeyError(source_id)

    raw = row["payload_json"]
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    payload = json.loads(raw) if isinstance(raw, str) else dict(raw)

    blob_removed = False
    if remove_blob:
        locations: list[Path] = []
        loc = row["storage_location"] or payload.get("storage_location")
        if loc:
            locations.append(Path(loc))
        digest = row["content_digest"]
        if not digest:
            digest_obj = payload.get("content_digest") or {}
            digest = digest_obj.get("value") if isinstance(digest_obj, dict) else None
        if digest and hasattr(store, "blobs"):
            locations.append(store.blobs._object_path(str(digest)))
        for path in locations:
            try:
                if path.is_file():
                    path.unlink()
                    blob_removed = True
            except OSError:
                pass

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload["text"] = None
    payload["tombstoned"] = True
    payload["tombstoned_at"] = now
    payload["blob_removed"] = blob_removed

    store._conn.execute(
        "UPDATE raw_sources SET payload_json = ? WHERE source_id = ?",
        (json.dumps(payload), source_id),
    )
    store._conn.commit()
    return {
        "source_id": source_id,
        "tombstoned": True,
        "tombstoned_at": now,
        "blob_removed": blob_removed,
        "payload": payload,
    }


def strip_tombstone_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove tombstone-only keys so remaining fields validate as RawSource."""
    return {k: v for k, v in payload.items() if k not in _TOMBSTONE_KEYS}
