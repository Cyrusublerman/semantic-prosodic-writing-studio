from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from jsonschema import Draft202012Validator

import spws_contracts_core
from spws_contracts_core.digests import canonical_json_bytes
from spws_contracts_core.release import (
    BUNDLE_SCHEMA_ID,
    RELEASE_MODELS,
    SCHEMA_DIALECT,
    SCHEMA_RELEASE_VERSION,
    release_archive_resource,
    schema_id_for,
)

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "schemas/contracts-core" / SCHEMA_RELEASE_VERSION


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_versions() -> None:
    assert spws_contracts_core.__version__ == "0.1.0.dev2"
    assert SCHEMA_RELEASE_VERSION == "0.1.0-dev.2"


def test_registry() -> None:
    assert len(RELEASE_MODELS) == 39
    assert schema_id_for("core-object-envelope").endswith(":0.1.0-dev.2")


def test_bundle() -> None:
    schema = load(R / "bundle.schema.json")
    assert isinstance(schema, dict)
    assert schema["$schema"] == SCHEMA_DIALECT
    assert schema["$id"] == BUNDLE_SCHEMA_ID
    assert len(schema["oneOf"]) == 39
    Draft202012Validator.check_schema(schema)


def test_models() -> None:
    for slug in RELEASE_MODELS:
        schema = load(R / "models" / f"{slug}.schema.json")
        assert isinstance(schema, dict)
        assert schema["$id"] == schema_id_for(slug)
        Draft202012Validator.check_schema(schema)


def test_fixture_coverage() -> None:
    manifest = load(R / "fixtures/manifest.json")
    assert isinstance(manifest, dict)
    tags = {tag for fixture in manifest["fixtures"] for tag in fixture["tags"]}
    assert manifest["fixture_count"] == 21
    assert {
        "minimal",
        "complete",
        "ambiguous",
        "unavailable",
        "withheld",
        "failed",
        "identity",
        "digest",
        "parent-cycle",
        "policy",
        "provenance",
        "unicode",
        "emoji",
        "combining-mark",
        "crlf",
        "repeated-quote",
        "external-transmission",
        "mixed-source",
        "deletion",
    } <= tags


def test_summary() -> None:
    summary = load(R / "validation/summary.json")
    assert isinstance(summary, dict)
    assert summary["ok"]
    assert all(summary["checks"].values())
    assert summary["fixture_count"] == 21


def test_types() -> None:
    declarations = (R / "generated/typescript.d.ts").read_text(encoding="utf-8")
    assert "ContractsCoreBundle" in declarations
    assert "= any;" not in declarations


def test_manifest() -> None:
    manifest = load(R / "digest.json")
    assert isinstance(manifest, dict)
    records = []
    for expected in manifest["files"]:
        raw = (R / expected["path"]).read_bytes()
        assert len(raw) == expected["byte_length"]
        assert hashlib.sha256(raw).hexdigest() == expected["sha256"]
        records.append(
            {
                "path": expected["path"],
                "byte_length": expected["byte_length"],
                "sha256": expected["sha256"],
            }
        )
    assert (
        hashlib.sha256(canonical_json_bytes(records)).hexdigest()
        == manifest["release_root_sha256"]
    )


def test_archive() -> None:
    resource = release_archive_resource()
    data = resource.read_bytes()
    report = load(ROOT / "STAGE5_CAPABILITY_REPORT.json")
    assert isinstance(report, dict)
    assert hashlib.sha256(data).hexdigest() == report["distribution_archive"]["sha256"]
    with zipfile.ZipFile(Path(resource)) as archive:
        assert "digest.json" in archive.namelist()
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())
