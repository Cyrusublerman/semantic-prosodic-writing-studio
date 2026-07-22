"""Stress: assist modes + catalogue promotion defaults."""

from __future__ import annotations

import pytest

from spws_contracts_core.domain import RightsState
from spws_preprocessing import propose_fragments, to_promotion_draft
from spws_revision import assist_reword


@pytest.mark.parametrize("mode", ["rarefy", "ground_to_library", "meter_fit", "theme_align"])
def test_assist_modes_never_auto_apply(stress_config, seeded_gauge, mode):
    del seeded_gauge
    out = assist_reword(
        "The wind along the meadow path turns grass to gold",
        mode=mode,
        config=stress_config,
    )
    assert out.get("auto_apply") is False
    assert "candidates" in out
    for cand in out.get("candidates") or []:
        content = cand.get("content") or cand.get("revised") or ""
        if content:
            assert "\n" not in content.strip() or content.count("\n") == 0


def test_assist_unknown_mode_fails(stress_config):
    with pytest.raises((ValueError, KeyError, RuntimeError)):
        assist_reword("hello world line", mode="not_a_real_mode", config=stress_config)


def test_catalogue_never_invents_attribution_and_pending_rights(project_root):
    path = project_root / "fixtures" / "poetry" / "pastoral_12_lines.txt"
    result = propose_fragments(path)
    assert result["proposal_count"] >= 1
    for proposal in result["proposals"]:
        assert proposal["rights"] == RightsState.RESTRICTED_PENDING_REVIEW.value
        assert proposal["privacy"] == "private"
        assert proposal["review_status"] == "unreviewed"
        assert "author" not in proposal
        assert "license" not in proposal
        assert "attribution" not in proposal
        draft = to_promotion_draft(proposal)
        assert draft["rights"] == RightsState.RESTRICTED_PENDING_REVIEW.value
        assert "author" not in draft
