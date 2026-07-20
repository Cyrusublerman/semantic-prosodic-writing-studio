from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from spws_contracts_core import RevisionDecision
from spws_contracts_core.domain import RevisionDecisionKind
from spws_storage import WorkspaceStore

from .candidates import RevisionCandidate, apply_decision


def _utc_now():
    return datetime.now(UTC)


def record_decision(
    store: WorkspaceStore,
    *,
    run_id: str,
    candidates: list[RevisionCandidate],
    text: str,
    kind: RevisionDecisionKind,
    candidate_ids: list[str],
    decided_by: str = "human",
    rationale: str | None = None,
) -> RevisionDecision:
    resulting = apply_decision(text, candidates, candidate_ids) if candidate_ids else text
    decision = RevisionDecision(
        decision_id=f"dec-{uuid4().hex[:12]}",
        run_id=run_id,
        candidate_ids=candidate_ids,
        kind=kind,
        decided_at=_utc_now(),
        decided_by=decided_by,
        rationale=rationale,
        resulting_text=resulting,
    )
    store.save_revision_decision(decision)
    return decision
