"""Registered pipeline handlers wrapping existing SPWS packages."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .executor import resolve_step_inputs
from .llm_socket import assert_method_family_allowed
from .models import PipelineStep
from .registry import ComponentManifest, ComponentRegistry


def _text_from_context(ctx: dict[str, Any], resolved: dict[str, Any]) -> str:
    for key in ("text", "draft", "draft_text", "source_text"):
        value = resolved.get(key) or ctx.get(key)
        if isinstance(value, str) and value.strip():
            return value
    source = resolved.get("source") or ctx.get("raw_source") or ctx.get("source")
    if isinstance(source, dict):
        text = source.get("text") or source.get("content")
        if isinstance(text, str):
            return text
    if isinstance(source, (str, Path)) and Path(source).is_file():
        return Path(source).read_text(encoding="utf-8")
    path = ctx.get("target") or ctx.get("path")
    if isinstance(path, (str, Path)) and Path(path).is_file():
        return Path(path).read_text(encoding="utf-8")
    raise ValueError("context missing text/source for handler")


def handle_analyse_document(ctx: dict[str, Any], step: PipelineStep) -> dict[str, Any]:
    from spws_analysis import analyse_document

    resolved = resolve_step_inputs(ctx, step)
    text = _text_from_context(ctx, resolved)
    kind = resolved.get("kind") or ctx.get("kind") or "poem"
    config = resolved.get("config") or ctx.get("config")
    result = analyse_document(text, kind=str(kind), config=config)
    return {
        "analysis": result,
        "poetry_analysis": result.get("poetry"),
        "diagnosis": result.get("diagnosis"),
        "bundle": result.get("bundle"),
    }


def handle_build_source_board(ctx: dict[str, Any], step: PipelineStep) -> dict[str, Any]:
    from spws_planning import build_source_board

    resolved = resolve_step_inputs(ctx, step)
    query = resolved.get("query") or resolved.get("text") or ctx.get("query") or ctx.get("theme") or ""
    if isinstance(query, dict):
        query = query.get("text") or ""
    config = resolved.get("config") or ctx.get("config")
    if config is None:
        from spws_storage import load_config

        config = load_config()
    board = build_source_board(str(query), config, allow_empty_fail=bool(ctx.get("allow_empty_fail", True)))
    return {"board": board, "source_board": board}


def handle_create_work_plan(ctx: dict[str, Any], step: PipelineStep) -> dict[str, Any]:
    from spws_planning import confirm_work_plan, create_work_plan

    resolved = resolve_step_inputs(ctx, step)
    brief = resolved.get("brief") or ctx.get("brief") or "improve diction"
    form = resolved.get("form") or ctx.get("form") or "free_verse"
    diagnosis = resolved.get("diagnosis") or ctx.get("diagnosis")
    plan = create_work_plan(str(brief), form=str(form), diagnosis=diagnosis)
    decisions = ctx.get("decisions") or {}
    if isinstance(decisions, dict) and "plan_confirm" in decisions:
        confirmed = decisions["plan_confirm"]
        flag = True if confirmed is True or confirmed == {"confirmed": True} else bool(confirmed)
        plan = confirm_work_plan(plan, confirmed=flag)
    return {"work_plan": plan, "plan": plan}


def handle_revise_poetry(ctx: dict[str, Any], step: PipelineStep) -> dict[str, Any]:
    from spws_revision import revise_poetry

    resolved = resolve_step_inputs(ctx, step)
    gen_spec = resolved.get("generation_spec") or ctx.get("generation_spec")
    method_family = None
    if isinstance(gen_spec, dict):
        method_family = gen_spec.get("method_family")
    elif gen_spec is not None and hasattr(gen_spec, "method_family"):
        method_family = gen_spec.method_family
    assert_method_family_allowed(method_family)

    config = resolved.get("config") or ctx.get("config")
    brief = resolved.get("brief") or ctx.get("brief") or "improve diction"
    diagnosis = resolved.get("diagnosis") or ctx.get("diagnosis")
    work_plan = resolved.get("work_plan") or ctx.get("work_plan") or ctx.get("plan")
    decisions = ctx.get("decisions") or {}
    if isinstance(work_plan, dict) and isinstance(decisions, dict) and "plan_confirm" in decisions:
        if not work_plan.get("confirmed"):
            from spws_planning import confirm_work_plan

            flag = decisions["plan_confirm"]
            confirmed = True if flag is True or flag == {"confirmed": True} else bool(flag)
            work_plan = confirm_work_plan(work_plan, confirmed=confirmed)
            ctx["work_plan"] = work_plan
    target = resolved.get("target") or resolved.get("source") or ctx.get("target")
    if target is None:
        text = _text_from_context(ctx, resolved)
        import tempfile

        handle = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
        handle.write(text)
        handle.close()
        target = handle.name
        try:
            result = revise_poetry(
                Path(target),
                brief=str(brief),
                config=config,
                diagnosis=diagnosis,
                work_plan=work_plan,
                generation_spec=gen_spec,
            )
        finally:
            Path(target).unlink(missing_ok=True)
    else:
        result = revise_poetry(
            Path(target),
            brief=str(brief),
            config=config,
            diagnosis=diagnosis,
            work_plan=work_plan,
            generation_spec=gen_spec,
        )
    return {
        "revision": result,
        "candidates": result.get("candidate_set"),
        "revision_candidates": result.get("candidate_set"),
    }


def handle_generate_collage(ctx: dict[str, Any], step: PipelineStep) -> dict[str, Any]:
    from spws_generation import generate_collage

    resolved = resolve_step_inputs(ctx, step)
    gen_spec = resolved.get("generation_spec") or ctx.get("generation_spec")
    method_family = None
    if isinstance(gen_spec, dict):
        method_family = gen_spec.get("method_family")
    elif gen_spec is not None and hasattr(gen_spec, "method_family"):
        method_family = gen_spec.method_family
    if method_family is None:
        method_family = resolved.get("method_family") or ctx.get("method_family")
    assert_method_family_allowed(method_family)

    theme = resolved.get("theme") or resolved.get("query") or ctx.get("theme") or "nature"
    line_count = int(resolved.get("line_count") or ctx.get("line_count") or 3)
    config = resolved.get("config") or ctx.get("config")
    work_plan = resolved.get("work_plan") or ctx.get("work_plan")
    collage = generate_collage(
        theme=str(theme),
        line_count=line_count,
        config=config,
        work_plan=work_plan,
        generation_spec=gen_spec,
    )
    return {"collage": collage, "poem_draft": collage}


_HANDLERS: list[tuple[ComponentManifest, Any]] = [
    (
        ComponentManifest(
            component_id="analyse_document",
            component_version="0.1.0",
            functional_category="analysis",
            capabilities=["analyse_document", "poetry_suite"],
            accepted_contracts=["InputPackage", "RawSource"],
            produced_contracts=["AnalysisBundle", "RevisionDiagnosis"],
        ),
        handle_analyse_document,
    ),
    (
        ComponentManifest(
            component_id="build_source_board",
            component_version="0.1.0",
            functional_category="planning",
            capabilities=["build_source_board"],
            accepted_contracts=["SimilarityQuery"],
            produced_contracts=["SourceBoard"],
        ),
        handle_build_source_board,
    ),
    (
        ComponentManifest(
            component_id="create_work_plan",
            component_version="0.1.0",
            functional_category="planning",
            capabilities=["create_work_plan"],
            accepted_contracts=["RevisionDiagnosis"],
            produced_contracts=["WorkPlan", "WorkSpecification"],
        ),
        handle_create_work_plan,
    ),
    (
        ComponentManifest(
            component_id="revise_poetry",
            component_version="0.1.0",
            functional_category="revision",
            capabilities=["revise_poetry", "generate_candidates"],
            accepted_contracts=["WorkPlan", "RevisionDiagnosis"],
            produced_contracts=["CandidateSet", "EvaluationBundle"],
        ),
        handle_revise_poetry,
    ),
    (
        ComponentManifest(
            component_id="generate_collage",
            component_version="0.1.0",
            functional_category="generation",
            capabilities=["generate_collage"],
            accepted_contracts=["GenerationSpecification", "WorkPlan"],
            produced_contracts=["Candidate"],
        ),
        handle_generate_collage,
    ),
]


def register_defaults(registry: ComponentRegistry | None = None) -> ComponentRegistry:
    """Register default SPWS handlers on ``registry`` (or a new registry)."""
    reg = registry if registry is not None else ComponentRegistry()
    for manifest, handler in _HANDLERS:
        reg.register(manifest, handler)
    return reg
