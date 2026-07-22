"""Build and incrementally update the runtime PKL index outside the Library."""

from __future__ import annotations

import json
import shutil
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from spws_contracts_core.domain import PrivacyState, ReadMode, RightsState
from spws_contracts_core.time import format_rfc3339_utc

from ..config import SpwsConfig
from ..parser.parser import parse_pkl_bytes
from ..policy import catalogue_exclusion, parse_privacy, parse_rights
from ..snapshot.snapshot import SnapshotReader, WORKING_TREE_SHA, sha256_hex

CATALOGUE_DB = "catalogue.sqlite"
FULLTEXT_DB = "fulltext.sqlite"
RELATIONSHIPS_DB = "relationships.sqlite"
MANIFEST_FILE = "index-manifest.json"
EMBEDDINGS_DIR = "embeddings"


@dataclass(frozen=True, slots=True)
class IndexRecord:
    repo_identity: str
    commit_sha: str
    uid: str
    relative_path: str
    content_digest: str
    byte_length: int
    extracted_at: str
    rights: str
    privacy: str
    title: str
    object_type: str | None
    reproducible: bool
    excluded: bool
    exclusion_reason: str | None


@dataclass(frozen=True, slots=True)
class IndexManifest:
    schema_version: str
    repo_identity: str
    commit_sha: str
    read_mode: str
    built_at: str
    record_count: int
    excluded_count: int
    digest_index: dict[str, str]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    @classmethod
    def from_path(cls, path: Path) -> "IndexManifest":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)


def open_catalogue(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _init_catalogue(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS records (
            uid TEXT NOT NULL,
            repo_identity TEXT NOT NULL,
            commit_sha TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            content_digest TEXT NOT NULL,
            byte_length INTEGER NOT NULL,
            extracted_at TEXT NOT NULL,
            rights TEXT NOT NULL,
            privacy TEXT NOT NULL,
            title TEXT,
            object_type TEXT,
            reproducible INTEGER NOT NULL,
            excluded INTEGER NOT NULL DEFAULT 0,
            exclusion_reason TEXT,
            PRIMARY KEY (uid, commit_sha, repo_identity)
        );
        CREATE INDEX IF NOT EXISTS idx_records_path ON records(relative_path);
        CREATE INDEX IF NOT EXISTS idx_records_digest ON records(content_digest);
        """
    )


def _init_fulltext(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS documents USING fts5(
            uid UNINDEXED,
            commit_sha UNINDEXED,
            title,
            body,
            tokenize='porter'
        );
        """
    )


def _init_relationships(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS relationships (
            source_uid TEXT NOT NULL,
            commit_sha TEXT NOT NULL,
            rel_type TEXT NOT NULL,
            target TEXT NOT NULL,
            note TEXT,
            confidence TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_uid, commit_sha);
        """
    )


class PKLIndexer:
    def __init__(self, config: SpwsConfig) -> None:
        self.config = config
        self.index_root = config.index_root
        self.index_root.mkdir(parents=True, exist_ok=True)

    def _reader(self, commit: str | None = None) -> SnapshotReader:
        mode_text = self.config.pkl.read_mode
        if mode_text == "filesystem":
            return SnapshotReader(
                self.config.pkl.repository_path,
                read_mode="filesystem",
                commit=commit,
                mirror_cache=self.config.git_mirror_cache,
                allow_remote=self.config.policy.allow_remote_git,
            )
        mode = ReadMode(mode_text)
        if mode is ReadMode.WORKING_TREE and not self.config.policy.allow_working_tree_reads:
            raise PermissionError("working tree reads disabled by policy")
        return SnapshotReader(
            self.config.pkl.repository_path,
            read_mode=mode,
            commit=commit,
            mirror_cache=self.config.git_mirror_cache,
            allow_remote=self.config.policy.allow_remote_git,
        )

    def _extract_record(
        self,
        reader: SnapshotReader,
        relative_path: str,
        extracted_at: datetime,
    ) -> IndexRecord | None:
        try:
            data = reader.read_bytes(relative_path)
            parsed = parse_pkl_bytes(data)
        except Exception:
            return None
        digest = sha256_hex(data)
        rights = parse_rights(parsed.rights)
        privacy = parse_privacy(parsed.privacy)
        decision = catalogue_exclusion(rights, privacy, self.config.policy)
        commit_sha = reader.resolve_commit()
        reproducible = commit_sha != WORKING_TREE_SHA
        return IndexRecord(
            repo_identity=reader.repo_identity,
            commit_sha=commit_sha,
            uid=parsed.uid,
            relative_path=relative_path,
            content_digest=digest,
            byte_length=len(data),
            extracted_at=format_rfc3339_utc(extracted_at),
            rights=rights.value,
            privacy=privacy.value,
            title=parsed.title,
            object_type=parsed.object_type,
            reproducible=reproducible,
            excluded=not decision.allowed,
            exclusion_reason=decision.reason,
        )

    def _write_record(
        self,
        catalogue: sqlite3.Connection,
        fulltext: sqlite3.Connection,
        relationships: sqlite3.Connection,
        reader: SnapshotReader,
        record: IndexRecord,
        body: str,
        rels: list[Any],
    ) -> None:
        catalogue.execute(
            """
            INSERT INTO records (
                uid, repo_identity, commit_sha, relative_path, content_digest,
                byte_length, extracted_at, rights, privacy, title, object_type,
                reproducible, excluded, exclusion_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(uid, commit_sha, repo_identity) DO UPDATE SET
                relative_path=excluded.relative_path,
                content_digest=excluded.content_digest,
                byte_length=excluded.byte_length,
                extracted_at=excluded.extracted_at,
                rights=excluded.rights,
                privacy=excluded.privacy,
                title=excluded.title,
                object_type=excluded.object_type,
                reproducible=excluded.reproducible,
                excluded=excluded.excluded,
                exclusion_reason=excluded.exclusion_reason
            """,
            (
                record.uid,
                record.repo_identity,
                record.commit_sha,
                record.relative_path,
                record.content_digest,
                record.byte_length,
                record.extracted_at,
                record.rights,
                record.privacy,
                record.title,
                record.object_type,
                int(record.reproducible),
                int(record.excluded),
                record.exclusion_reason,
            ),
        )
        fulltext.execute(
            "DELETE FROM documents WHERE uid = ? AND commit_sha = ?",
            (record.uid, record.commit_sha),
        )
        if not record.excluded:
            fulltext.execute(
                "INSERT INTO documents(uid, commit_sha, title, body) VALUES (?, ?, ?, ?)",
                (record.uid, record.commit_sha, record.title, body),
            )
        relationships.execute(
            "DELETE FROM relationships WHERE source_uid = ? AND commit_sha = ?",
            (record.uid, record.commit_sha),
        )
        for rel in rels:
            relationships.execute(
                """
                INSERT INTO relationships(source_uid, commit_sha, rel_type, target, note, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.uid,
                    record.commit_sha,
                    rel.type,
                    rel.target,
                    rel.note,
                    str(rel.confidence) if rel.confidence is not None else None,
                ),
            )

    def _build_into(self, staging: Path, paths: list[str] | None = None) -> IndexManifest:
        staging.mkdir(parents=True, exist_ok=True)
        (staging / EMBEDDINGS_DIR).mkdir(exist_ok=True)

        catalogue_path = staging / CATALOGUE_DB
        fulltext_path = staging / FULLTEXT_DB
        relationships_path = staging / RELATIONSHIPS_DB

        catalogue = open_catalogue(catalogue_path)
        fulltext = open_catalogue(fulltext_path)
        relationships = open_catalogue(relationships_path)
        _init_catalogue(catalogue)
        _init_fulltext(fulltext)
        _init_relationships(relationships)

        reader = self._reader()
        extracted_at = datetime.now(tz=UTC)
        target_paths = paths if paths is not None else reader.list_markdown_paths()
        digest_index: dict[str, str] = {}
        record_count = 0
        excluded_count = 0

        for relative_path in sorted(target_paths):
            record = self._extract_record(reader, relative_path, extracted_at)
            if record is None:
                continue
            data = reader.read_bytes(relative_path)
            parsed = parse_pkl_bytes(data)
            self._write_record(
                catalogue,
                fulltext,
                relationships,
                reader,
                record,
                parsed.body,
                parsed.relationships,
            )
            if (
                self.config.embeddings.enabled
                and not record.excluded
                and parsed.body.strip()
            ):
                self._index_embeddings(
                    staging,
                    record,
                    parsed.body,
                )
            digest_index[relative_path] = record.content_digest
            record_count += 1
            if record.excluded:
                excluded_count += 1

        catalogue.commit()
        fulltext.commit()
        relationships.commit()
        catalogue.close()
        fulltext.close()
        relationships.close()

        manifest = IndexManifest(
            schema_version="0.1.0",
            repo_identity=reader.repo_identity,
            commit_sha=reader.resolve_commit(),
            read_mode=self.config.pkl.read_mode,
            built_at=format_rfc3339_utc(extracted_at),
            record_count=record_count,
            excluded_count=excluded_count,
            digest_index=digest_index,
        )
        (staging / MANIFEST_FILE).write_text(manifest.to_json(), encoding="utf-8")
        return manifest

    def _atomic_swap(self, staging: Path) -> None:
        for name in [CATALOGUE_DB, FULLTEXT_DB, RELATIONSHIPS_DB, MANIFEST_FILE]:
            src = staging / name
            dst = self.index_root / name
            tmp = dst.with_suffix(dst.suffix + ".swap")
            if tmp.exists():
                tmp.unlink()
            if dst.exists():
                dst.rename(tmp)
            src.replace(dst)
            if tmp.exists():
                tmp.unlink()

        staging_embeddings = staging / EMBEDDINGS_DIR
        target_embeddings = self.index_root / EMBEDDINGS_DIR
        if target_embeddings.exists():
            shutil.rmtree(target_embeddings)
        if staging_embeddings.exists():
            staging_embeddings.replace(target_embeddings)

        staging_meaning = staging / "meaning"
        target_meaning = self.index_root / "meaning"
        if staging_meaning.exists():
            if target_meaning.exists():
                shutil.rmtree(target_meaning)
            staging_meaning.replace(target_meaning)

        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

    def _index_embeddings(self, staging: Path, record: IndexRecord, body: str) -> None:
        """Index semantic chunks and meaning units when embeddings are enabled."""
        from dataclasses import replace

        from ..embeddings import EmbeddingRetriever

        # Point retriever store at staging embeddings dir
        staging_config = replace(
            self.config,
            pkl=replace(self.config.pkl, cache_path=staging),
        )
        # SpwsConfig.index_root uses pkl.cache_path
        try:
            retriever = EmbeddingRetriever(staging_config)
            retriever.index_record(
                record.uid,
                record.commit_sha,
                record.content_digest,
                body,
                RightsState(record.rights),
                PrivacyState(record.privacy),
            )
        except Exception:
            # Embedding failures must not abort catalogue indexing
            return
        try:
            from spws_semantics import MeaningGauge

            debug_hash = bool(getattr(self.config.embeddings, "debug_hash_embeddings", False))
            # Canonical meaning store lives at cache/meaning (not embeddings/meaning)
            gauge = MeaningGauge(
                staging / "meaning",
                model_id=self.config.embeddings.model_id,
                model_version=self.config.embeddings.model_version,
                debug_hash_embeddings=debug_hash,
                require_model=not debug_hash,
            )
            gauge.index_text(
                body,
                source_object_id=record.relative_path,
                object_uid=record.uid,
                commit_sha=record.commit_sha,
                rights=RightsState(record.rights),
                privacy=PrivacyState(record.privacy),
            )
        except Exception:
            return

    def build_full(self) -> IndexManifest:
        staging = self.index_root / f".staging-{uuid.uuid4().hex}"
        try:
            manifest = self._build_into(staging)
            self._atomic_swap(staging)
            return manifest
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)

    def update_incremental(self) -> IndexManifest:
        manifest_path = self.index_root / MANIFEST_FILE
        if not manifest_path.is_file():
            return self.build_full()

        previous = IndexManifest.from_path(manifest_path)
        reader = self._reader()
        current_commit = reader.resolve_commit()
        if current_commit == previous.commit_sha:
            return previous

        changes = reader.diff_since(previous.commit_sha)
        changed_paths = [change.relative_path for change in changes if not change.status.startswith("D")]
        deleted_paths = [change.relative_path for change in changes if change.status.startswith("D")]

        staging = self.index_root / f".staging-{uuid.uuid4().hex}"
        try:
            staging.mkdir(parents=True, exist_ok=True)
            for name in [CATALOGUE_DB, FULLTEXT_DB, RELATIONSHIPS_DB, MANIFEST_FILE]:
                src = self.index_root / name
                if src.is_file():
                    shutil.copy2(src, staging / name)
            src_embeddings = self.index_root / EMBEDDINGS_DIR
            if src_embeddings.is_dir():
                shutil.copytree(src_embeddings, staging / EMBEDDINGS_DIR)
            else:
                (staging / EMBEDDINGS_DIR).mkdir(exist_ok=True)

            catalogue = open_catalogue(staging / CATALOGUE_DB)
            fulltext = open_catalogue(staging / FULLTEXT_DB)
            relationships = open_catalogue(staging / RELATIONSHIPS_DB)

            for relative_path in deleted_paths:
                rows = catalogue.execute(
                    "SELECT uid FROM records WHERE relative_path = ?",
                    (relative_path,),
                ).fetchall()
                for row in rows:
                    uid = row["uid"]
                    catalogue.execute(
                        "DELETE FROM records WHERE uid = ? AND commit_sha = ?",
                        (uid, current_commit),
                    )
                    fulltext.execute(
                        "DELETE FROM documents WHERE uid = ? AND commit_sha = ?",
                        (uid, current_commit),
                    )
                    relationships.execute(
                        "DELETE FROM relationships WHERE source_uid = ? AND commit_sha = ?",
                        (uid, current_commit),
                    )

            extracted_at = datetime.now(tz=UTC)
            digest_index = dict(previous.digest_index)
            for relative_path in changed_paths:
                record = self._extract_record(reader, relative_path, extracted_at)
                if record is None:
                    digest_index.pop(relative_path, None)
                    continue
                parsed = parse_pkl_bytes(reader.read_bytes(relative_path))
                self._write_record(
                    catalogue,
                    fulltext,
                    relationships,
                    reader,
                    record,
                    parsed.body,
                    parsed.relationships,
                )
                digest_index[relative_path] = record.content_digest

            catalogue.commit()
            fulltext.commit()
            relationships.commit()
            catalogue.close()
            fulltext.close()
            relationships.close()

            count_conn = open_catalogue(staging / CATALOGUE_DB)
            rows = count_conn.execute("SELECT COUNT(*), SUM(excluded) FROM records").fetchone()
            record_count = int(rows[0])
            excluded_count = int(rows[1] or 0)
            count_conn.close()

            manifest = IndexManifest(
                schema_version=previous.schema_version,
                repo_identity=reader.repo_identity,
                commit_sha=current_commit,
                read_mode=self.config.pkl.read_mode,
                built_at=format_rfc3339_utc(extracted_at),
                record_count=record_count,
                excluded_count=excluded_count,
                digest_index=digest_index,
            )
            (staging / MANIFEST_FILE).write_text(manifest.to_json(), encoding="utf-8")
            self._atomic_swap(staging)
            return manifest
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)

    def load_manifest(self) -> IndexManifest | None:
        path = self.index_root / MANIFEST_FILE
        return IndexManifest.from_path(path) if path.is_file() else None
