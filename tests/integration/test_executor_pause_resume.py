"""Phase 5: executor human gates, pause/resume, parallel groups."""

from __future__ import annotations

import time

from spws_orchestration import (
    ComponentManifest,
    ComponentRegistry,
    PipelineDefinition,
    PipelineExecutor,
    PipelineStep,
    register_defaults,
)
from spws_pipelines import load_pipeline
from spws_storage import load_config


SAMPLE = (
    "The wind along the meadow path\n"
    "Turns every blade of grass to gold,\n"
    "And in the quiet after rain\n"
    "The earth remembers stories old."
)


def _manifest(component_id: str) -> ComponentManifest:
    return ComponentManifest(
        component_id=component_id,
        component_version="0.1.0",
        functional_category="test",
    )


def test_poetry_pipeline_pause_resume_gates(temp_workspace, monkeypatch) -> None:
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    config = load_config(temp_workspace["config_path"])
    registry = register_defaults()
    pipeline = load_pipeline("poetry_revision_v0")
    assert "plan_confirm" in pipeline.human_gates
    assert "revision_decide" in pipeline.human_gates

    executor = PipelineExecutor(registry)
    first = executor.execute(
        pipeline,
        context={
            "draft_text": SAMPLE,
            "text": SAMPLE,
            "config": config,
            "kind": "poem",
            "brief": "improve diction",
        },
    )
    assert first.status == "paused"
    assert first.checkpoint is not None
    assert first.checkpoint["paused_at_gate"] == "plan_confirm"
    assert "analyse_poetry" in first.checkpoint["completed_step_ids"]
    assert "create_plan" in first.checkpoint["completed_step_ids"]

    ctx = dict(first.context)
    ctx["decisions"] = {"plan_confirm": True}
    second = executor.resume(pipeline, context=ctx)
    assert second.status == "paused"
    assert second.checkpoint is not None
    assert second.checkpoint["paused_at_gate"] == "revision_decide"
    assert "propose_revisions" in second.checkpoint["completed_step_ids"]
    assert second.context.get("revision") or second.context.get("revision_candidates")

    ctx2 = dict(second.context)
    ctx2["decisions"] = {
        "plan_confirm": True,
        "revision_decide": {"kind": "accept"},
    }
    third = executor.resume(pipeline, context=ctx2)
    assert third.status == "completed"


def test_parallel_group_and_timeout() -> None:
    def fast_a(ctx, step):
        return {"a": 1}

    def fast_b(ctx, step):
        return {"b": 2}

    def slow(ctx, step):
        time.sleep(0.5)
        return {"slow": True}

    reg = ComponentRegistry()
    reg.register(_manifest("fast_a"), fast_a)
    reg.register(_manifest("fast_b"), fast_b)
    reg.register(_manifest("slow_step"), slow)

    pipeline = PipelineDefinition(
        id="parallel_demo",
        version="0.1.0",
        purpose="parallel + timeout",
        steps=[
            PipelineStep(
                step_id="a",
                component_id="fast_a",
                parallel_group="g1",
                outputs={"a": "a"},
            ),
            PipelineStep(
                step_id="b",
                component_id="fast_b",
                parallel_group="g1",
                outputs={"b": "b"},
            ),
            PipelineStep(
                step_id="slow",
                component_id="slow_step",
                timeout_seconds=0.05,
                optional=True,
            ),
        ],
        failure_policy="continue",
    )
    executor = PipelineExecutor(reg)
    result = executor.execute(pipeline, context={})
    assert result.context.get("a") == 1
    assert result.context.get("b") == 2
    slow_result = next(s for s in result.step_results if s.step_id == "slow")
    assert slow_result.status in {"timeout", "skipped"}
