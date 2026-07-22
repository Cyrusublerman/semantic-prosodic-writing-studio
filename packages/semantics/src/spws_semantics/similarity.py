"""Hybrid similarity ranking over MeaningStore."""

from __future__ import annotations

import math

from spws_contracts_core.domain import (
    MeaningProfile,
    MeaningUnit,
    PrivacyState,
    RightsState,
    SimilarityHit,
    SimilarityQuery,
    SimilarityResultSet,
)

from .encode import EmbeddingService
from .index import MeaningStore


def cosine(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def tag_jaccard(a: MeaningProfile, b: MeaningProfile) -> float:
    left = set(a.domain_tags + a.affect_tags + a.imagery_tags + a.theme_tags)
    right = set(b.domain_tags + b.affect_tags + b.imagery_tags + b.theme_tags)
    if not left and not right:
        return 0.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def graph_score(a: MeaningProfile, b: MeaningProfile) -> float:
    left = set(a.concept_ids)
    right = set(b.concept_ids)
    if not left or not right:
        # soft proxy: shared theme tags
        themes = set(a.theme_tags) & set(b.theme_tags)
        return min(1.0, 0.25 * len(themes))
    return len(left & right) / len(left | right)


def hybrid_score(
    query_profile: MeaningProfile,
    candidate_profile: MeaningProfile,
    *,
    weight_vector: float,
    weight_tags: float,
    weight_graph: float,
) -> tuple[float, float, float, float]:
    sv = cosine(query_profile.embedding, candidate_profile.embedding)
    st = tag_jaccard(query_profile, candidate_profile)
    sg = graph_score(query_profile, candidate_profile)
    total_w = weight_vector + weight_tags + weight_graph
    if total_w <= 0:
        total_w = 1.0
    combined = (weight_vector * sv + weight_tags * st + weight_graph * sg) / total_w
    return combined, sv, st, sg


def _allowed(
    unit: MeaningUnit,
    query: SimilarityQuery,
) -> bool:
    from spws_contracts_core.domain import rights_allows_retrieval

    # Fail closed: unknown / pending-review / restricted never retrieve (D006).
    if not rights_allows_retrieval(unit.rights):
        return False
    if unit.privacy == PrivacyState.UNKNOWN:
        return False
    if query.rights_allowed and unit.rights not in query.rights_allowed:
        return False
    if query.privacy_allowed and unit.privacy not in query.privacy_allowed:
        return False
    if query.commit and unit.commit_sha and unit.commit_sha != query.commit:
        return False
    if query.themes:
        return True  # theme filter applied via profile below
    return True


def similar(
    query: SimilarityQuery,
    store: MeaningStore,
    embedder: EmbeddingService,
    tagger_profile_for_text,
) -> SimilarityResultSet:
    """Run hybrid similarity. tagger_profile_for_text(text, embedding) -> MeaningProfile."""
    if query.unit_id:
        unit = store.get_unit(query.unit_id)
        profile = store.get_profile(query.unit_id) if unit else None
        if unit is None or profile is None:
            return SimilarityResultSet(query=query, hits=[], warnings=["unknown unit_id"])
        query_text = unit.text
        query_profile = profile
    else:
        query_text = query.text or ""
        embedding = embedder.encode(query_text)
        query_profile = tagger_profile_for_text(query_text, embedding)

    scales = query.target_scales or None
    candidates = store.all_with_profiles(scales=scales)
    hits: list[SimilarityHit] = []
    for unit, profile in candidates:
        if query.unit_id and unit.unit_id == query.unit_id:
            continue
        if not _allowed(unit, query):
            continue
        if query.themes:
            if not set(query.themes) & set(profile.theme_tags + profile.domain_tags):
                continue
        if query.fragment_types and unit.source_object_id:
            # fragment_type filter is soft without catalogue join
            pass
        combined, sv, st, sg = hybrid_score(
            query_profile,
            profile,
            weight_vector=query.weight_vector,
            weight_tags=query.weight_tags,
            weight_graph=query.weight_graph,
        )
        explanation = f"vector={sv:.3f} tags={st:.3f} graph={sg:.3f}"
        hits.append(
            SimilarityHit(
                unit_id=unit.unit_id,
                text=unit.text,
                scale=unit.scale,
                score_combined=combined,
                score_vector=sv,
                score_tags=st,
                score_graph=sg,
                explanation=explanation,
                object_uid=unit.object_uid,
                span=unit.span,
                theme_tags=profile.theme_tags,
                path=unit.source_object_id,
            )
        )
    hits.sort(key=lambda item: item.score_combined, reverse=True)
    return SimilarityResultSet(
        query=query,
        hits=hits[: query.result_limit],
        model_id=embedder.model_id,
        model_version=embedder.model_version,
        warnings=[],
    )
