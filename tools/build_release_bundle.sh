#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VERSION="${CONTRACTS_RELEASE_VERSION:-0.1.0}"
OUT="dist/release"
rm -rf "$OUT"
mkdir -p "$OUT"

# Schemas
mkdir -p "$OUT/schemas"
cp -a schemas/domain "$OUT/schemas/"
cp -a schemas/contracts-core "$OUT/schemas/" 2>/dev/null || true

# TypeScript declarations
mkdir -p "$OUT/typescript"
cp -a typescript/domain "$OUT/typescript/"

# Fixtures (synthetic only)
mkdir -p "$OUT/fixtures"
cp -a fixtures/contracts "$OUT/fixtures/"
cp -a fixtures/pkl "$OUT/fixtures/"
cp -a fixtures/poetry "$OUT/fixtures/"

# Compatibility manifest
cat > "$OUT/compatibility-manifest.json" <<EOF
{
  "release": "$VERSION",
  "contracts_core": "0.1.0-dev.2",
  "domain_schemas": "0.1.0",
  "compatible_with": ["0.1.0"],
  "repository": "https://github.com/Cyrusublerman/semantic-prosodic-writing-studio"
}
EOF

# Python wheel (uv avoids ensurepip isolation issues)
mkdir -p "$OUT/wheels"
if command -v uv >/dev/null 2>&1; then
  uv build --wheel packages/contracts/core --out-dir "$OUT/wheels"
else
  python -m build --wheel --no-isolation packages/contracts/core -o "$OUT/wheels"
fi

# Checksums
(
  cd "$OUT"
  find . -type f ! -name 'SHA256SUMS' -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
)

# Provenance
cat > "$OUT/PROVENANCE.json" <<EOF
{
  "built_from": "semantic-prosodic-writing-studio",
  "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo unknown)",
  "release": "$VERSION",
  "artifacts": ["schemas", "typescript", "fixtures", "wheels", "compatibility-manifest.json"]
}
EOF

echo "Release bundle at $OUT"
ls -la "$OUT"
