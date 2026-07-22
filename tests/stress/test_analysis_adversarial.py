"""Stress: analysis suite on adversarial / unicode / edge poems."""

from __future__ import annotations

from pathlib import Path

import pytest

from spws_analysis import analyse_document, analyze_poem, diagnose_poem


def _poem(project_root: Path, name: str) -> Path:
    path = project_root / "fixtures" / "poetry" / name
    assert path.is_file(), path
    return path


@pytest.mark.parametrize(
    "fixture,expect_problem",
    [
        ("adversarial_repetition_14.txt", "repetition"),
        ("pastoral_12_lines.txt", None),
        ("stress_unicode_meter.txt", None),
        ("stress_long_20.txt", None),
    ],
)
def test_analyse_fixture_shapes(stress_config, project_root, fixture, expect_problem):
    path = _poem(project_root, fixture)
    poem = path.read_text(encoding="utf-8")
    suite = analyse_document(poem, kind="poem", config=stress_config)
    bundle = suite["bundle"]
    if hasattr(bundle, "model_dump"):
        bundle = bundle.model_dump(mode="json")
    components = {
        k for k in (bundle.get("component_versions") or {}) if k != "spws_analysis"
    }
    assert components >= {
        "lexical",
        "prosodic",
        "semantic",
        "structural",
        "repetition_motif",
        "provenance",
    }
    assert suite.get("field_confidence")
    # Never all identical placeholder confidence
    confs = [float(v) for v in suite["field_confidence"].values()]
    assert confs
    assert not all(abs(c - 0.7) < 1e-9 for c in confs)

    diagnosis = suite.get("diagnosis")
    if isinstance(diagnosis, dict):
        problem = diagnosis.get("problem_type")
        line = diagnosis.get("target_line_index")
    else:
        problem = getattr(diagnosis, "problem_type", None)
        line = getattr(diagnosis, "target_line_index", None)
    assert problem
    assert line is not None and int(line) >= 0
    if expect_problem:
        assert problem == expect_problem


def test_analyse_emptyish_does_not_crash(stress_config, project_root):
    path = _poem(project_root, "stress_emptyish.txt")
    poem = path.read_text(encoding="utf-8")
    suite = analyse_document(poem, kind="poem", config=stress_config)
    assert "bundle" in suite


def test_unicode_spans_are_codepoint_consistent(stress_config, project_root):
    poem = _poem(project_root, "stress_unicode_meter.txt").read_text(encoding="utf-8")
    suite = analyse_document(poem, kind="poem", config=stress_config)
    bundle = suite["bundle"]
    if hasattr(bundle, "model_dump"):
        bundle = bundle.model_dump(mode="json")
    for ann in bundle.get("annotations") or []:
        loc = ann.get("location") or {}
        start, end = loc.get("start_char"), loc.get("end_char")
        if start is None or end is None:
            continue
        assert 0 <= start <= end <= len(poem)
        quote = loc.get("quote")
        if quote:
            assert poem[start:end] == quote or quote in poem


def test_diagnosis_measured_values_present_on_repetition(project_root):
    poem = _poem(project_root, "adversarial_repetition_14.txt").read_text(encoding="utf-8")
    analysis = analyze_poem(poem)
    diagnosis = diagnose_poem(poem, analysis, annotations=None)
    assert diagnosis.problem_type == "repetition"
    assert diagnosis.measured_values
    assert float(diagnosis.measured_values.get("max_token_freq") or 0) >= 2
