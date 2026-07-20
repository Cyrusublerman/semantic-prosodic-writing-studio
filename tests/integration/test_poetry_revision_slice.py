from __future__ import annotations

from pathlib import Path

from spws_analysis import analyze_poem
from spws_contracts_core import PKLQuery
from spws_ingestion import import_file
from spws_pkl_adapter import index_repository, query_index
from spws_revision import generate_candidates, record_decision
from spws_contracts_core.domain import RevisionDecisionKind
from spws_storage import WorkspaceStore


def test_poetry_revision_slice(spws_config, temp_workspace, project_root):
    fixture_pkl = project_root / "fixtures" / "pkl"
    poem_path = project_root / "fixtures" / "poetry" / "sample_poem.txt"
    index_repository(fixture_pkl, cache_path=temp_workspace["cache"])
    hits = query_index(PKLQuery(text="meter", result_limit=3), temp_workspace["cache"])
    assert hits

    store = WorkspaceStore(spws_config, workspace_root=temp_workspace["workspace"])
    package = import_file(poem_path)
    raw = store.persist_input_package(package)
    analysis = analyze_poem(package.text or "", hits)
    assert analysis.lines
    candidates = generate_candidates(package.text or "", analysis)
    decision = record_decision(
        store,
        run_id="run-test",
        candidates=candidates,
        text=package.text or "",
        kind=RevisionDecisionKind.ACCEPT if candidates else RevisionDecisionKind.DEFER,
        candidate_ids=[candidates[0].candidate_id] if candidates else [],
    )
    assert decision.decision_id
    assert store.get_raw_source(raw.source_id).text
    if analysis.pkl_evidence_count:
        assert any(line.evidence for line in analysis.lines)
    store.close()
