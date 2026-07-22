"""Shared helpers for SPWS stress battery."""

from __future__ import annotations

from pathlib import Path

import pytest

from spws_contracts_core.domain import MeaningScale, PrivacyState, RightsState
from spws_semantics import MeaningGauge
from spws_storage import load_config


@pytest.fixture
def stress_config(temp_workspace, monkeypatch):
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    return load_config(temp_workspace["config_path"])


@pytest.fixture
def seeded_gauge(stress_config, project_root) -> MeaningGauge:
    gauge = MeaningGauge(
        Path(stress_config.meaning_index_path),
        debug_hash_embeddings=True,
        require_model=False,
    )
    seeds = [
        "quiet river keeps a luminous measure under leaf-shadow",
        "zephyr edits the aureate meadow at dusk",
        "hushed earth remembers chronicles of seed and stone",
        "silver rain returns across the willow bend",
        "pastoral cadence of hill and rivulet song",
        "Wind edits the forest canopy at dusk.",
        "Meter and stress shape poetic rhythm.",
        "The earth remembers stories old and deep.",
    ]
    for index, text in enumerate(seeds):
        gauge.index_text(
            text,
            source_object_id=f"stress-seed-{index}",
            object_uid=f"stress-seed-{index}",
            rights=RightsState.PUBLIC,
            privacy=PrivacyState.PUBLIC,
            scales=[MeaningScale.PHRASE, MeaningScale.SENTENCE],
        )
    frag_root = project_root / "fixtures" / "fragments"
    if frag_root.is_dir():
        for path in sorted(frag_root.rglob("*.md")):
            body = path.read_text(encoding="utf-8")
            if body.startswith("---"):
                parts = body.split("---", 2)
                body = parts[2] if len(parts) >= 3 else body
            body = body.strip()
            if not body:
                continue
            gauge.index_text(
                body,
                source_object_id=str(path),
                object_uid=f"frag-{path.stem}",
                rights=RightsState.PUBLIC,
                privacy=PrivacyState.PUBLIC,
                scales=[MeaningScale.PHRASE, MeaningScale.SENTENCE],
            )
    return gauge


def poem_path(project_root: Path, name: str) -> Path:
    path = project_root / "fixtures" / "poetry" / name
    assert path.is_file(), path
    return path
