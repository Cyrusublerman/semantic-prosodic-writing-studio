from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from spws_contracts_core import InputPackage, RawSource, RunManifest, RevisionDecision

from .blobs import BlobStore
from dataclasses import replace

from .config import SpwsConfig, load_config


def _utc_now() -> datetime:
    return datetime.now(UTC)


class WorkspaceStore:
    """Mutable SPWS state stored outside git repositories."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS input_packages (
        package_id TEXT PRIMARY KEY,
        payload_json TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS raw_sources (
        source_id TEXT PRIMARY KEY,
        input_package_id TEXT NOT NULL,
        content_digest TEXT NOT NULL,
        storage_location TEXT NOT NULL,
        payload_json TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        payload_json TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS revision_decisions (
        decision_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        payload_json TEXT NOT NULL
    );
    """

    def __init__(self, config: SpwsConfig | None = None, *, workspace_root: Path | None = None) -> None:
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
        self._conn = sqlite3.connect(self.config.sqlite_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(self.SCHEMA)

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
        self._conn.execute(
            "INSERT OR REPLACE INTO input_packages (package_id, payload_json) VALUES (?, ?)",
            (package.package_id, package.model_dump_json()),
        )
        self._conn.execute(
            """
            INSERT OR REPLACE INTO raw_sources
            (source_id, input_package_id, content_digest, storage_location, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                source.source_id,
                source.input_package_id,
                source.content_digest.value,
                source.storage_location,
                source.model_dump_json(),
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
        row = self._conn.execute(
            "SELECT payload_json FROM raw_sources WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        if row is None:
            raise KeyError(source_id)
        return RawSource.model_validate_json(row["payload_json"])

    def save_run(self, manifest: RunManifest) -> Path:
        self._conn.execute(
            "INSERT OR REPLACE INTO runs (run_id, payload_json) VALUES (?, ?)",
            (manifest.run_id, manifest.model_dump_json()),
        )
        self._conn.commit()
        path = self.config.runs_path / f"{manifest.run_id}.json"
        path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        return path

    def save_revision_decision(self, decision: RevisionDecision) -> Path:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO revision_decisions (decision_id, run_id, payload_json)
            VALUES (?, ?, ?)
            """,
            (decision.decision_id, decision.run_id, decision.model_dump_json()),
        )
        self._conn.commit()
        path = self.config.decisions_path / f"{decision.decision_id}.json"
        path.write_text(decision.model_dump_json(indent=2), encoding="utf-8")
        return path

    def get_revision_decision(self, decision_id: str) -> RevisionDecision:
        row = self._conn.execute(
            "SELECT payload_json FROM revision_decisions WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
        if row is None:
            raise KeyError(decision_id)
        return RevisionDecision.model_validate_json(row["payload_json"])

    def workspace_inside_repo(self, repo_root: Path) -> bool:
        try:
            self.config.workspace_path.relative_to(repo_root.resolve())
            return True
        except ValueError:
            return False
