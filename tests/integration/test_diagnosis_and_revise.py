"""Diagnosis + span-bounded revise_poetry with debug-hash MeaningGauge."""

from __future__ import annotations

from pathlib import Path

from spws_analysis import analyse_document, diagnose_poem, analyze_poem
from spws_contracts_core.domain import MeaningScale
from spws_planning import confirm_work_plan, create_work_plan
from spws_revision import revise_poetry
from spws_semantics import MeaningGauge
from spws_storage import load_config


def test_diagnose_and_revise_span_bounded(tmp_path: Path, temp_workspace, monkeypatch) -> None:
    # Ensure config uses hash embeddings + meaning store under tmp cache
    config_path = temp_workspace["config_path"]
    monkeypatch.setenv("SPWS_CONFIG", str(config_path))
    config = load_config(config_path)

    meaning_root = Path(config.meaning_index_path)
    gauge = MeaningGauge(meaning_root, debug_hash_embeddings=True, require_model=False)
    fragments = [
        "quiet river luminous dream of leaves",
        "zephyr over aureate meadow grass",
        "hushed earth remembers ancient chronicles",
        "Meter and stress shape poetic rhythm.",
    ]
    for index, fragment in enumerate(fragments):
        gauge.index_text(
            fragment,
            source_object_id=f"fixture-frag-{index}",
            object_uid=f"frag-{index}",
            scales=[MeaningScale.PHRASE, MeaningScale.SENTENCE],
        )
    assert gauge.count() >= 1

    poem = (
        "The wind along the meadow path\n"
        "Turns every blade of grass to gold,\n"
        "And in the quiet after rain\n"
        "The earth remembers stories old."
    )
    poem_path = tmp_path / "poem.txt"
    poem_path.write_text(poem, encoding="utf-8")

    analysis = analyze_poem(poem)
    diagnosis = diagnose_poem(poem, analysis, annotations=None)
    assert diagnosis.target_line_index >= 0
    assert diagnosis.problem_type in {
        "meter_break",
        "rarity_gap",
        "theme_drift",
        "repetition",
        "diction",
    }

    suite = analyse_document(poem, kind="poem", config=config)
    assert suite["diagnosis"] is not None
    assert suite["field_confidence"]["syllable"] in {0.5, 0.9}
    assert "semantic" in suite["field_confidence"]

    plan = create_work_plan(brief="improve diction", form="free_verse", diagnosis=diagnosis)
    assert plan["confirmed"] is False
    plan = confirm_work_plan(plan, confirmed=True)
    assert plan["confirmed"] is True
    assert plan["confirmed_at"]

    result = revise_poetry(
        poem_path,
        brief="improve diction",
        config=config,
        diagnosis=diagnosis,
        work_plan=plan,
    )
    assert result["status"] == "awaiting_human_decision"
    candidates = result["candidate_set"]["candidates"]
    assert candidates

    poem_line_count = len(poem.splitlines())
    for cand in candidates:
        content = cand["content"]
        assert "\n" not in content, "candidate must not paste whole-poem / multi-line"
        assert cand.get("line_index") == diagnosis.target_line_index
        # Span-bound: replacement roughly line-sized
        target_line = poem.splitlines()[diagnosis.target_line_index]
        assert len(content) <= int(1.3 * max(len(target_line), 1)) + 5
        # Must not equal full poem
        assert content.strip() != poem.strip()
        assert content.count("\n") == 0
        # Sanity: candidate is not all poem lines joined
        assert len(content.splitlines()) == 1
        assert len([ln for ln in content.splitlines() if ln.strip()]) <= 1

    # Evaluation measured_value must not be a constant placeholder 0.7 for all
    measured = [
        r["measured_value"]
        for r in result["evaluation"]["results"]
        if r.get("measured_value") is not None
    ]
    assert measured
    assert not all(abs(float(v) - 0.7) < 1e-9 for v in measured)

    # Unconfirmed plan must refuse revise
    dirty = confirm_work_plan(create_work_plan("x", diagnosis=diagnosis), confirmed=False)
    try:
        revise_poetry(poem_path, config=config, diagnosis=diagnosis, work_plan=dirty)
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "not confirmed" in str(exc).lower()
    assert raised

    # Silence unused in assertion path
    assert poem_line_count >= 3
