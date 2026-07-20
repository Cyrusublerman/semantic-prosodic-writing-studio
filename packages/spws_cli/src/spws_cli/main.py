from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from spws_analysis import analyze_poem
from spws_contracts_core import PKLQuery, PKLPromotionBundle, RunManifest
from spws_contracts_core.domain import (
    PromotionOperation,
    ProvenanceStamp,
    ReadMode,
    RevisionDecisionKind,
    RightsState,
    PrivacyState,
)
from spws_ingestion import import_file
from spws_pkl_adapter import export_bundle, index_repository, query_index
from spws_revision import generate_candidates, record_decision
from spws_storage import WorkspaceStore

from .config import load_spws_config, project_root


def _utc_now():
    return datetime.now(UTC)


def run_poetry_revision_demo(*, accept_first: bool = True, poem_path: Path | None = None) -> dict:
    config = load_spws_config()
    root = project_root()
    fixture_root = root / "fixtures" / "pkl"
    poem_path = poem_path or (root / "fixtures" / "poetry" / "sample_poem.txt")
    cache_path = config.pkl_cache_path
    cache_path.mkdir(parents=True, exist_ok=True)

    index_repository(fixture_root, cache_path=cache_path)
    pkl_hits = query_index(PKLQuery(text="meter", result_limit=5), cache_path)

    store = WorkspaceStore(config)
    package = import_file(poem_path)
    raw = store.persist_input_package(package)
    analysis = analyze_poem(package.text or "", pkl_hits)
    candidates = generate_candidates(package.text or "", analysis)

    run_id = f"run-{uuid4().hex[:12]}"
    manifest = RunManifest(
        run_id=run_id,
        pipeline_id="poetry-revision",
        started_at=_utc_now(),
        finished_at=_utc_now(),
        read_mode=ReadMode.SNAPSHOT,
        component_versions={"spws": "0.1.0"},
        input_refs=[raw.source_id],
        output_refs=[],
        status="completed",
    )
    store.save_run(manifest)

    chosen_ids: list[str] = []
    if candidates:
        chosen_ids = [candidates[0].candidate_id] if accept_first else []
    decision = record_decision(
        store,
        run_id=run_id,
        candidates=candidates,
        text=package.text or "",
        kind=RevisionDecisionKind.ACCEPT if chosen_ids else RevisionDecisionKind.DEFER,
        candidate_ids=chosen_ids,
        rationale="demo auto-accept first candidate" if chosen_ids else "demo deferred",
    )

    bundle = PKLPromotionBundle(
        bundle_id=f"promo-{uuid4().hex[:12]}",
        operation=PromotionOperation.CREATE,
        proposed_new_uid=f"uid-{uuid4().hex[:12]}",
        proposed_content={
            "title": "Observed revision insight",
            "object_type": "insight",
            "body": decision.resulting_text or package.text,
            "source_run": run_id,
        },
        source_evidence=[hit.model_dump(mode="json") for hit in pkl_hits[:3]],
        originating_run_id=run_id,
        provenance=ProvenanceStamp(
            repository_identity="spws-demo",
            commit_sha="FIXTURE",
            extracted_at=_utc_now(),
            rights=RightsState.PUBLIC,
            privacy=PrivacyState.INTERNAL,
        ),
        confidence=0.6,
        created_at=_utc_now(),
    )
    export_path = export_bundle(bundle, config.promotions_path)
    store.close()
    return {
        "run_id": run_id,
        "source_id": raw.source_id,
        "candidate_count": len(candidates),
        "decision_id": decision.decision_id,
        "promotion_path": str(export_path),
        "analysis_engine": analysis.engine,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="spws")
    sub = parser.add_subparsers(dest="command", required=True)

    pkl = sub.add_parser("pkl", help="PKL snapshot operations")
    pkl_sub = pkl.add_subparsers(dest="pkl_command", required=True)
    index_cmd = pkl_sub.add_parser("index", help="Index PKL snapshot")
    index_cmd.add_argument("--commit", default=None)
    index_cmd.add_argument("--source", default=None, help="Repository or fixture path")
    query_cmd = pkl_sub.add_parser("query", help="Query indexed PKL knowledge")
    query_cmd.add_argument("text")

    demo = sub.add_parser("demo", help="Vertical slice demos")
    demo_sub = demo.add_subparsers(dest="demo_command", required=True)
    demo_sub.add_parser("poetry-revision", help="Poetry revision vertical slice")

    promo = sub.add_parser("promotion", help="Promotion bundle operations")
    promo_sub = promo.add_subparsers(dest="promotion_command", required=True)
    export_cmd = promo_sub.add_parser("export", help="Validate and copy bundle to promotions dir")
    export_cmd.add_argument("bundle")
    promo_sub.add_parser("validate", help="Validate promotion bundle").add_argument("bundle")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_spws_config()

    if args.command == "pkl":
        if args.pkl_command == "index":
            source = Path(args.source) if args.source else config.repository_path
            if not source.exists():
                source = project_root() / "fixtures" / "pkl"
            manifest = index_repository(source, commit=args.commit, cache_path=config.pkl_cache_path)
            print(json.dumps(manifest, indent=2))
            return 0
        if args.pkl_command == "query":
            hits = query_index(PKLQuery(text=args.text), config.pkl_cache_path)
            print(json.dumps([hit.model_dump(mode="json") for hit in hits], indent=2))
            return 0

    if args.command == "demo" and args.demo_command == "poetry-revision":
        result = run_poetry_revision_demo()
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "promotion":
        bundle_path = Path(args.bundle)
        from spws_pkl_adapter import validate_bundle

        bundle = validate_bundle(bundle_path)
        if args.promotion_command == "validate":
            print(json.dumps({"valid": True, "bundle_id": bundle.bundle_id}, indent=2))
            return 0
        if args.promotion_command == "export":
            path = export_bundle(bundle, config.promotions_path)
            print(json.dumps({"exported": str(path)}, indent=2))
            return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
