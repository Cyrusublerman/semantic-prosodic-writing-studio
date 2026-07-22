"""Phase 3: analysis fan-out across six components + diagnosis signals."""

from __future__ import annotations

from pathlib import Path

from spws_analysis import analyse_document, diagnose_poem, analyze_poem
from spws_storage import load_config

ROOT = Path(__file__).resolve().parents[2]
PASTORAL = ROOT / "fixtures" / "poetry" / "pastoral_12_lines.txt"

REQUIRED_COMPONENTS = {
    "lexical",
    "prosodic",
    "semantic",
    "structural",
    "repetition_motif",
    "provenance",
}


def test_analyse_pastoral_fanout(temp_workspace, monkeypatch) -> None:
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    config = load_config(temp_workspace["config_path"])
    poem = PASTORAL.read_text(encoding="utf-8")
    assert len([ln for ln in poem.splitlines() if ln.strip()]) >= 10

    result = analyse_document(poem, kind="poem", config=config)
    bundle = result["bundle"]
    versions = bundle.get("component_versions") or {}
    present = set(versions) & REQUIRED_COMPONENTS
    if present != REQUIRED_COMPONENTS:
        # Fallback: annotations from each analyser
        analysers = {a.get("analyser") for a in bundle.get("annotations") or []}
        assert REQUIRED_COMPONENTS.issubset(analysers | present), (
            f"missing components; versions={versions} analysers={analysers}"
        )
    else:
        assert present == REQUIRED_COMPONENTS

    # Field confidence must not be a universal 0.7 constant
    conf = result.get("field_confidence") or {}
    values = [float(v) for v in conf.values() if v is not None]
    assert values
    assert not all(abs(v - 0.7) < 1e-9 for v in values)

    assert result["diagnosis"] is not None
    assert result["diagnosis"]["problem_type"] in {
        "meter_break",
        "rarity_gap",
        "theme_drift",
        "repetition",
        "diction",
    }


def test_repetition_fixture_can_emit_repetition(temp_workspace, monkeypatch) -> None:
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    config = load_config(temp_workspace["config_path"])
    poem = PASTORAL.read_text(encoding="utf-8")
    result = analyse_document(poem, kind="poem", config=config)
    annotations = result["bundle"]["annotations"]
    poetry = analyze_poem(poem)
    diagnosis = diagnose_poem(poem, poetry, annotations)
    assert diagnosis.problem_type in {
        "meter_break",
        "rarity_gap",
        "theme_drift",
        "repetition",
        "diction",
    }
    # Pastoral fixture duplicates a brook line → repetition should be available
    rep_metrics = next(
        (a for a in annotations if a.get("feature") == "repetition_metrics"),
        None,
    )
    assert rep_metrics is not None
    ratio = float((rep_metrics.get("value") or {}).get("repetition_ratio") or 0)
    assert ratio > 0 or diagnosis.problem_type == "repetition"
