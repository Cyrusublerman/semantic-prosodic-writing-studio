"""R1 vertical slice: import → analyse → AU plan → ≥2 families → accept → export."""

from __future__ import annotations

from pathlib import Path

import pytest

from spws_analysis import analyse_document, diagnose_poem, analyze_poem
from spws_contracts_core.domain import DialectCode, MeaningScale, PrivacyState, RightsState
from spws_ingestion import import_file
from spws_planning import confirm_work_plan, create_work_plan
from spws_revision import (
    RestrictedSourceError,
    decide_revision,
    filter_restricted_source_hits,
    propose_revision,
)
from spws_semantics import MeaningGauge
from spws_storage import WorkspaceStore, load_config
from spws_storage.manuscripts import list_versions


def test_r1_vertical_slice_pastoral(tmp_path: Path, temp_workspace, monkeypatch, project_root) -> None:
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    config = load_config(temp_workspace["config_path"])

    gauge = MeaningGauge(Path(config.meaning_index_path), debug_hash_embeddings=True, require_model=False)
    for index, fragment in enumerate(
        [
            "quiet river luminous dream of leaves",
            "zephyr over aureate meadow grass",
            "hushed earth remembers ancient chronicles",
            "pastoral metre of dusk and hill",
            "silver rain along the willow bend",
        ]
    ):
        gauge.index_text(
            fragment,
            source_object_id=f"r1-frag-{index}",
            object_uid=f"r1-{index}",
            rights=RightsState.PUBLIC,
            privacy=PrivacyState.PUBLIC,
            scales=[MeaningScale.PHRASE, MeaningScale.SENTENCE],
        )

    poem_path = project_root / "fixtures" / "poetry" / "pastoral_12_lines.txt"
    assert poem_path.is_file()
    lines = [ln for ln in poem_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert 8 <= len(lines) <= 20

    package = import_file(poem_path)
    store = WorkspaceStore(config, workspace_root=temp_workspace["workspace"])
    raw = store.persist_input_package(package)
    assert raw.text

    poem = package.text or ""
    suite = analyse_document(poem, kind="poem", config=config)
    analysis = analyze_poem(poem)
    diagnosis = diagnose_poem(poem, analysis, annotations=None)
    assert suite.get("diagnosis") is not None or diagnosis.problem_type

    plan = create_work_plan(brief="improve diction", form="free_verse", diagnosis=diagnosis)
    dialect = (plan.get("work_specification") or {}).get("dialect_policy") or {}
    assert dialect.get("primary") == DialectCode.EN_AU.value
    plan = confirm_work_plan(plan, confirmed=True)
    assert plan["confirmed"] is True

    proposal = propose_revision(
        poem_path, brief="improve diction", config=config, diagnosis=diagnosis, work_plan=plan
    )
    families = set(proposal["proposal"].get("method_families") or [])
    candidates = proposal["proposal"]["candidate_set"]["candidates"]
    assert candidates
    assert len(families) >= 2 or len({c["method_family"] for c in candidates}) >= 2

    cand_id = candidates[0]["candidate_id"]
    export_dir = tmp_path / "export_pack"
    decided = decide_revision(
        config,
        proposal["proposal_path"],
        candidate_id=cand_id,
        kind="accept",
        store=store,
        export_dir=export_dir,
    )
    assert decided["decision"]["kind"] == "accept"
    child = decided["manuscript"]
    assert child["parent_version_ids"]
    assert Path(decided["manuscript_path"]).is_file()
    assert Path(decided["parent_manuscript_path"]).is_file()

    versions = list_versions(config, child["manuscript_id"])
    assert len(versions) >= 2
    assert any(v.parent_version_ids for v in versions)
    assert any(not v.parent_version_ids for v in versions)

    files = decided["export"]["files"]
    for key in ("annotated.html", "clean.txt", "bundle.json", "provenance.md", "version_diff.md"):
        assert Path(files[key]).is_file(), key
    html = Path(files["annotated.html"]).read_text(encoding="utf-8")
    assert "<html" in html.lower()
    assert "diagnosis" in html.lower() or "evaluation" in html.lower() or "Text" in html
    assert (export_dir / "clean.txt").read_text(encoding="utf-8").strip()
    assert "publication_bundle" in decided["export"]
    assert decided["export"]["publication_bundle"].get("manuscript_id")
    envelopes = proposal.get("envelopes") or proposal["proposal"].get("envelopes")
    assert envelopes and "candidate_set" in envelopes and "evaluation" in envelopes

    store.close()


def test_refuse_restricted_source_candidates() -> None:
    hits = [
        {"unit_id": "u-public", "rights": RightsState.PUBLIC.value, "text": "ok"},
        {"unit_id": "u-restricted", "rights": RightsState.RESTRICTED.value, "text": "no"},
        {
            "unit_id": "u-pending",
            "rights": RightsState.RESTRICTED_PENDING_REVIEW.value,
            "text": "nope",
        },
    ]
    kept, warnings = filter_restricted_source_hits(hits, config=None)
    assert [h["unit_id"] for h in kept] == ["u-public"]
    assert len(warnings) == 2

    with pytest.raises(RestrictedSourceError):
        filter_restricted_source_hits(
            [{"unit_id": "bad", "rights": "restricted"}],
            config=None,
            raise_on_restricted=True,
        )
