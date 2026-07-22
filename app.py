"""ASGI entry: WordRare generation API + SPWS studio routes."""

from __future__ import annotations

import logging
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SPWS / WordRare API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from apps.studio_api_routes import mount_studio_routes

    mount_studio_routes(app)
except Exception:
    try:
        from spws_studio_api import mount_studio_routes

        mount_studio_routes(app)
    except Exception as exc:
        logger.warning("Studio routes not mounted: %s", exc)

try:
    from wordrare.generation import GenerationSpec, PoemGenerator

    generator = PoemGenerator()
except Exception as exc:
    logger.error("PoemGenerator unavailable: %s", exc)
    generator = None


class GenerateRequest(BaseModel):
    form: str = "haiku"
    theme: str | None = None
    affect_profile: str | None = None
    rarity_bias: float = Field(default=0.5, ge=0.0, le=1.0)
    min_rarity: float = Field(default=0.3, ge=0.0, le=1.0)
    max_rarity: float = Field(default=0.9, ge=0.0, le=1.0)
    domain_tags: list[str] = Field(default_factory=list)
    imagery_tags: list[str] = Field(default_factory=list)
    debug_mode: bool = False


@app.get("/health")
def health():
    return {
        "status": "ok",
        "wordrare": bool(generator),
        "studio": True,
    }


@app.post("/generate")
def generate_poem(request: GenerateRequest):
    if generator is None:
        raise HTTPException(status_code=503, detail="PoemGenerator not initialized")
    spec = GenerationSpec(
        form=request.form,
        theme=request.theme,
        affect_profile=request.affect_profile,
        rarity_bias=request.rarity_bias,
        min_rarity=request.min_rarity,
        max_rarity=request.max_rarity,
        domain_tags=request.domain_tags,
        imagery_tags=request.imagery_tags,
        debug_mode=request.debug_mode,
    )
    poem = generator.generate(spec)
    return {
        "run_id": poem.run_id,
        "text": poem.text,
        "lines": poem.lines,
        "form": poem.spec.form,
        "theme": poem.spec.theme,
        "metrics": poem.metrics,
        "annotations": poem.annotations,
    }


# Prefer apps/studio-api as importable module path for uvicorn
try:
    from apps.studio_api.main import app as studio_app  # type: ignore

    for route in studio_app.routes:
        if getattr(route, "path", None) not in {"/health", "/docs", "/openapi.json", "/redoc"}:
            app.routes.append(route)
except Exception:
    pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
