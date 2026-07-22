"""Playwright e2e: import → diagnose → confirm plan → accept candidate → export.

Requires Playwright Chromium (CI installs via `python -m playwright install chromium`).
Serves the Vite production build from apps/studio-web/dist.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import uvicorn
from playwright.sync_api import sync_playwright


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _ensure_studio_web_build(web_root: Path) -> Path:
    dist = web_root / "dist"
    index = dist / "index.html"
    if index.is_file():
        return dist
    npm = shutil.which("pnpm") or shutil.which("npm")
    if not npm:
        pytest.skip("pnpm/npm unavailable to build studio-web")
    cmd = [npm, "run", "build"]
    if Path(npm).name == "npm":
        cmd = [npm, "run", "build"]
    env = os.environ.copy()
    # Install deps if needed
    if not (web_root / "node_modules").is_dir():
        install = [npm, "install"]
        subprocess.run(install, cwd=web_root, check=True, env=env)
    subprocess.run(cmd, cwd=web_root, check=True, env=env)
    if not index.is_file():
        pytest.fail("studio-web build did not produce dist/index.html")
    return dist


@pytest.fixture
def studio_stack(temp_workspace, monkeypatch, project_root):
    monkeypatch.setenv("SPWS_CONFIG", str(temp_workspace["config_path"]))

    from spws_contracts_core.domain import MeaningScale, PrivacyState, RightsState
    from spws_semantics import MeaningGauge
    from spws_storage import load_config

    config = load_config(temp_workspace["config_path"])
    gauge = MeaningGauge(Path(config.meaning_index_path), debug_hash_embeddings=True, require_model=False)
    for index, text in enumerate(
        [
            "quiet river luminous dream of leaves",
            "zephyr over aureate meadow grass",
            "hushed earth remembers ancient chronicles",
        ]
    ):
        gauge.index_text(
            text,
            source_object_id=f"pw-{index}",
            object_uid=f"pw-{index}",
            rights=RightsState.PUBLIC,
            privacy=PrivacyState.PUBLIC,
            scales=[MeaningScale.PHRASE, MeaningScale.SENTENCE],
        )

    apps_root = str(project_root / "apps")
    if apps_root not in sys.path:
        sys.path.insert(0, apps_root)
    from studio_api.main import app

    api_port = _free_port()
    web_port = _free_port()
    uv_config = uvicorn.Config(app, host="127.0.0.1", port=api_port, log_level="warning")
    server = uvicorn.Server(uv_config)
    threading.Thread(target=server.run, daemon=True).start()

    web_root = project_root / "apps" / "studio-web"
    dist = _ensure_studio_web_build(web_root)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(dist), **kwargs)

        def log_message(self, format, *args):  # noqa: A003
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", web_port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", api_port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.05)
    else:
        pytest.fail("API server failed to start")

    yield {
        "api": f"http://127.0.0.1:{api_port}",
        "web": f"http://127.0.0.1:{web_port}/",
    }
    server.should_exit = True
    httpd.shutdown()


def test_studio_five_workspace_flow(studio_stack):
    poem = (
        "The wind along the meadow path\n"
        "Turns every blade of grass to gold,\n"
        "And in the quiet after rain\n"
        "The earth remembers stories old."
    )
    api = studio_stack["api"]
    web = studio_stack["web"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.add_init_script(f"localStorage.setItem('SPWS_API', {api!r});")
        page.goto(web, wait_until="networkidle")
        page.wait_for_selector('[data-testid="btn-load"]')
        page.wait_for_selector('[data-testid="ws-import"]')

        page.fill("#draft", poem)
        page.click('[data-testid="btn-load"]')
        page.wait_for_function(
            "() => (document.querySelector('[data-testid=\"sum-import\"]')?.textContent || '').includes('Loaded')",
            timeout=10000,
        )

        page.click('[data-tab="analysis"]')
        page.click('[data-testid="btn-analyse"]')
        page.wait_for_function(
            "() => (document.querySelector('[data-testid=\"sum-analysis\"]')?.textContent || '').toLowerCase().includes('problem')",
            timeout=60000,
        )

        page.click('[data-tab="plan"]')
        page.click('[data-testid="btn-plan-create"]')
        page.wait_for_function(
            "() => (document.querySelector('[data-testid=\"sum-plan\"]')?.textContent || '').includes('Plan id')",
            timeout=30000,
        )
        page.click('[data-testid="btn-plan-confirm"]')
        page.wait_for_function(
            "() => (document.querySelector('[data-testid=\"sum-plan\"]')?.textContent || '').includes('Confirmed: true')",
            timeout=30000,
        )

        page.click('[data-tab="candidates"]')
        page.click('[data-testid="btn-propose"]')
        page.wait_for_selector('[data-testid="btn-accept-0"]', timeout=90000)
        page.click('[data-testid="btn-accept-0"]')
        page.wait_for_function(
            "() => (document.querySelector('[data-testid=\"sum-candidates\"]')?.textContent || '').toLowerCase().includes('accept')",
            timeout=60000,
        )

        page.click('[data-tab="export"]')
        page.click('[data-testid="btn-refresh-export"]')
        export_text = page.locator('[data-testid="sum-export"]').inner_text()
        assert export_text.strip()
        assert any(
            token in export_text.lower()
            for token in ("clean", "bundle", "provenance", "files", "export")
        )
        browser.close()
