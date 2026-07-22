"""Stress: FastAPI studio routes under sequential workflow pressure."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


@pytest.fixture
def api_client(stress_config, seeded_gauge, project_root):
    del seeded_gauge, stress_config  # SPWS_CONFIG set by stress_config fixture
    apps = str(project_root / "apps")
    if apps not in sys.path:
        sys.path.insert(0, apps)
    from studio_api.main import app

    return TestClient(app)


def test_api_full_revision_flow(api_client, project_root):
    poem = (project_root / "fixtures" / "poetry" / "adversarial_repetition_14.txt").read_text(
        encoding="utf-8"
    )
    health = api_client.get("/health")
    assert health.status_code == 200

    analysis = api_client.post("/analyse", json={"text": poem, "kind": "poem"})
    assert analysis.status_code == 200, analysis.text
    body = analysis.json()
    assert body.get("diagnosis")
    assert body["diagnosis"]["problem_type"] == "repetition"

    plan = api_client.post(
        "/plan/create",
        json={
            "brief": "reduce repetition",
            "form": "free_verse",
            "diagnosis": body["diagnosis"],
        },
    )
    assert plan.status_code == 200
    confirmed = api_client.post("/plan/confirm", json={"plan": plan.json(), "confirmed": True})
    assert confirmed.status_code == 200
    assert confirmed.json()["confirmed"] is True

    # Propose without confirm should 400 if we send unconfirmed — confirmed path:
    propose = api_client.post(
        "/revise/propose",
        json={
            "text": poem,
            "brief": "reduce repetition",
            "work_plan": confirmed.json(),
            "diagnosis": body["diagnosis"],
        },
    )
    assert propose.status_code == 200, propose.text
    payload = propose.json()
    candidates = ((payload.get("proposal") or payload).get("candidate_set") or {}).get("candidates") or []
    assert len(candidates) >= 2
    families = {c.get("method_family") for c in candidates}
    assert len(families) >= 2

    decide = api_client.post(
        "/revise/decide",
        json={
            "candidate_id": candidates[0]["candidate_id"],
            "kind": "accept",
            "proposal_path": payload.get("proposal_path"),
            "export": True,
            "rationale": "api stress accept",
        },
    )
    assert decide.status_code == 200, decide.text
    decided = decide.json()
    assert decided["decision"]["kind"] == "accept"
    assert decided.get("export")

    for mode in ("rarefy", "ground_to_library", "meter_fit", "theme_align"):
        assist = api_client.post(
            "/assist/reword",
            json={"text": "The wind along the meadow path", "mode": mode},
        )
        assert assist.status_code == 200, assist.text
        assert assist.json().get("auto_apply") is False


def test_api_propose_rejects_unconfirmed_plan(api_client, project_root):
    poem = (project_root / "fixtures" / "poetry" / "sample_poem.txt").read_text(encoding="utf-8")
    plan = api_client.post("/plan/create", json={"brief": "x", "form": "free_verse"}).json()
    assert plan.get("confirmed") is False
    resp = api_client.post(
        "/revise/propose",
        json={"text": poem, "brief": "x", "work_plan": plan},
    )
    assert resp.status_code == 400
