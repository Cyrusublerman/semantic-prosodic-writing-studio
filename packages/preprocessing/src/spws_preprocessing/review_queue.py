"""Human review queue for catalogue fragment proposals."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from spws_domain.ids import new_id

from .catalogue import to_promotion_draft


def save_review_bundle(
    proposals: list[dict[str, Any]],
    out_dir: str | Path,
) -> dict[str, Any]:
    """Persist a review bundle with promotion drafts. Returns summary path metadata."""
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    bundle_id = new_id("review")
    drafts = [to_promotion_draft(p) for p in proposals]
    bundle = {
        "bundle_id": bundle_id,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "proposal_count": len(proposals),
        "proposals": proposals,
        "promotion_drafts": drafts,
        "status": "pending",
    }
    path = root / f"{bundle_id}.json"
    path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "bundle_id": bundle_id,
        "path": str(path),
        "proposal_count": len(proposals),
        "status": "pending",
    }


def list_pending(out_dir: str | Path) -> list[dict[str, Any]]:
    """List review bundles under ``out_dir`` whose status is pending / unreviewed."""
    root = Path(out_dir)
    if not root.is_dir():
        return []
    pending: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        status = str(data.get("status") or "pending").lower()
        if status in {"pending", "unreviewed"}:
            pending.append(
                {
                    "bundle_id": data.get("bundle_id") or path.stem,
                    "path": str(path),
                    "proposal_count": data.get("proposal_count", 0),
                    "status": status,
                    "created_at": data.get("created_at"),
                }
            )
    return pending
