"""Load bundled pipeline YAML into PipelineDefinition models."""

from __future__ import annotations

from pathlib import Path

from spws_orchestration import PipelineDefinition, load_pipeline_yaml

# .../packages/pipelines/src/spws_pipelines
_MODULE_DIR = Path(__file__).resolve().parent
# parents[0]=src, [1]=packages/pipelines, [2]=packages, [3]=repo root
_PIPELINES_PKG_ROOT = _MODULE_DIR.parents[1]
_MONOREPO_ROOT = _MODULE_DIR.parents[3]


def pipeline_search_dirs() -> list[Path]:
    """Ordered candidate directories containing ``*_v0.yaml`` definitions."""
    dirs: list[Path] = [
        _MODULE_DIR / "definitions",
        _PIPELINES_PKG_ROOT,
        _MONOREPO_ROOT / "pipelines",
    ]
    seen: set[Path] = set()
    ordered: list[Path] = []
    for d in dirs:
        resolved = d.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_dir():
            ordered.append(resolved)
    return ordered


def resolve_pipeline_path(name: str) -> Path:
    """
    Resolve a pipeline name to a YAML path.

    Accepts bare family names (``poetry_revision_v0``), names with or without
    ``.yaml`` / ``.yml``, or an absolute/relative path that already exists.
    """
    candidate = Path(name)
    if candidate.is_file():
        return candidate.resolve()

    stem = name.removesuffix(".yaml").removesuffix(".yml")
    filenames = (f"{stem}.yaml", f"{stem}.yml")

    for directory in pipeline_search_dirs():
        for filename in filenames:
            path = directory / filename
            if path.is_file():
                return path.resolve()

    searched = ", ".join(str(d) for d in pipeline_search_dirs())
    raise FileNotFoundError(
        f"pipeline '{name}' not found; searched: {searched}"
    )


def load_pipeline(name: str) -> PipelineDefinition:
    """Load a PipelineDefinition by family name or filesystem path."""
    return load_pipeline_yaml(resolve_pipeline_path(name))


def list_pipelines() -> list[str]:
    """Return sorted unique pipeline stems discovered on the search path."""
    stems: set[str] = set()
    for directory in pipeline_search_dirs():
        for path in directory.glob("*_v0.yaml"):
            stems.add(path.stem)
        for path in directory.glob("*_v0.yml"):
            stems.add(path.stem)
    return sorted(stems)
