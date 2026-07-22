"""Stress: rights/privacy fail-closed matrix across retrieval."""

from __future__ import annotations

import pytest

from spws_contracts_core.domain import (
    MeaningScale,
    PrivacyState,
    RightsState,
    SimilarityQuery,
    rights_allows_retrieval,
)
from spws_semantics import MeaningGauge
from pathlib import Path


@pytest.mark.parametrize(
    "rights,privacy,should_retrieve",
    [
        (RightsState.PUBLIC, PrivacyState.PUBLIC, True),
        (RightsState.INTERNAL, PrivacyState.INTERNAL, True),
        (RightsState.UNKNOWN, PrivacyState.PUBLIC, False),
        (RightsState.RESTRICTED_PENDING_REVIEW, PrivacyState.PRIVATE, False),
        (RightsState.RESTRICTED, PrivacyState.PRIVATE, False),
        (RightsState.PRIVATE, PrivacyState.PRIVATE, False),
        (RightsState.PUBLIC, PrivacyState.UNKNOWN, False),
    ],
)
def test_rights_privacy_retrieval_matrix(
    stress_config, rights, privacy, should_retrieve, tmp_path
):
    gauge = MeaningGauge(
        Path(stress_config.meaning_index_path) / f"m-{rights.value}-{privacy.value}",
        debug_hash_embeddings=True,
        require_model=False,
    )
    marker = f"UNIQUE_TOKEN_{rights.value}_{privacy.value}_XYZ"
    text = f"A pastoral line containing {marker} by the quiet river."
    uid = f"unit-{rights.value}-{privacy.value}"
    gauge.index_text(
        text,
        source_object_id=uid,
        object_uid=uid,
        rights=rights,
        privacy=privacy,
        scales=[MeaningScale.SENTENCE, MeaningScale.PHRASE],
    )
    hits = gauge.similar(SimilarityQuery(text=marker, result_limit=20))
    found = any(uid == h.object_uid or marker in (h.text or "") for h in hits.hits)
    if should_retrieve:
        assert found, f"expected retrieval for {rights}/{privacy}"
        assert rights_allows_retrieval(rights)
    else:
        assert not found, f"fail-closed violated for {rights}/{privacy}"
