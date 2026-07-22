"""Typed DAG executor with human gates, resume, parallel groups, timeouts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from concurrent.futures import as_completed
from pathlib import Path
from typing import Any

from .models import (
    PipelineDefinition,
    PipelineStep,
    RunResult,
    StepResult,
    load_pipeline_yaml,
)
from .registry import ComponentRegistry


class PipelineExecutionError(RuntimeError):
    """Raised when failure_policy is fail_fast and a required step fails."""

    def __init__(self, message: str, result: RunResult) -> None:
        super().__init__(message)
        self.result = result


class PipelineExecutor:
    """Execute pipeline steps against a ComponentRegistry."""

    def __init__(self, registry: ComponentRegistry | None = None) -> None:
        self.registry = registry if registry is not None else ComponentRegistry()

    def load(self, path: str | Path) -> PipelineDefinition:
        return load_pipeline_yaml(path)

    def execute(
        self,
        pipeline: PipelineDefinition,
        context: dict[str, Any] | None = None,
    ) -> RunResult:
        return self._run(pipeline, context=dict(context or {}), resume_from=None)

    def resume(
        self,
        pipeline: PipelineDefinition,
        context: dict[str, Any] | None = None,
    ) -> RunResult:
        """Continue from the next incomplete step using checkpoint/context."""
        ctx = dict(context or {})
        checkpoint = ctx.get("checkpoint") if isinstance(ctx.get("checkpoint"), dict) else {}
        completed_ids = set(checkpoint.get("completed_step_ids") or [])
        prior = ctx.get("step_results")
        if isinstance(prior, list):
            for item in prior:
                if isinstance(item, dict) and item.get("status") == "completed":
                    completed_ids.add(item["step_id"])
                elif isinstance(item, StepResult) and item.status == "completed":
                    completed_ids.add(item.step_id)
        return self._run(pipeline, context=ctx, resume_from=completed_ids)

    def _run(
        self,
        pipeline: PipelineDefinition,
        *,
        context: dict[str, Any],
        resume_from: set[str] | None,
    ) -> RunResult:
        ctx: dict[str, Any] = dict(context)
        step_results: list[StepResult] = []
        warnings: list[str] = []
        failed = False
        completed_ids: set[str] = set(resume_from or [])

        if resume_from:
            prior = ctx.get("_step_results_objects")
            if isinstance(prior, list):
                for item in prior:
                    if isinstance(item, StepResult) and item.step_id in resume_from:
                        step_results.append(item)

        groups = self._group_steps(pipeline.steps)

        for group in groups:
            if resume_from is not None and all(s.step_id in completed_ids for s in group):
                continue

            gate_name = self._pending_gate(pipeline, group[0], ctx)
            if gate_name is not None:
                return self._paused_result(
                    pipeline,
                    ctx,
                    step_results,
                    warnings,
                    completed_ids,
                    gate_name=gate_name,
                    next_step_id=group[0].step_id,
                )

            if len(group) == 1 or group[0].parallel_group is None:
                result = self._execute_step(pipeline, group[0], ctx, warnings)
                step_results.append(result)
                if result.status == "completed":
                    completed_ids.add(group[0].step_id)
                    pause_gate = self._pause_after_gate(pipeline, group[0], ctx)
                    if pause_gate is not None:
                        return self._paused_result(
                            pipeline,
                            ctx,
                            step_results,
                            warnings,
                            completed_ids,
                            gate_name=pause_gate,
                            next_step_id=None,
                        )
                elif result.status in {"failed", "timeout"}:
                    run = RunResult(
                        pipeline_id=pipeline.id,
                        status="failed" if result.status == "failed" else "partial",
                        context=ctx,
                        step_results=step_results,
                        warnings=warnings,
                    )
                    if pipeline.failure_policy == "fail_fast" and result.status == "failed":
                        raise PipelineExecutionError(result.error or "step failed", run)
                    failed = True
                continue

            parallel_results = self._execute_parallel_group(pipeline, group, ctx, warnings)
            step_results.extend(parallel_results)
            for step, result in zip(group, parallel_results):
                if result.status == "completed":
                    completed_ids.add(result.step_id)
                    pause_gate = self._pause_after_gate(pipeline, step, ctx)
                    if pause_gate is not None:
                        return self._paused_result(
                            pipeline,
                            ctx,
                            step_results,
                            warnings,
                            completed_ids,
                            gate_name=pause_gate,
                            next_step_id=None,
                        )
                elif result.status in {"failed", "timeout"}:
                    run = RunResult(
                        pipeline_id=pipeline.id,
                        status="failed" if result.status == "failed" else "partial",
                        context=ctx,
                        step_results=step_results,
                        warnings=warnings,
                    )
                    if pipeline.failure_policy == "fail_fast" and result.status == "failed":
                        raise PipelineExecutionError(result.error or "step failed", run)
                    failed = True

        if failed:
            completed_any = any(s.status == "completed" for s in step_results)
            status: str = "partial" if completed_any else "failed"
            ctx["checkpoint"] = {"completed_step_ids": sorted(completed_ids)}
            return RunResult(
                pipeline_id=pipeline.id,
                status=status,  # type: ignore[arg-type]
                context=ctx,
                step_results=step_results,
                warnings=warnings,
                checkpoint=ctx["checkpoint"],
            )

        ctx["checkpoint"] = {"completed_step_ids": sorted(completed_ids)}
        return RunResult(
            pipeline_id=pipeline.id,
            status="completed",
            context=ctx,
            step_results=step_results,
            warnings=warnings,
            checkpoint=ctx["checkpoint"],
        )

    def _paused_result(
        self,
        pipeline: PipelineDefinition,
        ctx: dict[str, Any],
        step_results: list[StepResult],
        warnings: list[str],
        completed_ids: set[str],
        *,
        gate_name: str,
        next_step_id: str | None,
    ) -> RunResult:
        checkpoint = {
            "paused_at_gate": gate_name,
            "next_step_id": next_step_id,
            "completed_step_ids": sorted(completed_ids),
        }
        ctx["checkpoint"] = checkpoint
        ctx["_step_results_objects"] = list(step_results)
        paused_results = list(step_results)
        if next_step_id:
            paused_results.append(
                StepResult(
                    step_id=next_step_id,
                    status="paused",
                    error=f"awaiting human gate: {gate_name}",
                )
            )
        return RunResult(
            pipeline_id=pipeline.id,
            status="paused",
            context=ctx,
            step_results=paused_results,
            warnings=warnings,
            checkpoint=checkpoint,
        )

    def _pending_gate(
        self,
        pipeline: PipelineDefinition,
        step: PipelineStep,
        context: dict[str, Any],
    ) -> str | None:
        """Return gate name if this step is blocked on an undecided human gate."""
        decisions = context.get("decisions") or {}
        if not isinstance(decisions, dict):
            decisions = {}

        gate = step.human_gate
        if gate and gate in pipeline.human_gates and gate not in decisions:
            return gate

        # Explicit marker: step_id/component_id equals a declared gate
        for gate_name in pipeline.human_gates:
            if gate_name in decisions:
                continue
            if step.step_id == gate_name or step.component_id == gate_name:
                return gate_name
        return None

    def _pause_after_gate(
        self,
        pipeline: PipelineDefinition,
        step: PipelineStep,
        context: dict[str, Any],
    ) -> str | None:
        gate = step.pause_after_gate
        if not gate or gate not in pipeline.human_gates:
            return None
        decisions = context.get("decisions") or {}
        if isinstance(decisions, dict) and gate in decisions:
            return None
        return gate

    def _execute_step(
        self,
        pipeline: PipelineDefinition,
        step: PipelineStep,
        ctx: dict[str, Any],
        warnings: list[str],
    ) -> StepResult:
        _ = pipeline
        try:
            _, handler = self.registry.get(step.component_id)
        except KeyError as exc:
            error = str(exc)
            if step.optional:
                warnings.append(f"optional step skipped ({step.step_id}): {error}")
                return StepResult(step_id=step.step_id, status="skipped", error=error)
            return StepResult(step_id=step.step_id, status="failed", error=error)

        timeout = step.timeout_seconds
        try:
            if timeout is not None and timeout > 0:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(handler, ctx, step)
                    try:
                        outputs = future.result(timeout=float(timeout))
                    except FuturesTimeoutError:
                        error = f"step exceeded timeout_seconds={timeout}"
                        if step.optional:
                            warnings.append(f"optional step timeout ({step.step_id}): {error}")
                            return StepResult(step_id=step.step_id, status="skipped", error=error)
                        return StepResult(step_id=step.step_id, status="timeout", error=error)
            else:
                outputs = handler(ctx, step)
            if outputs is None:
                outputs = {}
            if not isinstance(outputs, dict):
                raise TypeError(
                    f"handler for {step.component_id} must return a dict, "
                    f"got {type(outputs).__name__}"
                )
            self._merge_outputs(ctx, step, outputs)
            return StepResult(step_id=step.step_id, status="completed")
        except PipelineExecutionError:
            raise
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
            if step.optional:
                warnings.append(f"optional step skipped ({step.step_id}): {error}")
                return StepResult(step_id=step.step_id, status="skipped", error=error)
            return StepResult(step_id=step.step_id, status="failed", error=error)

    def _execute_parallel_group(
        self,
        pipeline: PipelineDefinition,
        group: list[PipelineStep],
        ctx: dict[str, Any],
        warnings: list[str],
    ) -> list[StepResult]:
        """Run same-group steps concurrently; merge outputs into shared context."""
        _ = pipeline
        results: dict[str, StepResult] = {}
        output_map: dict[str, tuple[PipelineStep, dict[str, Any]]] = {}

        def _run_one(step: PipelineStep) -> tuple[PipelineStep, StepResult, dict[str, Any]]:
            local_ctx = dict(ctx)
            try:
                _, handler = self.registry.get(step.component_id)
            except KeyError as exc:
                error = str(exc)
                status = "skipped" if step.optional else "failed"
                if step.optional:
                    warnings.append(f"optional step skipped ({step.step_id}): {error}")
                return step, StepResult(step_id=step.step_id, status=status, error=error), {}

            timeout = step.timeout_seconds
            try:
                if timeout is not None and timeout > 0:
                    with ThreadPoolExecutor(max_workers=1) as pool:
                        future = pool.submit(handler, local_ctx, step)
                        try:
                            outputs = future.result(timeout=float(timeout))
                        except FuturesTimeoutError:
                            return (
                                step,
                                StepResult(
                                    step_id=step.step_id,
                                    status="timeout",
                                    error=f"step exceeded timeout_seconds={timeout}",
                                ),
                                {},
                            )
                else:
                    outputs = handler(local_ctx, step)
                if outputs is None:
                    outputs = {}
                if not isinstance(outputs, dict):
                    raise TypeError(
                        f"handler for {step.component_id} must return a dict, "
                        f"got {type(outputs).__name__}"
                    )
                return step, StepResult(step_id=step.step_id, status="completed"), outputs
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}"
                if step.optional:
                    warnings.append(f"optional step skipped ({step.step_id}): {error}")
                    return step, StepResult(step_id=step.step_id, status="skipped", error=error), {}
                return step, StepResult(step_id=step.step_id, status="failed", error=error), {}

        with ThreadPoolExecutor(max_workers=max(1, len(group))) as pool:
            futures = {pool.submit(_run_one, step): step for step in group}
            for future in as_completed(futures):
                step, result, outputs = future.result()
                results[step.step_id] = result
                if result.status == "completed":
                    output_map[step.step_id] = (step, outputs)

        ordered: list[StepResult] = []
        for step in group:
            result = results[step.step_id]
            ordered.append(result)
            if step.step_id in output_map:
                self._merge_outputs(ctx, step, output_map[step.step_id][1])
        return ordered

    @staticmethod
    def _group_steps(steps: list[PipelineStep]) -> list[list[PipelineStep]]:
        groups: list[list[PipelineStep]] = []
        current: list[PipelineStep] = []
        current_key: str | None = None
        for step in steps:
            key = step.parallel_group
            if key and current and current_key == key:
                current.append(step)
                continue
            if current:
                groups.append(current)
            current = [step]
            current_key = key
        if current:
            groups.append(current)
        return groups

    @staticmethod
    def _merge_outputs(
        context: dict[str, Any],
        step: PipelineStep,
        outputs: dict[str, Any],
    ) -> None:
        if step.outputs:
            for result_key, context_key in step.outputs.items():
                if result_key in outputs:
                    context[context_key] = outputs[result_key]
        else:
            context.update(outputs)


def resolve_step_inputs(context: dict[str, Any], step: PipelineStep) -> dict[str, Any]:
    """Map step.inputs (param -> context key) into a parameter dict."""
    resolved: dict[str, Any] = {}
    for param, context_key in step.inputs.items():
        if context_key in context:
            resolved[param] = context[context_key]
    return resolved
