"""Register default handlers and execute poetry_revision analyse step."""

from __future__ import annotations

import pytest

from spws_orchestration import (
    LLMMethodFamilyDisabled,
    PipelineExecutor,
    assert_method_family_allowed,
    register_defaults,
)
from spws_pipelines import load_pipeline


SAMPLE = (
    "The wind along the meadow path\n"
    "Turns every blade of grass to gold,\n"
    "And in the quiet after rain\n"
    "The earth remembers stories old."
)


def test_register_defaults_and_analyse_step(temp_workspace, monkeypatch):
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    from spws_storage import load_config

    config = load_config(temp_workspace["config_path"])
    registry = register_defaults()
    assert "analyse_document" in registry
    assert "revise_poetry" in registry

    pipeline = load_pipeline("poetry_revision_v0")
    # Run only the analyse step by slicing
    analyse_only = pipeline.model_copy(
        update={"steps": [s for s in pipeline.steps if s.component_id == "analyse_document"]}
    )
    executor = PipelineExecutor(registry)
    result = executor.execute(
        analyse_only,
        context={"draft_text": SAMPLE, "text": SAMPLE, "config": config, "kind": "poem"},
    )
    assert result.status == "completed"
    # step outputs map handler key "analysis" → context "poetry_analysis"
    analysis = result.context.get("poetry_analysis") or result.context.get("analysis") or {}
    assert analysis.get("bundle")
    assert analysis.get("kind") == "poem"


def test_llm_socket_fail_closed(monkeypatch):
    monkeypatch.delenv("SPWS_ALLOW_LLM", raising=False)
    with pytest.raises(LLMMethodFamilyDisabled):
        assert_method_family_allowed("llm_bounded")
    with pytest.raises(LLMMethodFamilyDisabled):
        assert_method_family_allowed("llm_chat")
    assert_method_family_allowed("rare_lexical")
    assert_method_family_allowed(None)
    monkeypatch.setenv("SPWS_ALLOW_LLM", "1")
    assert_method_family_allowed("llm_bounded")
