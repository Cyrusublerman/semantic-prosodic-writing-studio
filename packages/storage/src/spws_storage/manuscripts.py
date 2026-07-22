"""ManuscriptVersion persistence: BlobStore CAS + SQLite metadata (D011)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from spws_contracts_core.domain import ManuscriptVersion, RevisionDecision

from .blobs import BlobStore
from .db import ensure_schema, get_session
from .db.models import ManuscriptVersionRow, RevisionDecisionRow, WorkPlanRow


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _as_manuscript(manuscript: ManuscriptVersion | dict) -> ManuscriptVersion:
    if isinstance(manuscript, ManuscriptVersion):
        return manuscript
    return ManuscriptVersion.model_validate(manuscript)


def _sqlite_path(config: Any) -> Path:
    path = getattr(config, "sqlite_path", None)
    if path is not None:
        return Path(path)
    workspace = Path(getattr(config, "workspace_path"))
    return workspace / "studio.sqlite3"


def _objects_path(config: Any) -> Path:
    path = getattr(config, "objects_path", None)
    if path is not None:
        return Path(path)
    return Path(getattr(config, "workspace_path")) / "objects"


def save_manuscript(config: Any, manuscript: ManuscriptVersion | dict) -> Path:
    """Persist text blob via BlobStore AND SQLite row; also write JSON pointer file."""
    ms = _as_manuscript(manuscript)
    parents = [p for p in (ms.parent_version_ids or []) if p]
    # Child versions (accepted edits) MUST have non-empty parent_version_ids.
    if ms.accepted_change_ids and not parents:
        raise ValueError("child ManuscriptVersion requires non-empty parent_version_ids")

    blobs = BlobStore(_objects_path(config))
    digest, _blob_path = blobs.put_text(ms.text, media_type="text/plain")

    payload = ms.model_dump(mode="json")
    # Digest lives on the SQL row / blob pointer, not on the ManuscriptVersion contract.

    sqlite_path = _sqlite_path(config)
    ensure_schema(sqlite_path)
    session = get_session(sqlite_path)
    try:
        created = ms.created_at
        if hasattr(created, "to_datetime"):
            created_dt = created  # type: ignore[assignment]
        else:
            created_dt = created if isinstance(created, datetime) else _utc_now()
        row = session.get(ManuscriptVersionRow, ms.version_id)
        if row is None:
            row = ManuscriptVersionRow(
                version_id=ms.version_id,
                manuscript_id=ms.manuscript_id,
                content_digest=digest.value,
                parent_version_ids=parents,
                payload_json=payload,
                created_at=created_dt if isinstance(created_dt, datetime) else _utc_now(),
            )
            session.add(row)
        else:
            row.manuscript_id = ms.manuscript_id
            row.content_digest = digest.value
            row.parent_version_ids = parents
            row.payload_json = payload
            row.created_at = created_dt if isinstance(created_dt, datetime) else row.created_at
        session.commit()
    finally:
        session.close()

    # Keep JSON file for WorkspaceStore / export-path compatibility.
    root = Path(getattr(config, "manuscripts_path"))
    root.mkdir(parents=True, exist_ok=True)
    folder = root / str(ms.manuscript_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{ms.version_id}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    latest = folder / "latest.json"
    latest.write_text(
        json.dumps({"version_id": ms.version_id, "path": str(path)}, indent=2),
        encoding="utf-8",
    )
    return path


def load_manuscript(
    path: str | Path | None = None,
    *,
    config: Any | None = None,
    version_id: str | None = None,
) -> ManuscriptVersion:
    """Load by JSON path, or by version_id from SQLite when config is provided."""
    if version_id is not None:
        if config is None:
            raise ValueError("load_manuscript by version_id requires config")
        sqlite_path = _sqlite_path(config)
        ensure_schema(sqlite_path)
        session = get_session(sqlite_path)
        try:
            row = session.get(ManuscriptVersionRow, version_id)
            if row is None:
                raise KeyError(version_id)
            payload = _row_to_manuscript_payload(row, config)
            return ManuscriptVersion.model_validate_json(json.dumps(payload))
        finally:
            session.close()

    if path is None:
        raise ValueError("load_manuscript requires path or version_id")
    return ManuscriptVersion.model_validate_json(Path(path).read_text(encoding="utf-8"))


def _row_to_manuscript_payload(row: ManuscriptVersionRow, config: Any) -> dict[str, Any]:
    payload = dict(row.payload_json or {})
    payload.pop("content_digest", None)
    if not payload.get("text"):
        blobs = BlobStore(_objects_path(config))
        payload["text"] = blobs.get_bytes(row.content_digest).decode("utf-8")
    payload.setdefault("version_id", row.version_id)
    payload.setdefault("manuscript_id", row.manuscript_id)
    payload.setdefault("parent_version_ids", row.parent_version_ids or [])
    if "created_at" not in payload and row.created_at is not None:
        created = row.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        payload["created_at"] = created.isoformat().replace("+00:00", "Z")
    return payload


def list_versions(config: Any, manuscript_id: str) -> list[ManuscriptVersion]:
    """Return all ManuscriptVersion rows for manuscript_id (newest first)."""
    sqlite_path = _sqlite_path(config)
    ensure_schema(sqlite_path)
    session = get_session(sqlite_path)
    try:
        from sqlalchemy import select

        rows = session.scalars(
            select(ManuscriptVersionRow)
            .where(ManuscriptVersionRow.manuscript_id == manuscript_id)
            .order_by(ManuscriptVersionRow.created_at.desc())
        ).all()
        out: list[ManuscriptVersion] = []
        for row in rows:
            payload = _row_to_manuscript_payload(row, config)
            out.append(ManuscriptVersion.model_validate_json(json.dumps(payload)))
        return out
    finally:
        session.close()


def save_work_plan(
    config: Any,
    work_plan: dict | Any,
    *,
    manuscript_id: str | None = None,
    version_id: str | None = None,
) -> str:
    """Persist WorkPlan (or plan wrapper dict) into SQLite; return plan_id."""
    if hasattr(work_plan, "model_dump"):
        payload = work_plan.model_dump(mode="json")
        plan_id = getattr(work_plan, "plan_id", None) or payload.get("plan_id")
    elif isinstance(work_plan, dict):
        payload = dict(work_plan)
        inner = payload.get("work_plan") if isinstance(payload.get("work_plan"), dict) else None
        plan_id = payload.get("plan_id") or (inner or {}).get("plan_id")
    else:
        raise TypeError("work_plan must be dict or ContractModel")
    if not plan_id:
        raise ValueError("work_plan missing plan_id")

    text_blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    blobs = BlobStore(_objects_path(config))
    digest, _ = blobs.put_text(text_blob, media_type="application/json")

    sqlite_path = _sqlite_path(config)
    ensure_schema(sqlite_path)
    session = get_session(sqlite_path)
    try:
        row = session.get(WorkPlanRow, str(plan_id))
        if row is None:
            row = WorkPlanRow(
                plan_id=str(plan_id),
                manuscript_id=manuscript_id,
                version_id=version_id,
                content_digest=digest.value,
                parent_version_ids=[],
                payload_json=payload,
                created_at=_utc_now(),
            )
            session.add(row)
        else:
            row.manuscript_id = manuscript_id or row.manuscript_id
            row.version_id = version_id or row.version_id
            row.content_digest = digest.value
            row.payload_json = payload
        session.commit()
    finally:
        session.close()
    return str(plan_id)


def load_work_plan(config: Any, plan_id: str) -> dict[str, Any]:
    sqlite_path = _sqlite_path(config)
    ensure_schema(sqlite_path)
    session = get_session(sqlite_path)
    try:
        row = session.get(WorkPlanRow, plan_id)
        if row is None:
            raise KeyError(plan_id)
        return dict(row.payload_json or {})
    finally:
        session.close()


def save_revision_decision(
    config: Any,
    decision: RevisionDecision | dict,
    *,
    manuscript_id: str | None = None,
    version_id: str | None = None,
) -> str:
    """Persist RevisionDecision into SQLite; return decision_id."""
    if isinstance(decision, RevisionDecision):
        payload = decision.model_dump(mode="json")
        decision_id = decision.decision_id
        run_id = decision.run_id
    elif isinstance(decision, dict):
        payload = dict(decision)
        decision_id = str(payload["decision_id"])
        run_id = payload.get("run_id")
    else:
        raise TypeError("decision must be RevisionDecision or dict")

    text_blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    blobs = BlobStore(_objects_path(config))
    digest, _ = blobs.put_text(text_blob, media_type="application/json")

    sqlite_path = _sqlite_path(config)
    ensure_schema(sqlite_path)
    session = get_session(sqlite_path)
    try:
        created_raw = payload.get("decided_at")
        created_at = _utc_now()
        if isinstance(created_raw, str):
            try:
                created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            except ValueError:
                pass
        row = session.get(RevisionDecisionRow, decision_id)
        if row is None:
            row = RevisionDecisionRow(
                decision_id=decision_id,
                run_id=run_id,
                manuscript_id=manuscript_id,
                version_id=version_id,
                content_digest=digest.value,
                parent_version_ids=[],
                payload_json=payload,
                created_at=created_at,
            )
            session.add(row)
        else:
            row.run_id = run_id
            row.manuscript_id = manuscript_id or row.manuscript_id
            row.version_id = version_id or row.version_id
            row.content_digest = digest.value
            row.payload_json = payload
        session.commit()
    finally:
        session.close()

    # Mirror JSON export for D014 compatibility.
    decisions_path = Path(getattr(config, "workspace_path", _sqlite_path(config).parent)) / "decisions"
    decisions_path.mkdir(parents=True, exist_ok=True)
    (decisions_path / f"{decision_id}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return decision_id
