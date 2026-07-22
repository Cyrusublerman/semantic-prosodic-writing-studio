"""SPWS Studio FastAPI boundary."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="SPWS Studio API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-process session state for propose → decide (tests / single-user studio).
_SESSION: dict[str, Any] = {
    "text": "",
    "analysis": None,
    "plan": None,
    "proposal": None,
    "last_export": None,
}


class TextBody(BaseModel):
    text: str
    mode: str = "rarefy"
    kind: str = "poem"


class PlanCreateBody(BaseModel):
    brief: str = "improve diction"
    form: str = "free_verse"
    text: str | None = None
    diagnosis: Any = None


class PlanConfirmBody(BaseModel):
    plan: Any = None
    confirmed: bool = True


class ReviseProposeBody(BaseModel):
    text: str
    brief: str = "improve diction"
    work_plan: Any = None
    diagnosis: Any = None


class ReviseDecideBody(BaseModel):
    candidate_id: str
    kind: str = "accept"
    proposal_path: str | None = None
    rationale: str | None = None
    export: bool = True


class CollageBody(BaseModel):
    theme: str
    lines: int = Field(default=3, ge=1, le=40)


class SimilarBody(BaseModel):
    text: str
    limit: int = Field(default=5, ge=1, le=50)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "spws-studio-api"}


@app.post("/analyse")
def analyse(body: TextBody) -> dict[str, Any]:
    from spws_analysis import analyse_document
    from spws_storage import load_config

    try:
        config = load_config()
    except Exception:
        config = None
    result = analyse_document(body.text, kind=body.kind, config=config)
    _SESSION["text"] = body.text
    _SESSION["analysis"] = result
    return result


@app.post("/plan/create")
def plan_create(body: PlanCreateBody) -> dict[str, Any]:
    from spws_planning import create_work_plan

    diagnosis = body.diagnosis
    if diagnosis is None and _SESSION.get("analysis"):
        diagnosis = (_SESSION["analysis"] or {}).get("diagnosis")
    plan = create_work_plan(brief=body.brief, form=body.form, diagnosis=diagnosis)
    _SESSION["plan"] = plan
    return plan


@app.post("/plan/confirm")
def plan_confirm(body: PlanConfirmBody) -> dict[str, Any]:
    from spws_planning import confirm_work_plan

    plan = body.plan if body.plan is not None else _SESSION.get("plan")
    if plan is None:
        raise HTTPException(status_code=400, detail="no plan to confirm; call /plan/create first")
    confirmed = confirm_work_plan(plan, confirmed=body.confirmed)
    _SESSION["plan"] = confirmed
    return confirmed


@app.post("/revise/propose")
def revise_propose(body: ReviseProposeBody) -> dict[str, Any]:
    from spws_revision import propose_revision
    from spws_storage import load_config

    config = load_config()
    plan = body.work_plan if body.work_plan is not None else _SESSION.get("plan")
    if plan is not None and not plan.get("confirmed"):
        raise HTTPException(status_code=400, detail="work plan not confirmed")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as handle:
        handle.write(body.text)
        path = Path(handle.name)
    try:
        proposal = propose_revision(
            path,
            brief=body.brief,
            config=config,
            diagnosis=body.diagnosis
            or ((_SESSION.get("analysis") or {}).get("diagnosis") if _SESSION.get("analysis") else None),
            work_plan=plan,
        )
    finally:
        path.unlink(missing_ok=True)
    _SESSION["text"] = body.text
    _SESSION["proposal"] = proposal
    return proposal


@app.post("/revise/decide")
def revise_decide(body: ReviseDecideBody) -> dict[str, Any]:
    from spws_revision import decide_revision
    from spws_storage import load_config

    config = load_config()
    proposal_path = body.proposal_path
    if not proposal_path:
        stored = _SESSION.get("proposal") or {}
        proposal_path = stored.get("proposal_path")
    if not proposal_path:
        raise HTTPException(status_code=400, detail="proposal_path required")
    export_dir = None
    if body.export:
        export_dir = Path(config.workspace_path) / "exports" / "last"
    result = decide_revision(
        config,
        proposal_path,
        body.candidate_id,
        body.kind,
        rationale=body.rationale,
        export_dir=export_dir,
    )
    if result.get("export"):
        _SESSION["last_export"] = result["export"]
    return result


@app.post("/revise/poetry")
def revise(body: ReviseProposeBody) -> dict[str, Any]:
    """Legacy convenience path — same as propose without session persist requirement."""
    import tempfile as _tf

    from spws_revision import revise_poetry
    from spws_storage import load_config

    config = load_config()
    with _tf.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as handle:
        handle.write(body.text)
        path = Path(handle.name)
    try:
        return revise_poetry(path, brief=body.brief, config=config, diagnosis=body.diagnosis, work_plan=body.work_plan)
    finally:
        path.unlink(missing_ok=True)


@app.post("/assist/reword")
def assist(body: TextBody) -> dict[str, Any]:
    from spws_revision import assist_reword
    from spws_storage import load_config

    try:
        return assist_reword(body.text, mode=body.mode, config=load_config())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/meaning/similar")
def meaning_similar(body: SimilarBody) -> dict[str, Any]:
    try:
        from spws_contracts_core.domain import MeaningScale, SimilarityQuery
        from spws_semantics import MeaningGauge
        from spws_storage import load_config

        config = load_config()
        try:
            gauge = MeaningGauge.from_config(config)
        except RuntimeError:
            gauge = MeaningGauge(
                Path(config.meaning_index_path),
                debug_hash_embeddings=True,
                require_model=False,
            )
        if gauge.count() == 0:
            raise HTTPException(
                status_code=400,
                detail="meaning index empty — run `spws meaning index-library` on rights-cleared fragments",
            )
        result = gauge.similar(
            SimilarityQuery(
                text=body.text,
                result_limit=body.limit,
                target_scales=[MeaningScale.SENTENCE, MeaningScale.PHRASE, MeaningScale.PARAGRAPH],
            )
        )
        return result.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/generate/collage")
def collage(body: CollageBody) -> dict[str, Any]:
    from spws_generation import generate_collage
    from spws_storage import load_config

    return generate_collage(theme=body.theme, line_count=body.lines, config=load_config())


@app.get("/session/export")
def session_export() -> dict[str, Any]:
    return {"last_export": _SESSION.get("last_export"), "has_proposal": _SESSION.get("proposal") is not None}


def create_app() -> FastAPI:
    return app
