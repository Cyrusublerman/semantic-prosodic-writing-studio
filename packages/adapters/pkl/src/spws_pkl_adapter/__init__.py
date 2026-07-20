"""SPWS PKL Library adapter."""

from __future__ import annotations

from .config import SpwsConfig, load_config
from .embeddings import EmbeddingRetriever, EmbeddingStore
from .facade import export_bundle, index_repository, query_index, validate_bundle
from .indexer.indexer import PKLIndexer
from .promotion.promotion import PromotionExporter
from .resolver.resolver import PKLResolver
from .retriever.retriever import PKLRetriever
from .snapshot.snapshot import FILESYSTEM_SHA, SnapshotReader, WORKING_TREE_SHA

__all__ = [
    "EmbeddingRetriever",
    "EmbeddingStore",
    "FILESYSTEM_SHA",
    "PKLIndexer",
    "PKLResolver",
    "PKLRetriever",
    "PromotionExporter",
    "SnapshotReader",
    "SpwsConfig",
    "WORKING_TREE_SHA",
    "export_bundle",
    "index_repository",
    "load_config",
    "query_index",
    "validate_bundle",
]

__version__ = "0.1.0"
