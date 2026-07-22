"""Embedding and tagging services for MeaningUnits."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable

from spws_contracts_core.domain import MeaningProfile, MeaningUnit

_WORD_RE = re.compile(r"[a-zA-Z']+")

DOMAIN_SEEDS: dict[str, list[str]] = {
    "nature": ["nature", "river", "forest", "tree", "sky", "ocean", "stone", "wind", "leaf"],
    "emotion": ["love", "grief", "joy", "fear", "anger", "hope", "sorrow", "desire"],
    "time": ["time", "night", "day", "dawn", "dusk", "memory", "age", "moment"],
    "body": ["heart", "hand", "eye", "blood", "breath", "bone", "skin"],
    "urban": ["city", "street", "glass", "steel", "crowd", "room", "door"],
    "mythic": ["god", "spirit", "dream", "shadow", "ritual", "oracle", "fate"],
}

AFFECT_SEEDS: dict[str, list[str]] = {
    "melancholic": ["sad", "sorrow", "grief", "melancholy", "mournful", "gloomy", "wistful"],
    "joyful": ["happy", "joy", "delight", "cheerful", "merry", "bliss"],
    "fearful": ["fear", "terror", "dread", "anxiety", "ominous"],
    "tender": ["gentle", "soft", "tender", "warm", "quiet", "calm"],
    "fierce": ["fierce", "wild", "harsh", "violent", "sharp", "burning"],
}

IMAGERY_SEEDS: dict[str, list[str]] = {
    "visual": ["light", "dark", "colour", "color", "shadow", "gleam", "bright"],
    "auditory": ["sound", "silence", "echo", "voice", "whisper", "song"],
    "tactile": ["cold", "warm", "rough", "smooth", "touch", "weight"],
    "liquid": ["water", "rain", "river", "sea", "tear", "flood"],
    "aerial": ["wind", "sky", "cloud", "air", "flight", "smoke"],
}

THEME_SEEDS: dict[str, list[str]] = {
    "loss": ["loss", "absence", "gone", "empty", "fade", "death"],
    "longing": ["longing", "yearn", "desire", "want", "reach"],
    "renewal": ["renew", "begin", "bloom", "return", "birth", "spring"],
    "isolation": ["alone", "isolate", "solitude", "distant", "separate"],
    "connection": ["together", "bind", "join", "touch", "meet", "kin"],
    "meter": ["meter", "metre", "stress", "syllable", "iamb", "rhythm", "prosody"],
    "writing": ["writing", "poem", "prose", "word", "line", "verse", "text"],
}


def _hash_embedding(text: str, dims: int = 32) -> list[float]:
    values = [0.0] * dims
    for index, char in enumerate(text.encode("utf-8")):
        values[index % dims] += char / 255.0
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _WORD_RE.finditer(text)}


def _seed_hits(tokens: set[str], seeds: dict[str, list[str]]) -> list[str]:
    """Exact token match only — no substring overfire."""
    hits: list[str] = []
    for label, words in seeds.items():
        if any(word in tokens for word in words):
            hits.append(label)
    return hits


class EmbeddingService:
    """Encode text. Hash fallback only when debug_hash_embeddings is explicitly true."""

    def __init__(
        self,
        model_id: str = "sentence-transformers/all-MiniLM-L6-v2",
        model_version: str = "unspecified",
        *,
        debug_hash_embeddings: bool = False,
        require_model: bool = True,
    ) -> None:
        self.model_id = model_id
        self.model_version = model_version
        self.debug_hash_embeddings = debug_hash_embeddings
        self.require_model = require_model
        self._model = None
        self._tried = False

    def _load(self) -> None:
        if self._tried:
            return
        self._tried = True
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_id)
            if self.model_version == "unspecified":
                self.model_version = "loaded"
        except Exception:
            self._model = None
            if self.require_model and not self.debug_hash_embeddings:
                raise RuntimeError(
                    f"Embedding model {self.model_id} unavailable and debug_hash_embeddings is false"
                )

    @property
    def using_hash(self) -> bool:
        self._load()
        return self._model is None

    def encode(self, text: str) -> list[float]:
        self._load()
        if self._model is not None:
            vector = self._model.encode(text, normalize_embeddings=True)
            return [float(v) for v in vector.tolist()]
        if self.debug_hash_embeddings:
            return _hash_embedding(text)
        raise RuntimeError("No embedding model available")

    def encode_many(self, texts: Iterable[str]) -> list[list[float]]:
        return [self.encode(text) for text in texts]


class TaggingService:
    """Rule + embedding-seed tagging for meaning profiles."""

    def __init__(self, embedder: EmbeddingService | None = None) -> None:
        self.embedder = embedder
        self._seed_centroids: dict[str, dict[str, list[float]]] | None = None

    def rule_tags(self, text: str) -> dict[str, list[str]]:
        tokens = _tokens(text)
        return {
            "domain_tags": _seed_hits(tokens, DOMAIN_SEEDS),
            "affect_tags": _seed_hits(tokens, AFFECT_SEEDS),
            "imagery_tags": _seed_hits(tokens, IMAGERY_SEEDS),
            "theme_tags": _seed_hits(tokens, THEME_SEEDS),
            "register_tags": [],
        }

    def _ensure_centroids(self) -> None:
        if self._seed_centroids is not None or self.embedder is None:
            return
        centroids: dict[str, dict[str, list[float]]] = {}
        for family, seeds in [
            ("domain", DOMAIN_SEEDS),
            ("affect", AFFECT_SEEDS),
            ("imagery", IMAGERY_SEEDS),
            ("theme", THEME_SEEDS),
        ]:
            centroids[family] = {}
            for label, words in seeds.items():
                vectors = [self.embedder.encode(word) for word in words[:5]]
                dim = len(vectors[0])
                avg = [sum(row[i] for row in vectors) / len(vectors) for i in range(dim)]
                norm = math.sqrt(sum(v * v for v in avg)) or 1.0
                centroids[family][label] = [v / norm for v in avg]
        self._seed_centroids = centroids

    def embedding_tags(self, text: str, *, threshold: float = 0.5) -> dict[str, list[str]]:
        if self.embedder is None:
            return {"domain_tags": [], "affect_tags": [], "imagery_tags": [], "theme_tags": []}
        self._ensure_centroids()
        assert self._seed_centroids is not None
        query = self.embedder.encode(text)
        out: dict[str, list[str]] = {
            "domain_tags": [],
            "affect_tags": [],
            "imagery_tags": [],
            "theme_tags": [],
        }
        family_key = {
            "domain": "domain_tags",
            "affect": "affect_tags",
            "imagery": "imagery_tags",
            "theme": "theme_tags",
        }
        for family, labels in self._seed_centroids.items():
            scored = []
            for label, centroid in labels.items():
                scored.append((label, _cosine(query, centroid)))
            scored.sort(key=lambda item: item[1], reverse=True)
            out[family_key[family]] = [label for label, score in scored[:2] if score >= threshold]
        return out

    def profile_for(self, unit: MeaningUnit, embedding: list[float] | None = None) -> MeaningProfile:
        rule = self.rule_tags(unit.text)
        # Skip embedding tags when using hash vectors (unreliable centroids)
        use_emb = (
            self.embedder is not None
            and embedding is not None
            and not getattr(self.embedder, "using_hash", False)
        )
        emb_tags = (
            self.embedding_tags(unit.text)
            if use_emb
            else {"domain_tags": [], "affect_tags": [], "imagery_tags": [], "theme_tags": []}
        )

        def merge(a: list[str], b: list[str]) -> list[str]:
            return sorted(set(a) | set(b))

        rule_only = any(rule[k] for k in ("domain_tags", "affect_tags", "imagery_tags", "theme_tags"))
        emb_only = any(emb_tags[k] for k in ("domain_tags", "affect_tags", "imagery_tags", "theme_tags"))
        if use_emb and rule_only and emb_only:
            confidence = 0.85
        elif use_emb and emb_only:
            confidence = 0.7
        elif rule_only:
            confidence = 0.55
        else:
            confidence = 0.35

        return MeaningProfile(
            unit_id=unit.unit_id,
            embedding=embedding,
            model_id=self.embedder.model_id if self.embedder else None,
            model_version=self.embedder.model_version if self.embedder else None,
            domain_tags=merge(rule["domain_tags"], emb_tags["domain_tags"]),
            register_tags=rule["register_tags"],
            affect_tags=merge(rule["affect_tags"], emb_tags["affect_tags"]),
            imagery_tags=merge(rule["imagery_tags"], emb_tags["imagery_tags"]),
            theme_tags=merge(rule["theme_tags"], emb_tags["theme_tags"]),
            concept_ids=[],
            confidence=confidence,
            analyser="spws_semantics",
            analyser_version="0.1.0",
        )


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def stable_concept_id(label: str) -> str:
    return "concept-" + hashlib.sha256(label.encode()).hexdigest()[:10]
