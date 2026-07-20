from __future__ import annotations

import json
from pathlib import Path

from spws_cli.main import main, run_poetry_revision_demo
from spws_pkl_adapter import validate_bundle
from spws_storage import load_config, WorkspaceStore


def test_vertical_demo_function(spws_config, temp_workspace, monkeypatch):
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    from spws_cli import config as cli_config

    monkeypatch.setattr(cli_config, "load_spws_config", lambda config_path=None: spws_config)
    result = run_poetry_revision_demo(accept_first=True)
    assert result["candidate_count"] >= 0
    assert Path(result["promotion_path"]).exists()
    bundle = validate_bundle(Path(result["promotion_path"]))
    assert bundle.originating_run_id == result["run_id"]


def test_cli_poetry_revision_command(spws_config, temp_workspace, monkeypatch, capsys):
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    from spws_cli import config as cli_config

    monkeypatch.setattr(cli_config, "load_spws_config", lambda config_path=None: spws_config)
    code = main(["demo", "poetry-revision"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert "run_id" in payload


def test_cli_pkl_query(spws_config, temp_workspace, monkeypatch, capsys, project_root):
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))
    from spws_cli import config as cli_config

    monkeypatch.setattr(cli_config, "load_spws_config", lambda config_path=None: spws_config)
    assert main(["pkl", "index", "--source", str(project_root / "fixtures" / "pkl")]) == 0
    capsys.readouterr()
    assert main(["pkl", "query", "meter"]) == 0
    hits = json.loads(capsys.readouterr().out)
    assert isinstance(hits, list)
    assert hits
