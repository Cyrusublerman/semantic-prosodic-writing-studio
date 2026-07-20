#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from spws_contracts_core.digests import canonical_json_bytes

ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION = "0.1.0-dev.2"
RELEASE_REL = Path("schemas/contracts-core") / RELEASE_VERSION
ARCHIVE_REL = Path("src/spws_contracts_core/data/releases") / f"contracts-core-{RELEASE_VERSION}.zip"
EXPECTED_ARCHIVE_SHA256 = "d0281b6dd8e49c0100225540e40389256a92d7571a1f279a9994fd2a6ce6f8d7"
EXPECTED_RELEASE_ROOT = "ac25160482e01ef38c4281fa6444e2b2772885ebccb10588c001aee225d30488"


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def changed_paths(base_ref: str) -> list[str]:
    output = git_output("diff", "--name-only", f"{base_ref}...HEAD")
    return [line.strip() for line in output.splitlines() if line.strip()]


def verify_manifest(release: Path) -> tuple[int, str]:
    manifest_path = release / "digest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest.get("files")
    if not isinstance(records, list):
        raise SystemExit("release digest manifest has no files array")

    expected_paths = {record["path"] for record in records}
    actual_paths = {
        path.relative_to(release).as_posix()
        for path in release.rglob("*")
        if path.is_file() and path.name != "digest.json"
    }
    if actual_paths != expected_paths:
        missing = sorted(expected_paths - actual_paths)
        extra = sorted(actual_paths - expected_paths)
        raise SystemExit(
            "release manifest membership changed"
            + (f"\nmissing: {missing}" if missing else "")
            + (f"\nextra: {extra}" if extra else "")
        )

    canonical_records: list[dict[str, object]] = []
    for record in records:
        path = release / record["path"]
        raw = path.read_bytes()
        actual = {
            "path": record["path"],
            "byte_length": len(raw),
            "sha256": sha256_bytes(raw),
        }
        if actual != record:
            raise SystemExit(f"release file diverged from manifest: {record['path']}")
        canonical_records.append(actual)

    root = sha256_bytes(canonical_json_bytes(canonical_records))
    if root != manifest.get("release_root_sha256"):
        raise SystemExit("release manifest root does not match file records")
    if root != EXPECTED_RELEASE_ROOT:
        raise SystemExit("immutable 0.1.0-dev.2 release root changed")
    if manifest.get("file_count") != len(records):
        raise SystemExit("release manifest file_count is incorrect")
    return len(records), root


def verify_archive(archive: Path, release_file_count: int) -> str:
    raw = archive.read_bytes()
    digest = sha256_bytes(raw)
    if digest != EXPECTED_ARCHIVE_SHA256:
        raise SystemExit("immutable 0.1.0-dev.2 archive digest changed")
    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        if len(infos) != release_file_count + 1:
            raise SystemExit("immutable archive membership count changed")
        if "digest.json" not in {info.filename for info in infos}:
            raise SystemExit("immutable archive is missing digest.json")
        if any(info.date_time != (1980, 1, 1, 0, 0, 0) for info in infos):
            raise SystemExit("immutable archive timestamps are not deterministic")
    return digest


def verify_repository_paths(base_ref: str) -> None:
    git_root = Path(git_output("rev-parse", "--show-toplevel"))
    package_prefix = ROOT.relative_to(git_root).as_posix() + "/"
    release_prefix = package_prefix + RELEASE_REL.as_posix() + "/"
    archive_path = package_prefix + ARCHIVE_REL.as_posix()
    modified = [
        path
        for path in changed_paths(base_ref)
        if path.startswith(release_prefix) or path == archive_path
    ]
    if modified:
        raise SystemExit(
            "published release 0.1.0-dev.2 is immutable; create a new version instead:\n- "
            + "\n- ".join(modified)
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref")
    args = parser.parse_args()

    release = ROOT / RELEASE_REL
    archive = ROOT / ARCHIVE_REL
    capability_path = ROOT / "STAGE5_CAPABILITY_REPORT.json"
    if not release.is_dir() or not archive.is_file():
        raise SystemExit("immutable 0.1.0-dev.2 release or archive is missing")

    file_count, release_root = verify_manifest(release)
    archive_digest = verify_archive(archive, file_count)

    capability = json.loads(capability_path.read_text(encoding="utf-8"))
    if capability.get("release_root_sha256") != release_root:
        raise SystemExit("capability report release root changed")
    if capability.get("distribution_archive", {}).get("sha256") != archive_digest:
        raise SystemExit("capability report archive digest changed")

    if args.base_ref:
        verify_repository_paths(args.base_ref)

    print(
        json.dumps(
            {
                "ok": True,
                "release": RELEASE_VERSION,
                "file_count": file_count,
                "release_root_sha256": release_root,
                "archive_sha256": archive_digest,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
