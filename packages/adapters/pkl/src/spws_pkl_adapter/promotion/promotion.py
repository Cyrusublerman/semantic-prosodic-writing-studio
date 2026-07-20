"""Export reviewable promotion bundles without mutating the Library."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from spws_contracts_core.domain import PKLPromotionBundle
from spws_contracts_core.time import format_rfc3339_utc

from ..config import SpwsConfig


class PromotionExporter:
    def __init__(self, config: SpwsConfig) -> None:
        self.config = config
        self.output_root = config.runtime.promotions_path
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.library_root = config.pkl.repository_path

    def validate_bundle(self, bundle: PKLPromotionBundle) -> PKLPromotionBundle:
        # Round-trip through JSON wire format (strict Python validation rejects enums-as-str).
        return PKLPromotionBundle.model_validate_json(bundle.model_dump_json())

    def export_bundle(self, bundle: PKLPromotionBundle) -> Path:
        validated = self.validate_bundle(bundle)
        bundle_dir = self.output_root / validated.bundle_id
        bundle_dir.mkdir(parents=True, exist_ok=True)

        payload = validated.model_dump(mode="json")
        (bundle_dir / "bundle.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        if isinstance(validated.proposed_content, str):
            proposed_text = validated.proposed_content
        else:
            proposed_text = json.dumps(validated.proposed_content, indent=2, sort_keys=True)

        (bundle_dir / "proposed.md").write_text(proposed_text, encoding="utf-8")

        target_uid = validated.target_uid or validated.proposed_new_uid or "unknown"
        diff_lines = [
            f"# Promotion {validated.bundle_id}",
            f"operation: {validated.operation.value}",
            f"target_uid: {target_uid}",
            f"created_at: {format_rfc3339_utc(datetime.now(tz=UTC))}",
            "",
            "## Proposed content",
            proposed_text,
        ]
        (bundle_dir / "review.patch").write_text("\n".join(diff_lines) + "\n", encoding="utf-8")

        manifest = {
            "bundle_id": validated.bundle_id,
            "exported_at": format_rfc3339_utc(datetime.now(tz=UTC)),
            "library_path": str(self.library_root),
            "library_mutated": False,
        }
        (bundle_dir / "export-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return bundle_dir

    def assert_library_unmodified(self, before: dict[str, str]) -> bool:
        return self.snapshot_library_text() == before

    def snapshot_library_text(self) -> dict[str, str]:
        """Fingerprint Library files without requiring UTF-8 text."""
        import hashlib

        snapshot: dict[str, str] = {}
        if not self.library_root.exists():
            return snapshot
        for path in self.library_root.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts:
                continue
            rel = str(path.relative_to(self.library_root))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            snapshot[rel] = digest
        return snapshot
