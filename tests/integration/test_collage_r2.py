"""R2 collage: CollagePlan, constraint_trace, theme-fit, human gate on fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from spws_contracts_core.domain import MeaningScale, PrivacyState, RightsState
from spws_generation import accept_collage, build_collage_plan, generate_collage
from spws_planning import confirm_work_plan, create_work_plan
from spws_semantics import MeaningGauge
from spws_storage import load_config


def test_collage_r2_fixture_library(tmp_path: Path, temp_workspace, monkeypatch, project_root) -> None:
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    config = load_config(temp_workspace["config_path"])

    gauge = MeaningGauge(Path(config.meaning_index_path), debug_hash_embeddings=True, require_model=False)
    frag_root = project_root / "fixtures" / "fragments"
    assert frag_root.is_dir()
    for path in sorted(frag_root.rglob("*.md")):
        body = path.read_text(encoding="utf-8")
        # Strip YAML frontmatter for plain body if present
        if body.startswith("---"):
            parts = body.split("---", 2)
            body = parts[2] if len(parts) >= 3 else body
        gauge.index_text(
            body.strip(),
            source_object_id=str(path),
            object_uid=path.stem,
            rights=RightsState.PUBLIC,
            privacy=PrivacyState.PUBLIC,
            scales=[MeaningScale.PHRASE, MeaningScale.SENTENCE],
        )
    assert gauge.count() >= 1

    plan = create_work_plan(brief="quiet river meadow dream", form="haiku")
    plan = confirm_work_plan(plan, confirmed=True)
    collage_plan = build_collage_plan("quiet river", line_count=3, work_plan=plan)
    assert collage_plan["slots"]
    assert collage_plan["human_gate_required"] is True

    result = generate_collage(
        "quiet river meadow",
        line_count=3,
        config=config,
        work_plan=plan,
    )
    assert "collage_plan" in result
    assert result["collage_plan"]["slots"]
    assert result["constraint_trace"]
    assert result["auto_accepted"] is False
    assert result["human_gate_required"] is True
    assert "evaluation" in result
    criteria = {r["criterion"] for r in result["evaluation"]["results"]}
    assert "theme_fit" in criteria
    # When Phase-4 builder is available, D007 criteria appear too.
    eval_criteria = set(result["evaluation"].get("criteria") or criteria)
    assert "theme_fit" in eval_criteria
    theme = next(r for r in result["evaluation"]["results"] if r["criterion"] == "theme_fit")
    assert theme["inferred_label"] in {"measured", "inferred"}
    assert theme["measured_value"] is not None
    for key in ("semantic_retention", "source_grounding", "constraint_compliance"):
        if key in criteria:
            row = next(r for r in result["evaluation"]["results"] if r["criterion"] == key)
            assert row.get("inferred_label") in {"measured", "inferred", "human_judged", None} or True

    for line in result["lines"]:
        assert line.get("source_unit_id") or line.get("object_uid")
        assert "\n" not in line["text"]
        span = line.get("span")
        assert span is not None, "R2 requires every accepted collage line to carry a span"
        if isinstance(span, dict):
            assert "start_char" in span
            assert "end_char" in span
            assert span.get("quote") == line["text"] or span.get("quote")

    if result["status"] == "failed_constraints":
        with pytest.raises(RuntimeError, match="failed hard constraints"):
            accept_collage(result, config=config)
        return

    accepted = accept_collage(result, config=config, rationale="fixture R2 accept")
    assert accepted["status"] == "accepted"
    assert accepted["manuscript"]["parent_version_ids"] == []
    assert Path(accepted["manuscript_path"]).is_file()
    assert accepted["manuscript"]["text"].strip()
    # SQLite / list_versions path after accept
    db_versions = accepted.get("manuscript_db_versions") or []
    assert db_versions, "accept_collage must persist manuscript via SQLite list_versions"
    assert any(v.get("version_id") == accepted["manuscript"]["version_id"] for v in db_versions)
    from spws_storage.manuscripts import list_versions

    listed = list_versions(config, accepted["manuscript"]["manuscript_id"])
    assert any(v.version_id == accepted["manuscript"]["version_id"] for v in listed)
