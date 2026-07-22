"""Optional semantic retrieval backed by chunked embedding storage."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from spws_contracts_core.digests import CanonicalisationMethod, CanonicalisationRecord, DigestBasis, DigestRecord
from spws_contracts_core.domain import PKLQuery, PKLResult, RetrievalMethod, RightsState, PrivacyState, TextSpan
from datetime import datetime

from .config import SpwsConfig
from .indexer.indexer import CATALOGUE_DB, EMBEDDINGS_DIR, open_catalogue
from .policy import allows_embeddings


@dataclass(frozen=True, slots=True)
class EmbeddingChunk:
    uid: str
    commit_sha: str
    content_digest: str
    start_char: int
    end_char: int
    text: str


class EmbeddingStore:
    def __init__(self, root: Path, model_id: str, model_version: str) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.model_id = model_id
        self.model_version = model_version
        self.db_path = self.root / "chunks.sqlite"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                uid TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                content_digest TEXT NOT NULL,
                start_char INTEGER NOT NULL,
                end_char INTEGER NOT NULL,
                text TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                model_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                PRIMARY KEY (uid, commit_sha, content_digest, start_char)
            );
            CREATE TABLE IF NOT EXISTS model_meta (
                model_id TEXT PRIMARY KEY,
                model_version TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT OR REPLACE INTO model_meta(model_id, model_version) VALUES (?, ?)",
            (self.model_id, self.model_version),
        )
        conn.commit()
        conn.close()

    def clear_object(self, uid: str, commit_sha: str) -> None:
        conn = self._connect()
        conn.execute("DELETE FROM chunks WHERE uid = ? AND commit_sha = ?", (uid, commit_sha))
        conn.commit()
        conn.close()

    def store_chunks(
        self,
        uid: str,
        commit_sha: str,
        content_digest: str,
        chunks: list[tuple[EmbeddingChunk, list[float]]],
    ) -> None:
        conn = self._connect()
        conn.execute(
            "DELETE FROM chunks WHERE uid = ? AND commit_sha = ? AND content_digest = ?",
            (uid, commit_sha, content_digest),
        )
        for chunk, vector in chunks:
            conn.execute(
                """
                INSERT INTO chunks(
                    uid, commit_sha, content_digest, start_char, end_char, text,
                    vector_json, model_id, model_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uid,
                    commit_sha,
                    content_digest,
                    chunk.start_char,
                    chunk.end_char,
                    chunk.text,
                    json.dumps(vector),
                    self.model_id,
                    self.model_version,
                ),
            )
        conn.commit()
        conn.close()

    def search(self, query_vector: list[float], limit: int = 20) -> list[tuple[sqlite3.Row, float]]:
        conn = self._connect()
        rows = conn.execute("SELECT * FROM chunks").fetchall()
        conn.close()
        scored: list[tuple[sqlite3.Row, float]] = []
        for row in rows:
            vector = json.loads(row["vector_json"])
            score = _cosine_similarity(query_vector, vector)
            scored.append((row, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def chunk_text(text: str, *, chunk_size: int = 400, overlap: int = 40) -> list[EmbeddingChunk]:
    chunks: list[EmbeddingChunk] = []
    if not text:
        return chunks
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(
            EmbeddingChunk(
                uid="",
                commit_sha="",
                content_digest="",
                start_char=start,
                end_char=end,
                text=text[start:end],
            )
        )
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _hash_embedding(text: str, dims: int = 32) -> list[float]:
    values = [0.0] * dims
    for index, char in enumerate(text.encode("utf-8")):
        values[index % dims] += char / 255.0
    norm = sum(v * v for v in values) ** 0.5 or 1.0
    return [v / norm for v in values]


def embed_text(text: str, *, debug_hash_embeddings: bool = True, model_id: str | None = None) -> list[float]:
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_id or "sentence-transformers/all-MiniLM-L6-v2")
        vector = model.encode(text, normalize_embeddings=True)
        return [float(v) for v in vector.tolist()]
    except Exception:
        if not debug_hash_embeddings:
            raise RuntimeError("Embedding model unavailable and debug_hash_embeddings is false")
        return _hash_embedding(text)


class EmbeddingRetriever:
    def __init__(self, config: SpwsConfig) -> None:
        if not config.embeddings.enabled:
            raise ValueError("embeddings disabled")
        self.config = config
        self.store = EmbeddingStore(
            config.index_root / EMBEDDINGS_DIR,
            config.embeddings.model_id,
            config.embeddings.model_version,
        )
        self._debug_hash = bool(getattr(config.embeddings, "debug_hash_embeddings", True))

    def index_record(self, uid: str, commit_sha: str, digest: str, body: str, rights: RightsState, privacy: PrivacyState) -> None:
        decision = allows_embeddings(rights, privacy, self.config.policy)
        if not decision.allowed:
            self.store.clear_object(uid, commit_sha)
            return
        # Prefer sentence/paragraph-aware chunks via meaning unitiser when available
        try:
            from spws_semantics.unitise import unitise_text
            from spws_contracts_core.domain import MeaningScale

            units = unitise_text(
                body,
                object_uid=uid,
                commit_sha=commit_sha,
                scales=[MeaningScale.SENTENCE, MeaningScale.PARAGRAPH],
            )
            raw_chunks = [
                EmbeddingChunk(
                    uid=uid,
                    commit_sha=commit_sha,
                    content_digest=digest,
                    start_char=unit.span.start_char if unit.span else 0,
                    end_char=unit.span.end_char if unit.span else len(unit.text),
                    text=unit.text,
                )
                for unit in units
                if unit.text.strip()
            ]
        except Exception:
            raw_chunks = chunk_text(body)
        if not raw_chunks:
            raw_chunks = chunk_text(body)
        payload: list[tuple[EmbeddingChunk, list[float]]] = []
        for chunk in raw_chunks:
            enriched = EmbeddingChunk(
                uid=uid,
                commit_sha=commit_sha,
                content_digest=digest,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                text=chunk.text,
            )
            payload.append(
                (
                    enriched,
                    embed_text(
                        chunk.text,
                        debug_hash_embeddings=self._debug_hash,
                        model_id=self.config.embeddings.model_id,
                    ),
                )
            )
        self.store.store_chunks(uid, commit_sha, digest, payload)

    def search(self, query: PKLQuery, *, seen_uids: set[str]) -> list[PKLResult]:
        if not query.text:
            return []
        query_vector = embed_text(query.text)
        hits = self.store.search(query_vector, limit=query.result_limit)
        cat = open_catalogue(self.config.index_root / CATALOGUE_DB)
        results: list[PKLResult] = []
        try:
            for row, score in hits:
                if row["uid"] in seen_uids:
                    continue
                record = cat.execute(
                    "SELECT * FROM records WHERE uid = ? AND commit_sha = ? AND excluded = 0",
                    (row["uid"], row["commit_sha"]),
                ).fetchone()
                if record is None:
                    continue
                rights = RightsState(record["rights"])
                privacy = PrivacyState(record["privacy"])
                decision = allows_embeddings(rights, privacy, self.config.policy)
                if not decision.allowed:
                    continue
                if self.config.embeddings.require_lexical_gate and query.text.lower() not in (row["text"] or "").lower():
                    continue
                span = TextSpan(
                    start_char=int(row["start_char"]),
                    end_char=int(row["end_char"]),
                    quote=row["text"],
                )
                results.append(
                    PKLResult(
                        object_uid=record["uid"],
                        title=record["title"] or record["uid"],
                        relevant_span=span,
                        path=record["relative_path"],
                        commit=record["commit_sha"],
                        digest=DigestRecord(
                            value=record["content_digest"],
                            basis=DigestBasis.RAW_BYTES,
                            byte_length=record["byte_length"],
                            media_type="text/markdown",
                            character_encoding="utf-8",
                            canonicalisation=CanonicalisationRecord(method=CanonicalisationMethod.NONE),
                        ),
                        rights=rights,
                        privacy=privacy,
                        confidence=min(0.99, 0.5 + score * 0.5),
                        retrieval_method=RetrievalMethod.SEMANTIC,
                        summary=row["text"][:240],
                        object_type=record["object_type"],
                        reproducible=bool(record["reproducible"]),
                        extracted_at=datetime.fromisoformat(record["extracted_at"].replace("Z", "+00:00")),
                    )
                )
        finally:
            cat.close()
        return results
