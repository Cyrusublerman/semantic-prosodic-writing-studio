"""Phase E: propose → decide accept → ManuscriptVersion + D014 export pack."""

from __future__ import annotations

from pathlib import Path

from spws_analysis import diagnose_poem, analyze_poem
from spws_contracts_core.domain import MeaningScale
from spws_planning import confirm_work_plan, create_work_plan
from spws_revision import decide_revision, propose_revision
from spws_semantics import MeaningGauge
from spws_storage import load_config


def test_propose_decide_export_pack(tmp_path: Path, temp_workspace, monkeypatch) -> None:
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    config = load_config(temp_workspace["config_path"])

    gauge = MeaningGauge(Path(config.meaning_index_path), debug_hash_embeddings=True, require_model=False)
    for index, fragment in enumerate(
        [
            "quiet river luminous dream of leaves",
            "zephyr over aureate meadow grass",
            "hushed earth remembers ancient chronicles",
        ]
    ):
        gauge.index_text(
            fragment,
            source_object_id=f"e-frag-{index}",
            object_uid=f"e-{index}",
            scales=[MeaningScale.PHRASE, MeaningScale.SENTENCE],
        )

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

    proposal = propose_revision(
        poem_path, brief="improve diction", config=config, diagnosis=diagnosis, work_plan=plan
    )
    assert proposal["proposal_path"]
    candidates = proposal["proposal"]["candidate_set"]["candidates"]
    assert candidates
    cand_id = candidates[0]["candidate_id"]

    export_dir = tmp_path / "export_pack"
    decided = decide_revision(
        config,
        proposal["proposal_path"],
        candidate_id=cand_id,
        kind="accept",
        export_dir=export_dir,
    )
    assert decided["decision"]["kind"] == "accept"
    assert decided["manuscript"]["parent_version_ids"]
    assert Path(decided["manuscript_path"]).is_file()
    assert decided["export"]
    files = decided["export"]["files"]
    for key in (
        "clean.txt",
        "clean.md",
        "annotated.md",
        "annotated.html",
        "bundle.json",
        "provenance.md",
        "version_diff.md",
    ):
        assert Path(files[key]).is_file(), key
    assert (export_dir / "clean.txt").read_text(encoding="utf-8").strip()
    html = Path(files["annotated.html"]).read_text(encoding="utf-8")
    assert "semantic_retention" in html
    assert decided["export"].get("publication_bundle")
    assert decided["export"]["publication_bundle"].get("bundle_id")
    envelopes = proposal.get("envelopes") or proposal["proposal"].get("envelopes")
    assert envelopes
    assert envelopes["candidate_set"]["object_type"] == "CandidateSet"
    assert envelopes["evaluation"]["object_type"] == "EvaluationBundle"
    # D007 human preference recorded after decide
    ev = decided.get("evaluation") or {}
    prefs = [r for r in (ev.get("results") or []) if r.get("criterion") == "human_preference"]
    assert prefs
    assert any(r.get("human_judgement") for r in prefs)
