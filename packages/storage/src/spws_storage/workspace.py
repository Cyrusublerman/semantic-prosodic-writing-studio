from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from spws_contracts_core import InputPackage, RawSource, RunManifest, RevisionDecision

from .blobs import BlobStore
from dataclasses import replace

from .config import SpwsConfig, load_config
from .db import ensure_schema
from .manuscripts import save_revision_decision as persist_revision_decision


def _utc_now() -> datetime:
    return datetime.now(UTC)


class WorkspaceStore:
    """Mutable SPWS state stored outside git repositories."""

    def __init__(self, config: SpwsConfig | None = None, *, workspace_root: Path | None = None) -> None:
        import sqlite3

        base = config or load_config()
        if workspace_root is not None:
            root = workspace_root.resolve()
            base = replace(
                base,
                workspace_path=root,
                manuscripts_path=root / "manuscripts",
                runs_path=root / "runs",
            )
        self.config = base
        self._ensure_layout()
        self.blobs = BlobStore(self.config.objects_path)
        ensure_schema(self.config.sqlite_path)
        self._conn = sqlite3.connect(self.config.sqlite_path)
        self._conn.row_factory = sqlite3.Row

    def _ensure_layout(self) -> None:
        for path in (
            self.config.workspace_path,
            self.config.objects_path,
            self.config.manuscripts_path,
            self.config.runs_path,
            self.config.decisions_path,
            self.config.promotions_path,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        self._conn.close()

    def persist_input_package(self, package: InputPackage) -> RawSource:
        text = package.text
        if text is None:
            raise ValueError("persist_input_package requires inline text")
        digest, blob_path = self.blobs.put_text(text, media_type=package.media_type)
        stored_at = _utc_now()
        source = RawSource(
            source_id=f"raw-{uuid4().hex[:12]}",
            input_package_id=package.package_id,
            media_type=package.media_type,
            encoding=package.encoding,
            text=text,
            content_digest=digest,
            stored_at=stored_at,
            storage_location=str(blob_path),
            rights=package.rights,
            privacy=package.privacy,
        )
        payload = json.loads(source.model_dump_json())
        self._conn.execute(
            "INSERT OR REPLACE INTO input_packages (package_id, payload_json) VALUES (?, ?)",
            (package.package_id, package.model_dump_json()),
        )
        self._conn.execute(
            """
            INSERT OR REPLACE INTO raw_sources
            (source_id, input_package_id, content_digest, storage_location,
             manuscript_id, version_id, parent_version_ids, payload_json, created_at)
            VALUES (?, ?, ?, ?, NULL, NULL, NULL, ?, ?)
            """,
            (
                source.source_id,
                source.input_package_id,
                source.content_digest.value,
                source.storage_location,
                json.dumps(payload),
                stored_at.isoformat(),
            ),
        )
        self._conn.commit()
        return source

    def get_input_package(self, package_id: str) -> InputPackage:
        row = self._conn.execute(
            "SELECT payload_json FROM input_packages WHERE package_id = ?",
            (package_id,),
        ).fetchone()
        if row is None:
            raise KeyError(package_id)
        return InputPackage.model_validate_json(row["payload_json"])

    def get_raw_source(self, source_id: str) -> RawSource:
        from .tombstone import strip_tombstone_fields

        row = self._conn.execute(
            "SELECT payload_json FROM raw_sources WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        if row is None:
            raise KeyError(source_id)
        raw = row["payload_json"]
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        data = json.loads(raw) if isinstance(raw, str) else dict(raw)
        if data.get("tombstoned"):
            data = strip_tombstone_fields(data)
            data["text"] = None
        return RawSource.model_validate_json(json.dumps(data))

    def save_run(self, manifest: RunManifest) -> Path:
        payload = json.loads(manifest.model_dump_json())
        self._conn.execute(
            """
            INSERT OR REPLACE INTO runs
            (run_id, manuscript_id, version_id, content_digest, parent_version_ids, payload_json, created_at)
            VALUES (?, NULL, NULL, NULL, NULL, ?, ?)
            """,
            (manifest.run_id, json.dumps(payload), _utc_now().isoformat()),
        )
        self._conn.commit()
        path = self.config.runs_path / f"{manifest.run_id}.json"
        path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        return path

    def save_revision_decision(self, decision: RevisionDecision) -> Path:
        persist_revision_decision(self.config, decision)
        path = self.config.decisions_path / f"{decision.decision_id}.json"
        return path

    def get_revision_decision(self, decision_id: str) -> RevisionDecision:
        row = self._conn.execute(
            "SELECT payload_json FROM revision_decisions WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
        if row is None:
            raise KeyError(decision_id)
        raw = row["payload_json"]
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            return RevisionDecision.model_validate_json(raw)
        return RevisionDecision.model_validate(raw)

    def workspace_inside_repo(self, repo_root: Path) -> bool:
        try:
            self.config.workspace_path.relative_to(repo_root.resolve())
            return True
        except ValueError:
            return False
