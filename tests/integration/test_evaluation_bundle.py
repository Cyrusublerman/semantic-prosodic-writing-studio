"""Phase 4: full D007 EvaluationBundle criteria."""

from __future__ import annotations

from pathlib import Path

from spws_analysis import analyze_poem, diagnose_poem
from spws_planning import confirm_work_plan, create_work_plan
from spws_revision import ALL_CRITERIA, revise_poetry
from spws_storage import load_config


def test_full_evaluation_bundle_criteria(tmp_path: Path, temp_workspace, monkeypatch) -> None:
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    config = load_config(temp_workspace["config_path"])
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
    plan = confirm_work_plan(
        create_work_plan(brief="improve diction", form="free_verse", diagnosis=diagnosis),
        confirmed=True,
    )
    result = revise_poetry(
        poem_path,
        brief="improve diction",
        config=config,
        diagnosis=diagnosis,
        work_plan=plan,
    )
    results = result["evaluation"]["results"]
    by_subject: dict[str, set[str]] = {}
    for row in results:
        by_subject.setdefault(row["subject_id"], set()).add(row["criterion"])
    assert by_subject
    for subject, criteria in by_subject.items():
        assert set(ALL_CRITERIA).issubset(criteria), f"{subject} missing {set(ALL_CRITERIA) - criteria}"

    measured = [r["measured_value"] for r in results if r.get("measured_value") is not None]
    assert measured
    assert len({round(float(v), 6) for v in measured}) > 1
    assert not all(abs(float(v) - 0.7) < 1e-9 for v in measured)

    # Operations carry improve/degrade lists
    ops = result.get("operations") or []
    assert ops
    assert any(
        (op.get("predicted_improvements") or []) and (op.get("predicted_degradations") or [])
        for op in ops
    ), "at least one operation must have non-empty predicted_improvements and predicted_degradations"
