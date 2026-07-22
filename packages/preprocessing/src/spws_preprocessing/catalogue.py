"""Propose Library fragment candidates from source text. Never invent attribution."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from spws_contracts_core.domain import (
    AuthorshipClass,
    MeaningScale,
    PrivacyState,
    RightsState,
    normalize_rights_ingest,
)
from spws_domain.ids import new_id
from spws_semantics.encode import TaggingService
from spws_semantics.unitise import unitise_text

_NON_CREATIVE_PREFIX = re.compile(r"^(TODO|NOTE|FIXME|XXX)\b", re.IGNORECASE)
_CODE_FENCE = re.compile(r"^```|^~~~")
_TAGGER = TaggingService()

# Safe defaults pending human review — never invent richer attribution (D006).
_DEFAULT_RIGHTS = RightsState.RESTRICTED_PENDING_REVIEW
_DEFAULT_PRIVACY = PrivacyState.PRIVATE


def _looks_creative(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) <= 15:
        return False
    if _NON_CREATIVE_PREFIX.match(stripped):
        return False
    if stripped.startswith("#"):
        return False
    if _CODE_FENCE.search(stripped) or "```" in stripped:
        return False
    return True


def _fragment_type(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) >= 3:
        avg = sum(len(line.strip()) for line in lines) / len(lines)
        if avg <= 48:
            return "poetry"
    if len(text.strip()) < 80:
        return "phrase"
    return "prose"


def _span_dict(span: Any) -> dict[str, Any] | None:
    if span is None:
        return None
    return span.model_dump(mode="json")


def propose_fragments(path: Path) -> dict[str, Any]:
    """Read ``path``, unitise, propose unreviewed fragment candidates.

    Never invents attribution. Defaults rights=restricted, privacy=private.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    units = unitise_text(
        text,
        source_object_id=str(path),
        scales=[MeaningScale.SENTENCE, MeaningScale.PHRASE],
    )
    proposals: list[dict[str, Any]] = []
    seen: set[str] = set()
    for unit in units:
        if unit.scale not in (MeaningScale.SENTENCE, MeaningScale.PHRASE):
            continue
        body = unit.text.strip()
        if body in seen:
            continue
        if not _looks_creative(body):
            continue
        seen.add(body)
        tags = _TAGGER.rule_tags(body)
        proposals.append(
            {
                "proposal_id": new_id("fragprop"),
                "fragment_type": _fragment_type(body),
                "authorship": AuthorshipClass.USER.value,
                "rights": normalize_rights_ingest(_DEFAULT_RIGHTS).value,
                "privacy": _DEFAULT_PRIVACY.value,
                "text": body,
                "span": _span_dict(unit.span),
                "source_unit_id": unit.unit_id,
                "suggested_tone": tags.get("affect_tags", []),
                "suggested_themes": tags.get("theme_tags", []),
                "suggested_domain": tags.get("domain_tags", []),
                "suggested_imagery": tags.get("imagery_tags", []),
                "review_status": "unreviewed",
                "canonical": False,
            }
        )
    return {
        "source": str(path),
        "proposal_count": len(proposals),
        "proposals": proposals,
        "promotion_ready": False,
    }


def to_promotion_draft(proposal: dict[str, Any]) -> dict[str, Any]:
    """Map a proposal to Library fragment frontmatter fields.

    Preserves fail-closed rights/privacy; never invents attribution fields.
    """
    text = str(proposal.get("text") or "")
    title = text.strip().splitlines()[0][:80] if text.strip() else "untitled fragment"
    rights = normalize_rights_ingest(proposal.get("rights") or _DEFAULT_RIGHTS).value
    privacy = proposal.get("privacy") or _DEFAULT_PRIVACY.value
    try:
        privacy = PrivacyState(str(privacy)).value
    except ValueError:
        privacy = _DEFAULT_PRIVACY.value
    return {
        "title": title,
        "object_type": "fragment",
        "fragment_type": proposal.get("fragment_type") or "prose",
        "content": text,
        "authorship": proposal.get("authorship") or AuthorshipClass.USER.value,
        "rights": rights,
        "privacy": privacy,
        "status": "draft",
        "review_status": proposal.get("review_status") or "unreviewed",
        "canonical": bool(proposal.get("canonical", False)),
        "themes": list(proposal.get("suggested_themes") or []),
        "tone": list(proposal.get("suggested_tone") or []),
        "span": proposal.get("span"),
    }
