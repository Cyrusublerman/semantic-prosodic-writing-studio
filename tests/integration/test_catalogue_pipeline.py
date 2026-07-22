"""Catalogue propose → promotion draft → index → board hits."""

from __future__ import annotations

from pathlib import Path

from spws_contracts_core.domain import MeaningScale, PrivacyState, RightsState
from spws_planning import build_source_board
from spws_preprocessing import (
    list_pending,
    propose_fragments,
    save_review_bundle,
    to_promotion_draft,
)
from spws_semantics import MeaningGauge
from spws_storage import load_config


def test_catalogue_pipeline_to_board(tmp_path: Path, temp_workspace, monkeypatch, project_root) -> None:
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    config = load_config(temp_workspace["config_path"])

    poem = project_root / "fixtures" / "poetry" / "sample_poem.txt"
    assert poem.is_file()

    result = propose_fragments(poem)
    assert result["proposal_count"] >= 1
    proposals = result["proposals"]
    for proposal in proposals:
        assert proposal["authorship"] == "user"
        assert proposal["rights"] == RightsState.RESTRICTED_PENDING_REVIEW.value
        assert proposal["privacy"] == PrivacyState.PRIVATE.value
        assert proposal["review_status"] == "unreviewed"
        assert proposal["canonical"] is False
        assert proposal["fragment_type"]
        assert proposal["text"]
        assert "suggested_themes" in proposal
        assert "suggested_tone" in proposal
        # Never invent attribution beyond authorship class
        assert "author" not in proposal
        assert "license" not in proposal
        assert "attribution" not in proposal

    drafts = [to_promotion_draft(p) for p in proposals]
    for draft in drafts:
        assert draft["rights"] == RightsState.RESTRICTED_PENDING_REVIEW.value
        assert draft["privacy"] == PrivacyState.PRIVATE.value
        assert draft["authorship"] == "user"

    queue_dir = tmp_path / "review_queue"
    saved = save_review_bundle(proposals, queue_dir)
    assert Path(saved["path"]).is_file()
    pending = list_pending(queue_dir)
    assert len(pending) == 1
    assert pending[0]["bundle_id"] == saved["bundle_id"]

    # Index with public override so board retrieval is allowed in test
    meaning_root = Path(config.meaning_index_path)
    gauge = MeaningGauge(meaning_root, debug_hash_embeddings=True, require_model=False)
    for index, draft in enumerate(drafts):
        gauge.index_text(
            draft["content"],
            source_object_id=f"catalogue-draft-{index}",
            object_uid=f"catalogue-{index}",
            rights=RightsState.PUBLIC,
            privacy=PrivacyState.PUBLIC,
            scales=[MeaningScale.PHRASE, MeaningScale.SENTENCE],
        )
    assert gauge.count() >= 1

    board = build_source_board(drafts[0]["content"], config, allow_empty_fail=True, result_limit=8)
    assert board["hit_count"] >= 1
    flattened = [h for hits in board["clusters"].values() for h in hits]
    assert flattened
