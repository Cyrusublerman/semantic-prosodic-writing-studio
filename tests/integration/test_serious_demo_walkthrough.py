"""Serious capability walkthrough: revision, rights fail-closed, collage, assist, catalogue.

Run with: pytest tests/integration/test_serious_demo_walkthrough.py -v -s
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spws_analysis import analyse_document, analyze_poem, diagnose_poem
from spws_contracts_core.domain import (
    DialectCode,
    MeaningScale,
    PrivacyState,
    RightsState,
    SimilarityQuery,
)
from spws_generation import accept_collage, generate_collage
from spws_ingestion import import_file
from spws_planning import build_source_board, confirm_work_plan, create_work_plan
from spws_preprocessing import propose_fragments, to_promotion_draft
from spws_revision import assist_reword, decide_revision, propose_revision
from spws_semantics import MeaningGauge
from spws_storage import WorkspaceStore, load_config
from spws_storage.manuscripts import list_versions
from spws_wordrare_adapter import (
    constrained_search,
    form_scaffold,
    lexical_record,
    syllable_stress_rhyme,
)


def _banner(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def _index_fixture_fragments(gauge: MeaningGauge, project_root: Path) -> int:
    root = project_root / "fixtures" / "fragments"
    n = 0
    for path in sorted(root.rglob("*.md")):
        body = path.read_text(encoding="utf-8")
        if body.startswith("---"):
            parts = body.split("---", 2)
            body = parts[2] if len(parts) >= 3 else body
        body = body.strip()
        if not body:
            continue
        gauge.index_text(
            body,
            source_object_id=str(path),
            object_uid=path.stem,
            rights=RightsState.PUBLIC,
            privacy=PrivacyState.PUBLIC,
            scales=[MeaningScale.PHRASE, MeaningScale.SENTENCE],
        )
        n += 1
    # Extra retrieval seeds for pastoral / wind themes
    for index, text in enumerate(
        [
            "quiet river keeps a luminous measure under leaf-shadow",
            "zephyr edits the aureate meadow at dusk",
            "hushed earth remembers chronicles of seed and stone",
            "silver rain returns across the willow bend",
            "pastoral cadence of hill and rivulet song",
        ]
    ):
        gauge.index_text(
            text,
            source_object_id=f"seed-{index}",
            object_uid=f"seed-{index}",
            rights=RightsState.PUBLIC,
            privacy=PrivacyState.PUBLIC,
            scales=[MeaningScale.PHRASE, MeaningScale.SENTENCE],
        )
        n += 1
    return n


def test_serious_revision_walkthrough(tmp_path: Path, temp_workspace, monkeypatch, project_root, capsys):
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    config = load_config(temp_workspace["config_path"])

    gauge = MeaningGauge(Path(config.meaning_index_path), debug_hash_embeddings=True, require_model=False)
    indexed = _index_fixture_fragments(gauge, project_root)
    assert indexed >= 5

    # --- Rights fail-closed ---
    _banner("1. RIGHTS FAIL-CLOSED")
    gauge.index_text(
        "secret unpublished manuscript line about wind",
        source_object_id="secret",
        object_uid="secret-wind",
        rights=RightsState.UNKNOWN,
        privacy=PrivacyState.PRIVATE,
        scales=[MeaningScale.SENTENCE],
    )
    secret_hits = gauge.similar(
        SimilarityQuery(text="secret unpublished manuscript line about wind", result_limit=20)
    )
    secret_uids = {h.object_uid for h in secret_hits.hits}
    print(f"Indexed units (approx): {gauge.count()}")
    print(f"Retrieval hit object_uids (sample): {sorted(u for u in secret_uids if u)[:8]}")
    print(f"'secret-wind' in hits? {'secret-wind' in secret_uids} (must be False — UNKNOWN rights)")
    assert "secret-wind" not in secret_uids
    assert not any("unpublished manuscript" in (h.text or "") for h in secret_hits.hits)

    public_hits = gauge.similar(SimilarityQuery(text="quiet river meadow dusk", result_limit=5))
    print("Public retrieval sample:")
    for hit in public_hits.hits[:3]:
        print(f"  score={hit.score_combined:.3f}  {hit.text[:80]!r}")
    assert public_hits.hits

    # --- Adversarial poem: repetition ---
    poem_path = project_root / "fixtures" / "poetry" / "adversarial_repetition_14.txt"
    poem = poem_path.read_text(encoding="utf-8")
    lines = [ln for ln in poem.splitlines() if ln.strip()]
    assert 8 <= len(lines) <= 20

    _banner("2. IMPORT + ANALYSE (adversarial repetition poem)")
    package = import_file(poem_path)
    store = WorkspaceStore(config, workspace_root=temp_workspace["workspace"])
    raw = store.persist_input_package(package)
    print(f"RawSource id={raw.source_id}  rights={raw.rights}  lines={len(lines)}")
    print("Draft (first 4 lines):")
    for ln in lines[:4]:
        print(f"  | {ln}")

    suite = analyse_document(poem, kind="poem", config=config)
    analysis = analyze_poem(poem)
    diagnosis = diagnose_poem(poem, analysis, annotations=None)
    bundle = suite.get("bundle") or {}
    if hasattr(bundle, "model_dump"):
        bundle = bundle.model_dump(mode="json")
    components = sorted(
        k for k in (bundle.get("component_versions") or {}).keys() if k != "spws_analysis"
    )
    print(f"Analyser components: {components}")
    print(f"Field confidence: {suite.get('field_confidence')}")
    print(f"Disagreement warnings: {(bundle.get('warnings') or [])[:3]}")
    print(
        f"Diagnosis: type={diagnosis.problem_type}  "
        f"line={diagnosis.target_line_index}  brief={diagnosis.suggested_brief!r}"
    )
    print(f"  measured: {(diagnosis.measured_values if hasattr(diagnosis, 'measured_values') else {})}")
    assert len(components) >= 6
    assert diagnosis.problem_type == "repetition"
    assert diagnosis.target_line_index >= 0

    # --- Plan + revise ---
    _banner("3. PLAN CONFIRM → PROPOSE (≥2 families) → EVAL TRADE-OFFS")
    plan = create_work_plan(
        brief="reduce repetition and restore pastoral diction",
        form="free_verse",
        diagnosis=diagnosis,
    )
    assert (plan.get("work_specification") or {}).get("dialect_policy", {}).get("primary") == DialectCode.EN_AU.value
    plan = confirm_work_plan(plan, confirmed=True)

    proposal = propose_revision(
        poem_path,
        brief="reduce repetition and restore pastoral diction",
        config=config,
        diagnosis=diagnosis,
        work_plan=plan,
    )
    result = proposal["proposal"]
    candidates = result["candidate_set"]["candidates"]
    families = sorted({c.get("method_family") for c in candidates})
    print(f"Method families: {families}")
    print(f"Candidate count: {len(candidates)}")
    assert len(candidates) >= 2
    assert len(families) >= 2

    target_line = lines[diagnosis.target_line_index]
    print(f"Target line [{diagnosis.target_line_index}]: {target_line!r}")
    for cand in candidates[:4]:
        print(f"\n  [{cand['method_family']}] {cand['candidate_id']}")
        print(f"    content: {cand['content']!r}")
        assert "\n" not in cand["content"]
        assert cand.get("line_index") == diagnosis.target_line_index
        op = next(
            (o for o in (result.get("operations") or []) if o.get("candidate_id") == cand["candidate_id"]),
            None,
        )
        if op:
            print(f"    improves: {op.get('predicted_improvements')}")
            print(f"    degrades: {op.get('predicted_degradations')}")

    eval_results = (result.get("evaluation") or {}).get("results") or []
    criteria = sorted({r["criterion"] for r in eval_results})
    print(f"\nEvaluation criteria ({len(criteria)}): {criteria}")
    assert len(criteria) >= 10
    measured = [r["measured_value"] for r in eval_results if r.get("measured_value") is not None]
    assert measured and not all(abs(float(v) - 0.7) < 1e-9 for v in measured)

    # --- Decide + export ---
    _banner("4. HUMAN DECIDE → MANUSCRIPT LINEAGE → EXPORT PACK")
    cand_id = candidates[0]["candidate_id"]
    export_dir = tmp_path / "serious_export"
    decided = decide_revision(
        config,
        proposal["proposal_path"],
        candidate_id=cand_id,
        kind="accept",
        rationale="prefer first span-bounded alternative",
        export_dir=export_dir,
    )
    child = decided["manuscript"]
    versions = list_versions(config, child["manuscript_id"])
    print(f"Accepted candidate: {cand_id}")
    print(f"Parent versions: {child['parent_version_ids']}")
    print(f"Versions for manuscript: {len(versions)}")
    print("Revised target region (full text snippet):")
    for i, ln in enumerate(child["text"].splitlines()[:6]):
        mark = ">>" if i == diagnosis.target_line_index else "  "
        print(f"  {mark} {i}: {ln}")
    assert child["parent_version_ids"]
    assert len(versions) >= 2

    files = (decided.get("export") or {}).get("files") or {}
    print("Export files:")
    for key, path in sorted(files.items()):
        print(f"  {key}: {path}")
    assert Path(files["annotated.html"]).is_file()
    html = Path(files["annotated.html"]).read_text(encoding="utf-8")
    assert "semantic_retention" in html or "Evaluation" in html
    pub = (decided.get("export") or {}).get("publication_bundle")
    assert pub
    print(f"PublicationBundle keys: {sorted(pub.keys()) if isinstance(pub, dict) else type(pub)}")

    # keep capture for -s
    with capsys.disabled():
        pass


def test_serious_collage_and_assist(tmp_path: Path, temp_workspace, monkeypatch, project_root):
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    config = load_config(temp_workspace["config_path"])
    gauge = MeaningGauge(Path(config.meaning_index_path), debug_hash_embeddings=True, require_model=False)
    _index_fixture_fragments(gauge, project_root)

    _banner("5. COLLAGE R2 (theme → slots → human accept)")
    plan = confirm_work_plan(
        create_work_plan(brief="quiet river meadow pastoral dusk", form="haiku"),
        confirmed=True,
    )
    collage = generate_collage(
        "quiet river meadow dusk",
        line_count=3,
        config=config,
        work_plan=plan,
    )
    print(f"Collage status: {collage['status']}")
    print(f"Constraint trace ({len(collage['constraint_trace'])} events):")
    for event in collage["constraint_trace"][:8]:
        print(f"  {event}")
    print("Assembled text:")
    print(collage["text"])
    for line in collage["lines"]:
        assert line.get("span"), "every collage line needs span provenance"
        print(f"  span={line['span']}  unit={line.get('source_unit_id')}")

    if collage["status"] != "failed_constraints":
        accepted = accept_collage(collage, config=config, rationale="demo accept")
        print(f"Accepted collage → manuscript {accepted['manuscript']['version_id']}")
        assert accepted["status"] == "accepted"
    else:
        pytest.fail(f"collage underfilled: {collage.get('warnings')}")

    _banner("6. ASSIST MODES (no auto-apply)")
    selection = "The wind along the meadow path"
    for mode in ("rarefy", "ground_to_library", "meter_fit", "theme_align"):
        out = assist_reword(selection, mode=mode, config=config)
        assert out.get("auto_apply") is False
        cands = out.get("candidates") or []
        print(f"  mode={mode:18}  candidates={len(cands)}")
        if cands:
            print(f"    sample: {cands[0].get('content') or cands[0].get('revised')!r}")


def test_serious_catalogue_and_wordrare():
    _banner("7. CATALOGUE + WORDRARE CAPABILITIES")
    root = Path(__file__).resolve().parents[2]
    poem = root / "fixtures" / "poetry" / "pastoral_12_lines.txt"
    props = propose_fragments(poem)
    print(f"Proposals from pastoral poem: {props['proposal_count']}")
    assert props["proposal_count"] >= 1
    draft = to_promotion_draft(props["proposals"][0])
    print(f"Promotion draft rights={draft['rights']} privacy={draft['privacy']}")
    print(f"  title: {draft['title']!r}")
    assert draft["rights"] == RightsState.RESTRICTED_PENDING_REVIEW.value

    lex = lexical_record("meadow")
    syl = syllable_stress_rhyme("meadow")
    form = form_scaffold("haiku")
    search = constrained_search(min_rarity=0.0, max_rarity=1.0, limit=3)
    print(f"lexical_record: {lex['status']}  lemma={lex.get('record', {}).get('lemma')}")
    print(f"prosody: {syl['status']}  syllables={syl.get('syllable_count')}")
    print(f"form_scaffold(haiku): {form['status']}")
    print(f"constrained_search: {search['status']}  hits={len(search.get('hits') or [])}")
    assert lex["status"] == "ok"
    assert syl["status"] == "ok"
    assert form["status"] == "ok"
    assert search["status"] == "ok"
