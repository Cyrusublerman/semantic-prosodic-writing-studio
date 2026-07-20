#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)";cd "$ROOT"
python tools/generate_phase5_release.py --clean
python tools/validate_python_release.py --write-results
npm --prefix typescript ci
npm --prefix typescript run validate
npm --prefix typescript audit --json > schemas/contracts-core/0.1.0-dev.2/validation/npm-audit.json
python tools/finalize_phase5_release.py
python tools/verify_phase5_release.py
