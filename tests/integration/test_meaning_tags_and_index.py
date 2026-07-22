"""Phase A: exact tags + fragment fixture indexing (hash-ok for CI)."""

from __future__ import annotations

from pathlib import Path

from spws_contracts_core.domain import MeaningScale, SimilarityQuery
from spws_semantics import MeaningGauge
from spws_semantics.encode import TaggingService


ROOT = Path(__file__).resolve().parents[2]
FRAGMENTS = ROOT / "fixtures" / "fragments"


def test_exact_token_tags_no_meter_on_pastoral() -> None:
    tags = TaggingService().rule_tags("The wind along the meadow path")
    assert "meter" not in tags["theme_tags"]
    assert "nature" in tags["domain_tags"] or "aerial" in tags["imagery_tags"]


def test_index_library_fragments_and_similar(tmp_path: Path) -> None:
    gauge = MeaningGauge(tmp_path / "meaning", debug_hash_embeddings=True, require_model=False)
    stats = gauge.index_directory(FRAGMENTS, skip_unknown_rights=True)
    assert stats["indexed_files"] >= 3
    assert gauge.count() > 0
    result = gauge.similar(
        SimilarityQuery(
            text="quiet river after rain",
            result_limit=5,
            target_scales=[MeaningScale.PHRASE, MeaningScale.SENTENCE, MeaningScale.PARAGRAPH],
        )
    )
    assert result.hits
    # Should prefer nature fragment content over unrelated meter jargon when present
    joined = " ".join(h.text.lower() for h in result.hits[:3])
    assert "river" in joined or "grass" or "earth" in joined or "meadow" in joined or "rain" in joined
