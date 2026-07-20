from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def run_tool(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOLS / name), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_assurance_gate_structure_is_valid() -> None:
    result = run_tool("check_assurance_gate.py")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["gate_count"] >= 10


def test_phase6_gate_is_deliberately_blocked() -> None:
    result = run_tool("check_assurance_gate.py", "--require", "phase6")
    assert result.returncode != 0
    assert "phase6 assurance gate is blocked" in result.stderr
    assert "A-REP-001" in result.stderr


def test_stable_gate_is_deliberately_blocked() -> None:
    result = run_tool("check_assurance_gate.py", "--require", "stable")
    assert result.returncode != 0
    assert "stable assurance gate is blocked" in result.stderr
    assert "A-SUPPLY-001" in result.stderr


def test_immutable_release_hashes_match_baseline() -> None:
    result = run_tool("verify_immutable_release.py")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["release"] == "0.1.0-dev.2"
    assert payload["archive_sha256"] == (
        "d0281b6dd8e49c0100225540e40389256a92d7571a1f279a9994fd2a6ce6f8d7"
    )
