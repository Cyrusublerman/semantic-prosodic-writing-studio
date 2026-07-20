"""
FastAPI web server for WordRare poem generation.
Deployed on Railway.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="WordRare Poem Generator API",
    description="Generate procedural poetry using rare words with phonetic, semantic, and poetic-structure constraints",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import generation engine
try:
    from wordrare.generation import PoemGenerator, GenerationSpec
    generator = PoemGenerator()
    logger.info("PoemGenerator initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize PoemGenerator: {e}")
    generator = None


# Pydantic models for API
class GenerateRequest(BaseModel):
    """Request model for poem generation."""
    form: str = Field(default="haiku", description="Poetic form (e.g., shakespearean_sonnet, haiku, villanelle)")
    theme: Optional[str] = Field(default=None, description="Poem theme (e.g., nature, death, time)")
    affect_profile: Optional[str] = Field(default=None, description="Emotional profile (e.g., melancholic, joyful)")
    rarity_bias: float = Field(default=0.5, ge=0.0, le=1.0, description="Word rarity preference (0.0=common, 1.0=very rare)")
    min_rarity: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum word rarity threshold")
    max_rarity: float = Field(default=0.9, ge=0.0, le=1.0, description="Maximum word rarity threshold")
    domain_tags: List[str] = Field(default_factory=list, description="Domain tags (e.g., nautical, botanical)")
    imagery_tags: List[str] = Field(default_factory=list, description="Imagery tags (e.g., visual, auditory)")
    debug_mode: bool = Field(default=False, description="Enable debug output")


class GenerateResponse(BaseModel):
    """Response model for poem generation."""
    run_id: str
    text: str
    lines: List[str]
    form: str
    theme: Optional[str]
    rarity_bias: float
    metrics: Dict
    annotations: Dict


class FormInfo(BaseModel):
    """Model for poetic form information."""
    form_id: str
    name: str
    description: str
    total_lines: int
    rhyme_pattern: Optional[List[str]] = None
    meter_pattern: Optional[List[str]] = None


# API Routes

@app.get("/")
async def root():
    """Welcome endpoint with API information."""
    return {
        "name": "WordRare Poem Generator API",
        "version": "0.1.0",
        "status": "operational" if generator else "degraded",
        "endpoints": {
            "generate": "POST /generate - Generate a poem",
            "forms": "GET /forms - List available poetic forms",
            "form_info": "GET /forms/{form_id} - Get information about a specific form",
            "health": "GET /health - Health check"
        },
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint for Railway."""
    if generator is None:
        raise HTTPException(status_code=503, detail="PoemGenerator not initialized")

    return {
        "status": "healthy",
        "generator": "initialized",
        "forms_available": len(generator.list_forms()) if generator else 0
    }


@app.post("/generate", response_model=GenerateResponse)
async def generate_poem(request: GenerateRequest):
    """
    Generate a poem based on the provided specification.

    Example request:
    ```json
    {
        "form": "haiku",
        "theme": "nature",
        "rarity_bias": 0.6
    }
    ```
    """
    if generator is None:
        raise HTTPException(status_code=503, detail="PoemGenerator not initialized")

    try:
        logger.info(f"Generating poem: form={request.form}, theme={request.theme}, rarity={request.rarity_bias}")

        # Create generation spec
        spec = GenerationSpec(
            form=request.form,
            theme=request.theme,
            affect_profile=request.affect_profile,
            rarity_bias=request.rarity_bias,
            min_rarity=request.min_rarity,
            max_rarity=request.max_rarity,
            domain_tags=request.domain_tags,
            imagery_tags=request.imagery_tags,
            debug_mode=request.debug_mode
        )

        # Generate poem
        poem = generator.generate(spec)

        logger.info(f"Successfully generated poem: run_id={poem.run_id}")

        # Return response
        return GenerateResponse(
            run_id=poem.run_id,
            text=poem.text,
            lines=poem.lines,
            form=poem.spec.form,
            theme=poem.spec.theme,
            rarity_bias=poem.spec.rarity_bias,
            metrics=poem.metrics,
            annotations=poem.annotations
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate poem: {str(e)}")


@app.get("/forms", response_model=List[str])
async def list_forms():
    """
    List all available poetic forms.

    Returns a list of form IDs that can be used in generation requests.
    """
    if generator is None:
        raise HTTPException(status_code=503, detail="PoemGenerator not initialized")

    try:
        forms = generator.list_forms()
        logger.info(f"Listed {len(forms)} available forms")
        return forms
    except Exception as e:
        logger.error(f"Error listing forms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/forms/{form_id}", response_model=FormInfo)
async def get_form_info(form_id: str):
    """
    Get detailed information about a specific poetic form.

    Args:
        form_id: The form identifier (e.g., 'shakespearean_sonnet', 'haiku')
    """
    if generator is None:
        raise HTTPException(status_code=503, detail="PoemGenerator not initialized")

    try:
        info = generator.get_form_info(form_id)

        if not info:
            raise HTTPException(status_code=404, detail=f"Form '{form_id}' not found")

        return FormInfo(**info)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting form info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Startup event
@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    logger.info("WordRare API starting up...")
    logger.info(f"Generator status: {'initialized' if generator else 'failed'}")
    if generator:
        try:
            forms = generator.list_forms()
            logger.info(f"Available forms: {len(forms)}")
        except Exception as e:
            logger.warning(f"Could not list forms: {e}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown information."""
    logger.info("WordRare API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
