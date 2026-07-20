#!/usr/bin/env python3
"""Acceptance checks for the governed PKL adapter vertical slice."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT.parent / "Library"


def _ok(msg: str) -> None:
    print(f"PASS  {msg}")


def _fail(msg: str) -> None:
    print(f"FAIL  {msg}")
    raise SystemExit(1)


def main() -> int:
    # 1. Sibling repos, not nested
    if not (ROOT / ".git").is_dir():
        _fail("SPWS missing .git")
    if not (LIBRARY / ".git").is_dir():
        _fail("Library missing .git")
    if (ROOT / "Library" / ".git").exists():
        _fail("Library nested inside SPWS")
    if (LIBRARY / "semantic-prosodic-writing-studio" / ".git").exists():
        _fail("SPWS nested inside Library")
    _ok("sibling git roots")

    # 2. Runtime outside repos
    from spws_storage import load_config

    config = load_config(ROOT / "config" / "spws.toml")
    for path in [
        config.pkl_cache_path,
        config.workspace_path,
        config.manuscripts_path,
        config.promotions_path,
        config.wordrare_storage_path,
    ]:
        resolved = path.resolve()
        if ROOT.resolve() in resolved.parents or resolved == ROOT.resolve():
            _fail(f"runtime path inside SPWS repo: {resolved}")
        if LIBRARY.resolve() in resolved.parents or resolved == LIBRARY.resolve():
            _fail(f"runtime path inside Library: {resolved}")
    _ok("runtime paths outside both repositories")

    # 3. Vertical demo without Library mutation
    before = subprocess.check_output(["git", "-C", str(LIBRARY), "rev-parse", "HEAD"], text=True).strip()
    from spws_cli.main import run_poetry_revision_demo

    result = run_poetry_revision_demo(accept_first=True)
    after = subprocess.check_output(["git", "-C", str(LIBRARY), "rev-parse", "HEAD"], text=True).strip()
    if before != after:
        _fail("Library HEAD changed during demo")
    status = subprocess.check_output(["git", "-C", str(LIBRARY), "status", "--porcelain"], text=True)
    if status.strip():
        _fail(f"Library working tree dirty after demo:\n{status}")
    promo = Path(result["promotion_path"])
    if not (promo / "bundle.json").is_file():
        _fail("promotion bundle missing")
    _ok(f"vertical demo run={result['run_id']} promotion={promo}")

    # 4. Schemas / compatibility artifacts present
    for rel in [
        "schemas/domain/0.1.0/input-package.schema.json",
        "schemas/domain/0.1.0/pkl-promotion-bundle.schema.json",
        "schemas/domain/0.1.0/compatibility.json",
        "typescript/domain/0.1.0/index.d.ts",
        "fixtures/ci/library-release-consumer.yml",
        ".github/workflows/spws-ci.yml",
    ]:
        if not (ROOT / rel).is_file():
            _fail(f"missing artifact {rel}")
    _ok("release and CI artifacts present")

    print(json.dumps({"accepted": True, "demo": result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
