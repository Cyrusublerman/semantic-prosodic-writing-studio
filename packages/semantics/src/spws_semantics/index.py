"""SQLite meaning store for units and profiles."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from spws_contracts_core.domain import (
    MeaningProfile,
    MeaningScale,
    MeaningUnit,
    PrivacyState,
    RightsState,
    TextSpan,
)


class MeaningStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "meaning.sqlite"
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        conn = self._connect()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS units (
                unit_id TEXT PRIMARY KEY,
                scale TEXT NOT NULL,
                text TEXT NOT NULL,
                start_char INTEGER,
                end_char INTEGER,
                quote TEXT,
                source_object_id TEXT,
                parent_unit_id TEXT,
                object_uid TEXT,
                commit_sha TEXT,
                rights TEXT,
                privacy TEXT,
                content_digest TEXT
            );
            CREATE TABLE IF NOT EXISTS profiles (
                unit_id TEXT PRIMARY KEY,
                embedding_json TEXT,
                model_id TEXT,
                model_version TEXT,
                domain_tags TEXT,
                register_tags TEXT,
                affect_tags TEXT,
                imagery_tags TEXT,
                theme_tags TEXT,
                concept_ids TEXT,
                confidence REAL,
                analyser TEXT,
                analyser_version TEXT,
                FOREIGN KEY(unit_id) REFERENCES units(unit_id)
            );
            CREATE INDEX IF NOT EXISTS idx_units_scale ON units(scale);
            CREATE INDEX IF NOT EXISTS idx_units_object ON units(object_uid, commit_sha);
            """
        )
        conn.commit()
        conn.close()

    def clear_object(self, object_uid: str, commit_sha: str | None = None) -> None:
        conn = self._connect()
        if commit_sha:
            rows = conn.execute(
                "SELECT unit_id FROM units WHERE object_uid = ? AND commit_sha = ?",
                (object_uid, commit_sha),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT unit_id FROM units WHERE object_uid = ?",
                (object_uid,),
            ).fetchall()
        ids = [row["unit_id"] for row in rows]
        for unit_id in ids:
            conn.execute("DELETE FROM profiles WHERE unit_id = ?", (unit_id,))
            conn.execute("DELETE FROM units WHERE unit_id = ?", (unit_id,))
        conn.commit()
        conn.close()

    def upsert(self, unit: MeaningUnit, profile: MeaningProfile) -> None:
        conn = self._connect()
        span = unit.span
        conn.execute(
            """
            INSERT INTO units(
                unit_id, scale, text, start_char, end_char, quote, source_object_id,
                parent_unit_id, object_uid, commit_sha, rights, privacy, content_digest
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(unit_id) DO UPDATE SET
                scale=excluded.scale,
                text=excluded.text,
                start_char=excluded.start_char,
                end_char=excluded.end_char,
                quote=excluded.quote,
                source_object_id=excluded.source_object_id,
                parent_unit_id=excluded.parent_unit_id,
                object_uid=excluded.object_uid,
                commit_sha=excluded.commit_sha,
                rights=excluded.rights,
                privacy=excluded.privacy,
                content_digest=excluded.content_digest
            """,
            (
                unit.unit_id,
                unit.scale.value,
                unit.text,
                span.start_char if span else None,
                span.end_char if span else None,
                span.quote if span else None,
                unit.source_object_id,
                unit.parent_unit_id,
                unit.object_uid,
                unit.commit_sha,
                unit.rights.value,
                unit.privacy.value,
                unit.content_digest.value if unit.content_digest else None,
            ),
        )
        conn.execute(
            """
            INSERT INTO profiles(
                unit_id, embedding_json, model_id, model_version, domain_tags, register_tags,
                affect_tags, imagery_tags, theme_tags, concept_ids, confidence, analyser, analyser_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(unit_id) DO UPDATE SET
                embedding_json=excluded.embedding_json,
                model_id=excluded.model_id,
                model_version=excluded.model_version,
                domain_tags=excluded.domain_tags,
                register_tags=excluded.register_tags,
                affect_tags=excluded.affect_tags,
                imagery_tags=excluded.imagery_tags,
                theme_tags=excluded.theme_tags,
                concept_ids=excluded.concept_ids,
                confidence=excluded.confidence,
                analyser=excluded.analyser,
                analyser_version=excluded.analyser_version
            """,
            (
                profile.unit_id,
                json.dumps(profile.embedding) if profile.embedding is not None else None,
                profile.model_id,
                profile.model_version,
                json.dumps(profile.domain_tags),
                json.dumps(profile.register_tags),
                json.dumps(profile.affect_tags),
                json.dumps(profile.imagery_tags),
                json.dumps(profile.theme_tags),
                json.dumps(profile.concept_ids),
                profile.confidence,
                profile.analyser,
                profile.analyser_version,
            ),
        )
        conn.commit()
        conn.close()

    def get_unit(self, unit_id: str) -> MeaningUnit | None:
        conn = self._connect()
        row = conn.execute("SELECT * FROM units WHERE unit_id = ?", (unit_id,)).fetchone()
        conn.close()
        if row is None:
            return None
        return self._row_to_unit(row)

    def get_profile(self, unit_id: str) -> MeaningProfile | None:
        conn = self._connect()
        row = conn.execute("SELECT * FROM profiles WHERE unit_id = ?", (unit_id,)).fetchone()
        conn.close()
        if row is None:
            return None
        return self._row_to_profile(row)

    def all_with_profiles(
        self,
        *,
        scales: list[MeaningScale] | None = None,
    ) -> list[tuple[MeaningUnit, MeaningProfile]]:
        conn = self._connect()
        if scales:
            placeholders = ",".join("?" for _ in scales)
            rows = conn.execute(
                f"""
                SELECT u.*, p.embedding_json, p.model_id, p.model_version, p.domain_tags, p.register_tags,
                       p.affect_tags, p.imagery_tags, p.theme_tags, p.concept_ids, p.confidence,
                       p.analyser, p.analyser_version
                FROM units u JOIN profiles p ON u.unit_id = p.unit_id
                WHERE u.scale IN ({placeholders})
                """,
                [s.value for s in scales],
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT u.*, p.embedding_json, p.model_id, p.model_version, p.domain_tags, p.register_tags,
                       p.affect_tags, p.imagery_tags, p.theme_tags, p.concept_ids, p.confidence,
                       p.analyser, p.analyser_version
                FROM units u JOIN profiles p ON u.unit_id = p.unit_id
                """
            ).fetchall()
        conn.close()
        return [(self._row_to_unit(row), self._row_to_profile(row)) for row in rows]

    def count(self) -> int:
        conn = self._connect()
        count = conn.execute("SELECT COUNT(*) AS c FROM units").fetchone()["c"]
        conn.close()
        return int(count)

    @staticmethod
    def _row_to_unit(row: sqlite3.Row) -> MeaningUnit:
        span = None
        if row["start_char"] is not None and row["end_char"] is not None:
            span = TextSpan(
                start_char=row["start_char"],
                end_char=row["end_char"],
                quote=row["quote"],
            )
        return MeaningUnit(
            unit_id=row["unit_id"],
            scale=MeaningScale(row["scale"]),
            text=row["text"],
            span=span,
            source_object_id=row["source_object_id"],
            parent_unit_id=row["parent_unit_id"],
            object_uid=row["object_uid"],
            commit_sha=row["commit_sha"],
            rights=RightsState(row["rights"] or "unknown"),
            privacy=PrivacyState(row["privacy"] or "unknown"),
        )

    @staticmethod
    def _row_to_profile(row: sqlite3.Row) -> MeaningProfile:
        emb = row["embedding_json"]
        return MeaningProfile(
            unit_id=row["unit_id"],
            embedding=json.loads(emb) if emb else None,
            model_id=row["model_id"],
            model_version=row["model_version"],
            domain_tags=json.loads(row["domain_tags"] or "[]"),
            register_tags=json.loads(row["register_tags"] or "[]"),
            affect_tags=json.loads(row["affect_tags"] or "[]"),
            imagery_tags=json.loads(row["imagery_tags"] or "[]"),
            theme_tags=json.loads(row["theme_tags"] or "[]"),
            concept_ids=json.loads(row["concept_ids"] or "[]"),
            confidence=float(row["confidence"] or 0.0),
            analyser=row["analyser"] or "spws_semantics",
            analyser_version=row["analyser_version"] or "0.1.0",
        )
