"""Stress: revision propose/decide under pressure (span bounds, families, eval, rights)."""

from __future__ import annotations

from pathlib import Path

import pytest

from spws_analysis import analyze_poem, diagnose_poem
from spws_contracts_core.domain import DialectCode
from spws_orchestration.llm_socket import LLMMethodFamilyDisabled, assert_method_family_allowed
from spws_planning import confirm_work_plan, create_work_plan
from spws_revision import decide_revision, propose_revision, revise_poetry
from spws_storage.manuscripts import list_versions


REQUIRED_CRITERIA = {
    "semantic_retention",
    "grammatical_acceptability",
    "pronunciation_confidence",
    "syllable_fit",
    "stress_metre_fit",
    "rhyme_fit",
    "register_voice",
    "repetition_motif",
    "source_grounding",
    "quotation_risk",
    "constraint_compliance",
    "human_preference",
}


@pytest.mark.parametrize(
    "fixture",
    [
        "adversarial_repetition_14.txt",
        "pastoral_12_lines.txt",
        "stress_unicode_meter.txt",
        "stress_long_20.txt",
    ],
)
def test_revise_span_bounded_two_families(
    stress_config, seeded_gauge, project_root, tmp_path, fixture
):
    del seeded_gauge  # ensure index side-effect
    path = project_root / "fixtures" / "poetry" / fixture
    poem = path.read_text(encoding="utf-8")
    lines = [ln for ln in poem.splitlines() if ln.strip()]
    analysis = analyze_poem(poem)
    diagnosis = diagnose_poem(poem, analysis, annotations=None)
    plan = confirm_work_plan(
        create_work_plan(brief="stress revise", form="free_verse", diagnosis=diagnosis),
        confirmed=True,
    )
    dialect = (plan.get("work_specification") or {}).get("dialect_policy") or {}
    assert dialect.get("primary") == DialectCode.EN_AU.value

    proposal = propose_revision(
        path, brief="stress revise", config=stress_config, diagnosis=diagnosis, work_plan=plan
    )
    result = proposal["proposal"]
    candidates = result["candidate_set"]["candidates"]
    assert len(candidates) >= 2
    families = {c.get("method_family") for c in candidates}
    assert len(families) >= 2

    target = lines[diagnosis.target_line_index]
    for cand in candidates:
        content = cand["content"]
        assert "\n" not in content
        assert cand.get("line_index") == diagnosis.target_line_index
        assert content.strip() != poem.strip()
        assert len(content) <= int(1.5 * max(len(target), 1)) + 40

    criteria = {r["criterion"] for r in (result.get("evaluation") or {}).get("results") or []}
    assert REQUIRED_CRITERIA <= criteria
    measured = [
        r["measured_value"]
        for r in result["evaluation"]["results"]
        if r.get("measured_value") is not None
    ]
    assert measured and not all(abs(float(v) - 0.7) < 1e-9 for v in measured)

    # Unconfirmed plan must refuse
    dirty = confirm_work_plan(create_work_plan("x", diagnosis=diagnosis), confirmed=False)
    with pytest.raises(RuntimeError, match="not confirmed"):
        revise_poetry(path, config=stress_config, diagnosis=diagnosis, work_plan=dirty)

    export_dir = tmp_path / f"export-{fixture}"
    decided = decide_revision(
        stress_config,
        proposal["proposal_path"],
        candidate_id=candidates[0]["candidate_id"],
        kind="accept",
        rationale="stress accept",
        export_dir=export_dir,
    )
    child = decided["manuscript"]
    assert child["parent_version_ids"]
    assert len(list_versions(stress_config, child["manuscript_id"])) >= 2
    files = decided["export"]["files"]
    assert Path(files["annotated.html"]).is_file()
    html = Path(files["annotated.html"]).read_text(encoding="utf-8")
    assert "semantic_retention" in html or "Evaluation" in html
    # human preference filled on decide
    eval_after = decided.get("export") or {}
    assert eval_after.get("publication_bundle") or decided.get("decision")


def test_llm_method_family_fail_closed():
    assert_method_family_allowed("rare_lexical")
    assert_method_family_allowed("fragment_informed")
    with pytest.raises(LLMMethodFamilyDisabled):
        assert_method_family_allowed("llm_bounded")
    with pytest.raises(LLMMethodFamilyDisabled):
        assert_method_family_allowed("llm_chat")


def test_reject_retains_decision_without_child_merge(
    stress_config, seeded_gauge, project_root, tmp_path
):
    del seeded_gauge
    path = project_root / "fixtures" / "poetry" / "pastoral_12_lines.txt"
    poem = path.read_text(encoding="utf-8")
    diagnosis = diagnose_poem(poem, analyze_poem(poem), annotations=None)
    plan = confirm_work_plan(
        create_work_plan("reject path", form="free_verse", diagnosis=diagnosis),
        confirmed=True,
    )
    proposal = propose_revision(
        path, brief="reject path", config=stress_config, diagnosis=diagnosis, work_plan=plan
    )
    cand = proposal["proposal"]["candidate_set"]["candidates"][0]["candidate_id"]
    decided = decide_revision(
        stress_config,
        proposal["proposal_path"],
        candidate_id=cand,
        kind="reject",
        rationale="not useful",
        export_dir=tmp_path / "reject-export",
    )
    assert decided["decision"]["kind"] == "reject"
    # parent text unchanged on reject
    assert decided["manuscript"]["text"].strip() == poem.strip()
