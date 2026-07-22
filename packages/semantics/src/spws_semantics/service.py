"""MeaningGauge facade: index text corpora and query similarity."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from spws_contracts_core.domain import (
    MeaningProfile,
    MeaningScale,
    MeaningUnit,
    PrivacyState,
    RightsState,
    SimilarityQuery,
    SimilarityResultSet,
)

from .encode import EmbeddingService, TaggingService
from .index import MeaningStore
from .similarity import similar
from .unitise import unitise_text


class MeaningGauge:
    def __init__(
        self,
        store_path: Path,
        *,
        model_id: str = "sentence-transformers/all-MiniLM-L6-v2",
        model_version: str = "unspecified",
        debug_hash_embeddings: bool = False,
        require_model: bool = True,
    ) -> None:
        self.store_path = Path(store_path)
        self.store = MeaningStore(self.store_path)
        self.embedder = EmbeddingService(
            model_id=model_id,
            model_version=model_version,
            debug_hash_embeddings=debug_hash_embeddings,
            require_model=require_model,
        )
        self.tagger = TaggingService(self.embedder)

    @classmethod
    def from_config(cls, config: Any, *, allow_hash_fallback: bool | None = None) -> "MeaningGauge":
        """Build gauge from SpwsConfig. Quality default: real model unless debug_hash set."""
        emb = getattr(config, "embeddings", None)
        debug_hash = bool(getattr(emb, "debug_hash_embeddings", False)) if emb else False
        if allow_hash_fallback is not None:
            debug_hash = allow_hash_fallback
        model_id = getattr(emb, "model_id", "sentence-transformers/all-MiniLM-L6-v2") if emb else (
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        model_version = getattr(emb, "model_version", "unspecified") if emb else "unspecified"
        path = getattr(config, "meaning_index_path", None)
        if path is None:
            path = Path(config.pkl_cache_path) / "meaning"
        return cls(
            Path(path),
            model_id=str(model_id),
            model_version=str(model_version),
            debug_hash_embeddings=debug_hash,
            require_model=not debug_hash,
        )

    def index_text(
        self,
        text: str,
        *,
        source_object_id: str | None = None,
        object_uid: str | None = None,
        commit_sha: str | None = None,
        rights: RightsState = RightsState.UNKNOWN,
        privacy: PrivacyState = PrivacyState.UNKNOWN,
        scales: list[MeaningScale] | None = None,
        replace_object: bool = True,
    ) -> list[MeaningUnit]:
        if replace_object and object_uid:
            self.store.clear_object(object_uid, commit_sha)
        units = unitise_text(
            text,
            source_object_id=source_object_id,
            scales=scales,
            object_uid=object_uid,
            commit_sha=commit_sha,
            rights=rights,
            privacy=privacy,
        )
        for unit in units:
            embedding = self.embedder.encode(unit.text)
            profile = self.tagger.profile_for(unit, embedding)
            self.store.upsert(unit, profile)
        return units

    def index_directory(
        self,
        root: Path,
        *,
        commit_sha: str | None = None,
        default_rights: RightsState = RightsState.PUBLIC,
        default_privacy: PrivacyState = PrivacyState.INTERNAL,
        skip_unknown_rights: bool = True,
    ) -> dict[str, int]:
        """Index all markdown files under root. Skip UNKNOWN rights when fail-closed."""
        root = Path(root)
        indexed = 0
        skipped = 0
        for path in sorted(root.rglob("*.md")):
            if path.name.lower() in {"readme.md", "index.md"}:
                skipped += 1
                continue
            text = path.read_text(encoding="utf-8")
            rights, privacy, body = _parse_rights_privacy(text, default_rights, default_privacy)
            if skip_unknown_rights and rights == RightsState.UNKNOWN:
                skipped += 1
                continue
            if not body.strip():
                skipped += 1
                continue
            rel = str(path.relative_to(root))
            uid = f"file-{hashlib_sha(rel)}"
            self.index_text(
                body,
                source_object_id=rel,
                object_uid=uid,
                commit_sha=commit_sha or "FILESYSTEM",
                rights=rights,
                privacy=privacy,
            )
            indexed += 1
        return {"indexed_files": indexed, "skipped_files": skipped, "store_count": self.count()}

    def profile_text(self, text: str) -> MeaningProfile:
        embedding = self.embedder.encode(text)
        unit = MeaningUnit(
            unit_id="ephemeral",
            scale=MeaningScale.SENTENCE,
            text=text,
        )
        return self.tagger.profile_for(unit, embedding)

    def similar(self, query: SimilarityQuery) -> SimilarityResultSet:
        if self.count() == 0:
            return SimilarityResultSet(
                query=query,
                hits=[],
                model_id=self.embedder.model_id,
                model_version=self.embedder.model_version,
                warnings=["meaning index is empty; run spws meaning index or index-library"],
            )

        def make_profile(text: str, embedding: list[float]) -> MeaningProfile:
            unit = MeaningUnit(unit_id="query", scale=MeaningScale.SENTENCE, text=text)
            return self.tagger.profile_for(unit, embedding)

        return similar(query, self.store, self.embedder, make_profile)

    def count(self) -> int:
        return self.store.count()


def hashlib_sha(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode()).hexdigest()[:12]


def _parse_rights_privacy(
    text: str,
    default_rights: RightsState,
    default_privacy: PrivacyState,
) -> tuple[RightsState, PrivacyState, str]:
    body = text
    rights = default_rights
    privacy = default_privacy
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1]
            body = parts[2].lstrip("\n")
            for line in fm.splitlines():
                if ":" not in line:
                    continue
                key, val = line.split(":", 1)
                key = key.strip().lower()
                val = val.strip().strip("\"'")
                if key == "rights":
                    try:
                        rights = RightsState(val)
                    except Exception:
                        rights = RightsState.UNKNOWN
                if key == "privacy":
                    try:
                        privacy = PrivacyState(val)
                    except Exception:
                        privacy = PrivacyState.UNKNOWN
    return rights, privacy, body
