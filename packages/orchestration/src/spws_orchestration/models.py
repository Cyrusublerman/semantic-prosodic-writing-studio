"""Pipeline definition models and YAML loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class PipelineStep(BaseModel):
    step_id: str
    component_id: str
    inputs: dict[str, str] = Field(default_factory=dict)
    outputs: dict[str, str] = Field(default_factory=dict)
    optional: bool = False
    parallel_group: str | None = None
    timeout_seconds: float | None = None
    # Optional human gate name that must be decided before this step runs.
    human_gate: str | None = None
    # Pause after this step completes until the named gate appears in decisions.
    pause_after_gate: str | None = None


class PipelineDefinition(BaseModel):
    id: str
    version: str
    purpose: str
    accepted_inputs: list[str] = Field(default_factory=list)
    produced_outputs: list[str] = Field(default_factory=list)
    required_contract_versions: dict[str, str] = Field(default_factory=dict)
    steps: list[PipelineStep] = Field(default_factory=list)
    human_gates: list[str] = Field(default_factory=list)
    failure_policy: str = "fail_fast"
    caching_policy: str = "none"
    reproducibility_policy: str = "seeded_where_supported"


class StepResult(BaseModel):
    step_id: str
    status: Literal["completed", "failed", "skipped", "paused", "partial", "timeout"]
    error: str | None = None


class RunResult(BaseModel):
    pipeline_id: str
    status: Literal["completed", "failed", "partial", "paused"]
    context: dict[str, Any] = Field(default_factory=dict)
    step_results: list[StepResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checkpoint: dict[str, Any] | None = None


def load_pipeline_yaml(path: str | Path) -> PipelineDefinition:
    """Load a PipelineDefinition from a YAML file."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"pipeline YAML must be a mapping: {path}")
    return PipelineDefinition.model_validate(data)
