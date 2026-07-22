"""Smoke-test Studio FastAPI app via importlib (skip if fastapi unavailable)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


def _load_app():
    root = Path(__file__).resolve().parents[2]
    path = root / "apps" / "studio-api" / "main.py"
    name = "spws_studio_api_main_smoke"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so pydantic can resolve postponed annotations.
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    for attr in vars(mod).values():
        if isinstance(attr, type) and hasattr(attr, "model_rebuild"):
            try:
                attr.model_rebuild()
            except Exception:
                pass
    return mod.app


@pytest.fixture
def client(temp_workspace, monkeypatch):
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    return TestClient(_load_app())


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_analyse_and_plan_and_assist(client):
    poem = (
        "The wind along the meadow path\n"
        "Turns every blade of grass to gold,\n"
        "And in the quiet after rain\n"
        "The earth remembers stories old."
    )
    analyse = client.post("/analyse", json={"text": poem, "kind": "poem"})
    assert analyse.status_code == 200
    body = analyse.json()
    assert "bundle" in body

    plan = client.post(
        "/plan/create",
        json={"brief": "improve diction", "form": "free_verse", "diagnosis": body.get("diagnosis")},
    )
    assert plan.status_code == 200
    confirmed = client.post("/plan/confirm", json={"plan": plan.json(), "confirmed": True})
    assert confirmed.status_code == 200
    assert confirmed.json()["confirmed"] is True

    assist = client.post("/assist/reword", json={"text": poem.splitlines()[0], "mode": "rarefy"})
    assert assist.status_code == 200
    assert assist.json()["auto_apply"] is False
    assert "candidates" in assist.json()
