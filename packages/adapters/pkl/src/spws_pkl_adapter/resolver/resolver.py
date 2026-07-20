"""Resolve PKL object identity to indexed records — UID first, never path as identity."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from spws_contracts_core.digests import (
    CanonicalisationMethod,
    CanonicalisationRecord,
    DigestBasis,
    DigestRecord,
    digest_bytes,
)
from datetime import datetime

from spws_contracts_core.domain import PrivacyState, RightsState

from ..indexer.indexer import CATALOGUE_DB, IndexManifest, open_catalogue


@dataclass(frozen=True, slots=True)
class ResolvedObject:
    object_uid: str
    relative_path: str
    commit_sha: str
    repo_identity: str
    digest: DigestRecord
    title: str
    object_type: str | None
    rights: RightsState
    privacy: PrivacyState
    reproducible: bool
    extracted_at: datetime
    excluded: bool
    exclusion_reason: str | None


def _row_to_resolved(row: sqlite3.Row) -> ResolvedObject:
    return ResolvedObject(
        object_uid=row["uid"],
        relative_path=row["relative_path"],
        commit_sha=row["commit_sha"],
        repo_identity=row["repo_identity"],
        digest=DigestRecord(
            value=row["content_digest"],
            basis=DigestBasis.RAW_BYTES,
            byte_length=row["byte_length"],
            media_type="text/markdown",
            character_encoding="utf-8",
            canonicalisation=CanonicalisationRecord(method=CanonicalisationMethod.NONE),
        ),
        title=row["title"] or row["uid"],
        object_type=row["object_type"],
        rights=RightsState(row["rights"]),
        privacy=PrivacyState(row["privacy"]),
        reproducible=bool(row["reproducible"]),
        extracted_at=datetime.fromisoformat(row["extracted_at"].replace("Z", "+00:00")),
        excluded=bool(row["excluded"]),
        exclusion_reason=row["exclusion_reason"],
    )


class PKLResolver:
    def __init__(self, index_root: Path) -> None:
        self.index_root = index_root
        self.catalogue_path = index_root / CATALOGUE_DB

    def _connect(self) -> sqlite3.Connection:
        if not self.catalogue_path.is_file():
            raise FileNotFoundError(f"catalogue index missing: {self.catalogue_path}")
        return open_catalogue(self.catalogue_path)

    def resolve_uid(
        self,
        uid: str,
        *,
        commit: str | None = None,
        include_excluded: bool = False,
    ) -> ResolvedObject | None:
        conn = self._connect()
        try:
            if commit:
                row = conn.execute(
                    """
                    SELECT * FROM records
                    WHERE uid = ? AND commit_sha = ? AND excluded = 0
                    """,
                    (uid, commit),
                ).fetchone()
                if row is None and include_excluded:
                    row = conn.execute(
                        "SELECT * FROM records WHERE uid = ? AND commit_sha = ?",
                        (uid, commit),
                    ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM records
                    WHERE uid = ? AND excluded = 0
                    ORDER BY extracted_at DESC
                    LIMIT 1
                    """,
                    (uid,),
                ).fetchone()
                if row is None and include_excluded:
                    row = conn.execute(
                        """
                        SELECT * FROM records
                        WHERE uid = ?
                        ORDER BY extracted_at DESC
                        LIMIT 1
                        """,
                        (uid,),
                    ).fetchone()
            return _row_to_resolved(row) if row else None
        finally:
            conn.close()

    def resolve_path_hint(
        self,
        relative_path: str,
        *,
        commit: str | None = None,
    ) -> ResolvedObject | None:
        """Resolve by path only as a lookup hint; identity remains UID."""
        conn = self._connect()
        try:
            if commit:
                row = conn.execute(
                    """
                    SELECT * FROM records
                    WHERE relative_path = ? AND commit_sha = ?
                    ORDER BY excluded ASC, extracted_at DESC
                    LIMIT 1
                    """,
                    (relative_path, commit),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM records
                    WHERE relative_path = ?
                    ORDER BY excluded ASC, extracted_at DESC
                    LIMIT 1
                    """,
                    (relative_path,),
                ).fetchone()
            return _row_to_resolved(row) if row else None
        finally:
            conn.close()

    def digest_for_bytes(self, data: bytes) -> DigestRecord:
        return digest_bytes(data, media_type="text/markdown")
