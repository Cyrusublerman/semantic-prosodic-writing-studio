"""Revision session: propose → decide → manuscript child."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from spws_contracts_core.domain import (
    ExchangeEnvelope,
    ManuscriptVersion,
    RevisionDecision,
    RevisionDecisionKind,
)
from spws_domain.ids import new_id

from .export_pack import build_export_pack
from .rich_revise import accept_candidate_to_manuscript, revise_poetry


def _wrap_envelopes(result: dict) -> dict[str, Any]:
    """Wrap candidate_set and evaluation in ExchangeEnvelope payloads."""
    candidate_set = result.get("candidate_set") or {}
    evaluation = result.get("evaluation") or {}
    created = datetime.now(UTC)
    envelopes = {
        "candidate_set": ExchangeEnvelope(
            object_id=str(candidate_set.get("set_id") or new_id("cset")),
            object_type="CandidateSet",
            created_at=created,
            payload=candidate_set if isinstance(candidate_set, dict) else {},
        ).model_dump(mode="json"),
        "evaluation": ExchangeEnvelope(
            object_id=str(evaluation.get("bundle_id") or new_id("eb")),
            object_type="EvaluationBundle",
            created_at=created,
            payload=evaluation if isinstance(evaluation, dict) else {},
        ).model_dump(mode="json"),
    }
    return envelopes


def _apply_human_preference(
    evaluation: dict | None,
    *,
    candidate_id: str,
    kind: RevisionDecisionKind,
    rationale: str | None,
) -> dict | None:
    """Update or append human_preference EvaluationResult from decide kind+rationale."""
    if evaluation is None:
        return None
    if not isinstance(evaluation, dict):
        return evaluation

    judgement = kind.value if not rationale else f"{kind.value}: {rationale}"
    measured = 1.0 if kind is RevisionDecisionKind.ACCEPT else 0.0
    results = list(evaluation.get("results") or [])
    updated = False
    for item in results:
        if item.get("criterion") != "human_preference":
            continue
        subject = item.get("subject_id")
        if subject and candidate_id and subject != candidate_id:
            continue
        item["human_judgement"] = judgement
        item["measured_value"] = measured
        item["inferred_label"] = "human_judged"
        evidence = list(item.get("evidence") or [])
        evidence = [e for e in evidence if e != "pending_decision"]
        evidence.append(f"decision:{kind.value}")
        item["evidence"] = evidence
        updated = True
        if subject == candidate_id:
            break
    if not updated:
        results.append(
            {
                "evaluation_id": new_id("ev"),
                "subject_id": candidate_id,
                "criterion": "human_preference",
                "measured_value": measured,
                "inferred_label": "human_judged",
                "human_judgement": judgement,
                "evidence": [f"decision:{kind.value}"],
                "warnings": [],
                "schema_version": "0.1.0",
            }
        )
    evaluation = {**evaluation, "results": results}
    return evaluation


def propose_revision(
    target: Path | str,
    *,
    brief: str = "improve diction",
    config: Any,
    diagnosis: Any | None = None,
    work_plan: dict | None = None,
) -> dict:
    """Wrap revise_poetry and persist proposal JSON under runs_path."""
    result = revise_poetry(
        Path(target),
        brief=brief,
        config=config,
        diagnosis=diagnosis,
        work_plan=work_plan,
    )
    envelopes = _wrap_envelopes(result)
    result = {**result, "envelopes": envelopes}
    run_id = new_id("run")
    proposal = {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "proposal": result,
        "envelopes": envelopes,
        "target": str(target),
        "brief": brief,
    }
    runs = Path(getattr(config, "runs_path"))
    runs.mkdir(parents=True, exist_ok=True)
    path = runs / f"{run_id}-proposal.json"
    path.write_text(json.dumps(proposal, indent=2, ensure_ascii=False), encoding="utf-8")
    proposal["proposal_path"] = str(path)
    return proposal


def decide_revision(
    config: Any,
    proposal_path: Path | str,
    candidate_id: str,
    kind: str | RevisionDecisionKind,
    *,
    store: Any | None = None,
    decided_by: str = "human",
    rationale: str | None = None,
    export_dir: Path | str | None = None,
) -> dict:
    """Apply line change for accept, save ManuscriptVersion child, record decision."""
    from spws_storage.manuscripts import save_manuscript

    path = Path(proposal_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    proposal = payload.get("proposal") or payload
    kind_enum = RevisionDecisionKind(kind) if not isinstance(kind, RevisionDecisionKind) else kind

    manuscript_data = proposal["manuscript"]
    parent = ManuscriptVersion.model_validate_json(json.dumps(manuscript_data))
    candidates = (proposal.get("candidate_set") or {}).get("candidates") or []
    lookup = {c["candidate_id"]: c for c in candidates}
    if candidate_id not in lookup and kind_enum == RevisionDecisionKind.ACCEPT:
        raise KeyError(f"candidate_id not found: {candidate_id}")

    # Always persist parent so accept yields parent+child lineage.
    parent_path = save_manuscript(config, parent)

    resulting_text = parent.text
    child: ManuscriptVersion | None = None
    if kind_enum == RevisionDecisionKind.ACCEPT:
        cand = lookup[candidate_id]
        # Refuse accept when candidate provenance quotes restricted sources.
        from .rich_revise import filter_restricted_source_hits

        provenance_hits: list[dict] = []
        for src in cand.get("source_material") or []:
            if src:
                provenance_hits.append({"unit_id": src, "rights": cand.get("rights")})
        if cand.get("rights") is not None:
            provenance_hits.append(
                {"unit_id": cand.get("candidate_id"), "rights": cand["rights"]}
            )
        filter_restricted_source_hits(provenance_hits, config, raise_on_restricted=True)

        line_index = cand.get("line_index")
        if line_index is None:
            line_index = proposal.get("target_line_index")
        child = accept_candidate_to_manuscript(
            parent.text,
            cand["content"],
            parent_version_id=parent.version_id,
            line_index=line_index,
            manuscript_id=parent.manuscript_id,
        )
        resulting_text = child.text
        ms_path = save_manuscript(config, child)
    elif kind_enum == RevisionDecisionKind.MANUAL_REPLACE:
        # Expect candidate content as replacement for diagnosed line
        cand = lookup.get(candidate_id)
        if cand is None:
            raise KeyError(f"candidate_id not found: {candidate_id}")
        line_index = cand.get("line_index", proposal.get("target_line_index", 0))
        child = accept_candidate_to_manuscript(
            parent.text,
            cand["content"],
            parent_version_id=parent.version_id,
            line_index=line_index,
            manuscript_id=parent.manuscript_id,
        )
        resulting_text = child.text
        ms_path = save_manuscript(config, child)
    else:
        # reject / defer / combine — keep parent, no child merge
        ms_path = save_manuscript(config, parent)
        child = parent

    decision = RevisionDecision(
        decision_id=f"dec-{uuid4().hex[:12]}",
        run_id=payload.get("run_id") or new_id("run"),
        candidate_ids=[candidate_id] if candidate_id else [],
        kind=kind_enum,
        decided_at=datetime.now(UTC),
        decided_by=decided_by,
        rationale=rationale,
        resulting_text=resulting_text,
    )
    if store is not None and hasattr(store, "save_revision_decision"):
        store.save_revision_decision(decision)

    decisions_path = Path(getattr(config, "workspace_path", Path(getattr(config, "runs_path")).parent)) / "decisions"
    decisions_path.mkdir(parents=True, exist_ok=True)
    dec_path = decisions_path / f"{decision.decision_id}.json"
    dec_path.write_text(decision.model_dump_json(indent=2), encoding="utf-8")

    # D007: record human preference on the evaluation bundle after accept/reject.
    evaluation = _apply_human_preference(
        proposal.get("evaluation"),
        candidate_id=candidate_id,
        kind=kind_enum,
        rationale=rationale,
    )
    if evaluation is not None:
        proposal["evaluation"] = evaluation
        payload["proposal"] = proposal
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    run_manifest = {
        "run_id": decision.run_id,
        "proposal_path": str(path),
        "decision_id": decision.decision_id,
        "kind": kind_enum.value,
        "manuscript_path": str(ms_path),
    }

    export_payload = None
    if export_dir is not None and child is not None:
        export_payload = build_export_pack(
            child,
            proposal.get("diagnosis"),
            decision,
            run_manifest,
            out_dir=Path(export_dir),
            evaluation=evaluation or proposal.get("evaluation"),
        )

    return {
        "decision": decision.model_dump(mode="json"),
        "manuscript": child.model_dump(mode="json") if child else manuscript_data,
        "manuscript_path": str(ms_path),
        "parent_manuscript_path": str(parent_path),
        "decision_path": str(dec_path),
        "export": export_payload,
        "run_manifest": run_manifest,
        "evaluation": evaluation,
    }
