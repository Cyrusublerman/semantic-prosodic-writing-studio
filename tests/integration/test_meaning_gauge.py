"""Meaning gauge unitise/index/similar integration."""

from __future__ import annotations

from pathlib import Path

from spws_contracts_core.domain import MeaningScale, PrivacyState, RightsState, SimilarityQuery
from spws_semantics import MeaningGauge


def test_unitise_index_similar(tmp_path: Path) -> None:
    gauge = MeaningGauge(tmp_path / "meaning", debug_hash_embeddings=True, require_model=False)
    text = (
        "Meter and stress shape poetic rhythm.\n\n"
        "The quiet river holds a luminous dream of leaves."
    )
    units = gauge.index_text(
        text,
        source_object_id="fixture-a",
        rights=RightsState.PUBLIC,
        privacy=PrivacyState.PUBLIC,
    )
    assert units
    assert gauge.count() >= 2
    result = gauge.similar(
        SimilarityQuery(
            text="poetic meter rhythm",
            result_limit=5,
            target_scales=[MeaningScale.SENTENCE, MeaningScale.PARAGRAPH, MeaningScale.PHRASE],
        )
    )
    assert result.hits
    assert result.hits[0].explanation
    profile = gauge.profile_text("writing poems about nature")
    assert profile.theme_tags or profile.domain_tags or profile.affect_tags is not None


def test_pipelines_load() -> None:
    from spws_pipelines import load_pipeline

    for name in [
        "poetry_revision_v0",
        "source_ingestion_v0",
        "analysis_suite_v0",
        "source_board_v0",
        "local_revision_v0",
        "constrained_poetry_generation_v0",
    ]:
        pipe = load_pipeline(name)
        assert pipe.id
        assert pipe.steps
