"""Typed PKL retrieval over the runtime index."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from spws_contracts_core.digests import CanonicalisationMethod, CanonicalisationRecord, DigestBasis, DigestRecord
from spws_contracts_core.domain import (
    PKLQuery,
    PKLRelationship,
    PKLResult,
    PrivacyState,
    RetrievalMethod,
    RightsState,
    TextSpan,
)
from datetime import datetime

from ..config import SpwsConfig
from ..embeddings import EmbeddingRetriever
from ..indexer.indexer import CATALOGUE_DB, FULLTEXT_DB, RELATIONSHIPS_DB, open_catalogue
from ..policy import allows_retrieval


class PKLRetriever:
    def __init__(self, config: SpwsConfig) -> None:
        self.config = config
        self.index_root = config.index_root
        self.embedder = EmbeddingRetriever(config) if config.embeddings.enabled else None

    def _catalogue(self) -> sqlite3.Connection:
        return open_catalogue(self.index_root / CATALOGUE_DB)

    def _fulltext(self) -> sqlite3.Connection:
        return open_catalogue(self.index_root / FULLTEXT_DB)

    def _relationships(self) -> sqlite3.Connection:
        return open_catalogue(self.index_root / RELATIONSHIPS_DB)

    def _record_to_result(
        self,
        row: sqlite3.Row,
        *,
        method: RetrievalMethod,
        confidence: float,
        summary: str | None = None,
        span: TextSpan | None = None,
    ) -> PKLResult:
        return PKLResult(
            object_uid=row["uid"],
            title=row["title"] or row["uid"],
            relevant_span=span,
            path=row["relative_path"],
            commit=row["commit_sha"],
            digest=DigestRecord(
                value=row["content_digest"],
                basis=DigestBasis.RAW_BYTES,
                byte_length=row["byte_length"],
                media_type="text/markdown",
                character_encoding="utf-8",
                canonicalisation=CanonicalisationRecord(method=CanonicalisationMethod.NONE),
            ),
            relationships=self._relationships_for(row["uid"], row["commit_sha"]),
            rights=RightsState(row["rights"]),
            privacy=PrivacyState(row["privacy"]),
            confidence=confidence,
            retrieval_method=method,
            summary=summary,
            object_type=row["object_type"],
            reproducible=bool(row["reproducible"]),
            extracted_at=datetime.fromisoformat(row["extracted_at"].replace("Z", "+00:00")),
        )

    def _relationships_for(self, uid: str, commit_sha: str) -> list[PKLRelationship]:
        conn = self._relationships()
        try:
            rows = conn.execute(
                """
                SELECT rel_type, target, note, confidence
                FROM relationships
                WHERE source_uid = ? AND commit_sha = ?
                """,
                (uid, commit_sha),
            ).fetchall()
            return [
                PKLRelationship(
                    type=row["rel_type"],
                    target=row["target"],
                    note=row["note"],
                    confidence=row["confidence"],
                )
                for row in rows
            ]
        finally:
            conn.close()

    def _base_record_query(self, query: PKLQuery) -> tuple[str, list[object]]:
        clauses = ["excluded = 0"]
        params: list[object] = []
        if query.commit:
            clauses.append("commit_sha = ?")
            params.append(query.commit)
        elif not query.include_working_tree:
            clauses.append("commit_sha != 'WORKING_TREE'")
        if query.object_types:
            placeholders = ",".join("?" for _ in query.object_types)
            clauses.append(f"object_type IN ({placeholders})")
            params.extend(query.object_types)
        sql = f"SELECT * FROM records WHERE {' AND '.join(clauses)}"
        return sql, params

    def query(self, query: PKLQuery) -> list[PKLResult]:
        results: list[PKLResult] = []
        seen: set[str] = set()

        conn = self._catalogue()
        try:
            sql, params = self._base_record_query(query)
            for row in conn.execute(sql, params):
                decision = allows_retrieval(
                    RightsState(row["rights"]),
                    PrivacyState(row["privacy"]),
                    self.config.policy,
                    rights_filter=query.rights_filter,
                    privacy_filter=query.privacy_filter,
                )
                if not decision.allowed:
                    continue
                if row["uid"] in seen:
                    continue
                seen.add(row["uid"])
                results.append(
                    self._record_to_result(row, method=RetrievalMethod.METADATA, confidence=0.55)
                )
        finally:
            conn.close()

        if query.text:
            lexical = self._lexical_search(query)
            for item in lexical:
                if item.object_uid not in seen:
                    results.append(item)
                    seen.add(item.object_uid)

            if self.embedder is not None:
                semantic = self.embedder.search(query, seen_uids=seen)
                for item in semantic:
                    if item.object_uid not in seen:
                        results.append(item)
                        seen.add(item.object_uid)

        if query.relationships:
            rel_results = self._relationship_search(query, seen)
            for item in rel_results:
                if item.object_uid not in seen:
                    results.append(item)
                    seen.add(item.object_uid)

        results.sort(key=lambda item: item.confidence, reverse=True)
        return results[: query.result_limit]

    def _lexical_search(self, query: PKLQuery) -> list[PKLResult]:
        if not query.text:
            return []
        conn = self._fulltext()
        cat = self._catalogue()
        try:
            rows = conn.execute(
                """
                SELECT uid, commit_sha, title, body, bm25(documents) AS rank
                FROM documents
                WHERE documents MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query.text, query.result_limit),
            ).fetchall()
            results: list[PKLResult] = []
            for row in rows:
                record = cat.execute(
                    "SELECT * FROM records WHERE uid = ? AND commit_sha = ? AND excluded = 0",
                    (row["uid"], row["commit_sha"]),
                ).fetchone()
                if record is None:
                    continue
                decision = allows_retrieval(
                    RightsState(record["rights"]),
                    PrivacyState(record["privacy"]),
                    self.config.policy,
                    rights_filter=query.rights_filter,
                    privacy_filter=query.privacy_filter,
                )
                if not decision.allowed:
                    continue
                body = row["body"] or ""
                needle = query.text.lower()
                idx = body.lower().find(needle)
                span = None
                if idx >= 0:
                    span = TextSpan(start_char=idx, end_char=idx + len(query.text), quote=body[idx : idx + len(query.text)])
                confidence = min(0.95, 0.65 + abs(float(row["rank"] or 0)) * 0.01)
                results.append(
                    self._record_to_result(
                        record,
                        method=RetrievalMethod.LEXICAL,
                        confidence=confidence,
                        summary=body[:240] or None,
                        span=span,
                    )
                )
            return results
        finally:
            conn.close()
            cat.close()

    def _relationship_search(self, query: PKLQuery, seen: set[str]) -> list[PKLResult]:
        conn = self._relationships()
        cat = self._catalogue()
        try:
            placeholders = ",".join("?" for _ in query.relationships)
            rows = conn.execute(
                f"""
                SELECT DISTINCT source_uid, commit_sha
                FROM relationships
                WHERE rel_type IN ({placeholders})
                LIMIT ?
                """,
                [*query.relationships, query.result_limit],
            ).fetchall()
            results: list[PKLResult] = []
            for row in rows:
                if row["source_uid"] in seen:
                    continue
                record = cat.execute(
                    "SELECT * FROM records WHERE uid = ? AND commit_sha = ? AND excluded = 0",
                    (row["source_uid"], row["commit_sha"]),
                ).fetchone()
                if record is None:
                    continue
                decision = allows_retrieval(
                    RightsState(record["rights"]),
                    PrivacyState(record["privacy"]),
                    self.config.policy,
                    rights_filter=query.rights_filter,
                    privacy_filter=query.privacy_filter,
                )
                if not decision.allowed:
                    continue
                results.append(
                    self._record_to_result(
                        record,
                        method=RetrievalMethod.RELATIONSHIP,
                        confidence=0.6,
                    )
                )
            return results
        finally:
            conn.close()
            cat.close()
