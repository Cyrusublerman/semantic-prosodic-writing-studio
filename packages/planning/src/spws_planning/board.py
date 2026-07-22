"""Assemble a meaning-similarity source board. Quality mode: no demo seeds."""

from __future__ import annotations

from typing import Any

from spws_contracts_core.domain import SimilarityQuery
from spws_semantics import MeaningGauge
from spws_storage.config import SpwsConfig


def build_source_board(
    text: str,
    config: SpwsConfig,
    *,
    allow_empty_fail: bool = True,
    result_limit: int = 10,
) -> dict[str, Any]:
    """Query the meaning index and cluster hits by first theme tag.

    Fails closed when the meaning index is empty (no auto-seed in quality mode).
    """
    gauge = MeaningGauge.from_config(config)
    if gauge.count() == 0:
        msg = (
            "meaning index is empty; index Library fragments first "
            "(spws meaning index-library --root PATH) or spws meaning index FILE"
        )
        if allow_empty_fail:
            raise RuntimeError(msg)
        return {"query": SimilarityQuery(text=text).model_dump(mode="json"), "clusters": {}, "hit_count": 0, "warnings": [msg]}

    query = SimilarityQuery(text=text, result_limit=result_limit)
    result = gauge.similar(query)
    clusters: dict[str, list[dict[str, Any]]] = {}
    for hit in result.hits:
        tag = hit.theme_tags[0] if hit.theme_tags else "untagged"
        clusters.setdefault(tag, []).append(hit.model_dump(mode="json"))
    return {
        "query": query.model_dump(mode="json"),
        "clusters": clusters,
        "hit_count": len(result.hits),
        "warnings": list(result.warnings),
        "store_count": gauge.count(),
        "using_hash_embeddings": gauge.embedder.using_hash,
    }
