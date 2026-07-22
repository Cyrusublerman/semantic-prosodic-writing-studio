from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from spws_analysis import analyze_poem
from spws_contracts_core import PKLQuery, PKLPromotionBundle, RunManifest
from spws_contracts_core.domain import (
    MeaningScale,
    PromotionOperation,
    ProvenanceStamp,
    ReadMode,
    RevisionDecisionKind,
    RightsState,
    PrivacyState,
    SimilarityQuery,
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

    meaning = sub.add_parser("meaning", help="Meaning gauge operations")
    meaning_sub = meaning.add_subparsers(dest="meaning_command", required=True)
    meaning_index = meaning_sub.add_parser("index", help="Index a text file into the meaning store")
    meaning_index.add_argument("path")
    meaning_index.add_argument("--source-id", default=None)
    meaning_lib = meaning_sub.add_parser("index-library", help="Index markdown fragments under a root")
    meaning_lib.add_argument("--root", required=True, help="Directory of fragment markdown files")
    meaning_similar = meaning_sub.add_parser("similar", help="Find similar meaning units")
    meaning_similar.add_argument("text")
    meaning_similar.add_argument("--limit", type=int, default=5)
    meaning_explain = meaning_sub.add_parser("explain", help="Explain tags/profile for text")
    meaning_explain.add_argument("text")

    catalogue = sub.add_parser("catalogue", help="Note/fragment catalogue proposals")
    catalogue_sub = catalogue.add_subparsers(dest="catalogue_command", required=True)
    catalogue_propose = catalogue_sub.add_parser("propose", help="Propose fragments from a note")
    catalogue_propose.add_argument("--source", required=True)
    catalogue_draft = catalogue_sub.add_parser("promotion-draft", help="Write promotion drafts from proposals JSON")
    catalogue_draft.add_argument("--proposals", required=True)
    catalogue_draft.add_argument("--out", required=True)

    board = sub.add_parser("board", help="Source board")
    board_sub = board.add_subparsers(dest="board_command", required=True)
    board_query = board_sub.add_parser("query", help="Query meaning-similar sources")
    board_query.add_argument("text")

    plan_cmd = sub.add_parser("plan", help="Work planning")
    plan_sub = plan_cmd.add_subparsers(dest="plan_command", required=True)
    plan_create = plan_sub.add_parser("create", help="Create a work plan from a brief")
    plan_create.add_argument("--brief", required=True)
    plan_create.add_argument("--form", default="haiku")
    plan_create.add_argument("--out", default=None, help="Save plan JSON path")
    plan_confirm = plan_sub.add_parser("confirm", help="Confirm a work plan JSON")
    plan_confirm.add_argument("path")

    analyse = sub.add_parser("analyse", help="Analyse poem or prose")
    analyse_sub = analyse.add_subparsers(dest="analyse_command", required=True)
    analyse_poem = analyse_sub.add_parser("poem", help="Analyse a poem file")
    analyse_poem.add_argument("path")
    analyse_prose = analyse_sub.add_parser("prose", help="Analyse a prose file")
    analyse_prose.add_argument("path")

    revise = sub.add_parser("revise", help="Revision assist")
    revise_sub = revise.add_subparsers(dest="revise_command", required=True)
    revise_poetry = revise_sub.add_parser("poetry", help="Propose poetry revisions (alias of propose)")
    revise_poetry.add_argument("--target", required=True)
    revise_poetry.add_argument("--brief", default="improve diction")
    revise_poetry.add_argument("--plan", default=None, help="Confirmed work plan JSON")
    revise_propose = revise_sub.add_parser("propose", help="Propose revision candidates and save session")
    revise_propose.add_argument("--target", required=True)
    revise_propose.add_argument("--brief", default="improve diction")
    revise_propose.add_argument("--plan", default=None)
    revise_decide = revise_sub.add_parser("decide", help="Accept/reject a proposed candidate")
    revise_decide.add_argument("--proposal", required=True)
    revise_decide.add_argument("--candidate", required=True)
    revise_decide.add_argument(
        "--kind",
        required=True,
        choices=["accept", "reject", "combine", "defer", "manual_replace"],
    )
    revise_decide.add_argument(
        "--export-dir",
        default=None,
        help="Write D014 export pack on accept (txt/md/json/provenance/diff)",
    )

    generate = sub.add_parser("generate", help="Generation")
    generate_sub = generate.add_subparsers(dest="generate_command", required=True)
    generate_collage = generate_sub.add_parser("collage", help="Generate collage poem from meaning board")
    generate_collage.add_argument("--theme", required=True)
    generate_collage.add_argument("--lines", type=int, default=3)
    generate_collage.add_argument("--plan", default=None, help="Optional confirmed work plan JSON")
    generate_collage.add_argument(
        "--accept",
        action="store_true",
        help="Human-gate accept collage into ManuscriptVersion (explicit only)",
    )

    assist = sub.add_parser("assist", help="Inline reword assist")
    assist_sub = assist.add_subparsers(dest="assist_command", required=True)
    assist_reword = assist_sub.add_parser("reword", help="Propose reword candidates for text")
    assist_reword.add_argument("text")
    assist_reword.add_argument(
        "--mode",
        default="rarefy",
        choices=["rarefy", "ground_to_library", "meter_fit", "theme_align"],
    )

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

    if args.command == "meaning":
        from spws_semantics import MeaningGauge

        # Quality: from_config (hash only if config.debug_hash_embeddings)
        try:
            gauge = MeaningGauge.from_config(config)
        except RuntimeError:
            gauge = MeaningGauge.from_config(config, allow_hash_fallback=True)
        if args.meaning_command == "index":
            text = Path(args.path).read_text(encoding="utf-8")
            units = gauge.index_text(text, source_object_id=args.source_id or args.path)
            print(json.dumps({"indexed_units": len(units), "store_count": gauge.count()}, indent=2))
            return 0
        if args.meaning_command == "index-library":
            stats = gauge.index_directory(Path(args.root), skip_unknown_rights=True)
            print(json.dumps(stats, indent=2))
            return 0
        if args.meaning_command == "similar":
            result = gauge.similar(
                SimilarityQuery(
                    text=args.text,
                    result_limit=args.limit,
                    target_scales=[MeaningScale.SENTENCE, MeaningScale.PARAGRAPH, MeaningScale.PHRASE],
                )
            )
            print(json.dumps(result.model_dump(mode="json"), indent=2))
            return 0
        if args.meaning_command == "explain":
            profile = gauge.profile_text(args.text)
            print(json.dumps(profile.model_dump(mode="json"), indent=2))
            return 0

    if args.command == "catalogue" and args.catalogue_command == "propose":
        from spws_preprocessing import propose_fragments

        proposals = propose_fragments(Path(args.source))
        print(json.dumps(proposals, indent=2))
        return 0

    if args.command == "catalogue" and args.catalogue_command == "promotion-draft":
        from spws_preprocessing import to_promotion_draft

        data = json.loads(Path(args.proposals).read_text(encoding="utf-8"))
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        written = []
        for i, proposal in enumerate(data.get("proposals") or data if isinstance(data, list) else []):
            draft = to_promotion_draft(proposal)
            path = out / f"fragment_draft_{i:03d}.md"
            # write simple frontmatter + content
            fm = "\n".join(f"{k}: {json.dumps(v) if isinstance(v, (list, dict)) else v}" for k, v in draft.items() if k != "content")
            path.write_text(f"---\n{fm}\n---\n{draft.get('content', '')}\n", encoding="utf-8")
            written.append(str(path))
        print(json.dumps({"written": written}, indent=2))
        return 0

    if args.command == "board" and args.board_command == "query":
        from spws_planning import build_source_board

        board_data = build_source_board(args.text, config)
        print(json.dumps(board_data, indent=2))
        return 0

    if args.command == "plan" and args.plan_command == "create":
        from spws_planning import create_work_plan, save_plan

        plan = create_work_plan(brief=args.brief, form=args.form)
        if args.out:
            save_plan(plan, Path(args.out))
        print(json.dumps(plan, indent=2))
        return 0

    if args.command == "plan" and args.plan_command == "confirm":
        from spws_planning import confirm_work_plan, load_plan, save_plan

        plan = load_plan(Path(args.path))
        plan = confirm_work_plan(plan, confirmed=True)
        save_plan(plan, Path(args.path))
        print(json.dumps(plan, indent=2))
        return 0

    if args.command == "analyse":
        from spws_analysis import analyse_document

        path = Path(args.path)
        kind = "poem" if args.analyse_command == "poem" else "prose"
        result = analyse_document(path.read_text(encoding="utf-8"), kind=kind, config=config)
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "revise" and args.revise_command in {"poetry", "propose"}:
        from spws_planning import load_plan
        from spws_revision import propose_revision, revise_poetry

        plan = load_plan(Path(args.plan)) if args.plan else None
        if args.revise_command == "propose":
            result = propose_revision(
                Path(args.target), brief=args.brief, config=config, work_plan=plan
            )
        else:
            result = revise_poetry(
                Path(args.target), brief=args.brief, config=config, work_plan=plan
            )
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "revise" and args.revise_command == "decide":
        from spws_revision import decide_revision

        kind = RevisionDecisionKind(args.kind)
        export_dir = Path(args.export_dir) if args.export_dir else None
        result = decide_revision(
            config,
            Path(args.proposal),
            candidate_id=args.candidate,
            kind=kind,
            export_dir=export_dir,
        )
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "generate" and args.generate_command == "collage":
        from spws_generation import accept_collage, generate_collage
        from spws_planning import load_plan

        plan = load_plan(Path(args.plan)) if args.plan else None
        result = generate_collage(
            theme=args.theme, line_count=args.lines, config=config, work_plan=plan
        )
        if args.accept:
            result = {
                "proposal": result,
                "acceptance": accept_collage(result, config=config),
            }
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "assist" and args.assist_command == "reword":
        from spws_revision import assist_reword

        result = assist_reword(args.text, mode=args.mode, config=config)
        print(json.dumps(result, indent=2, default=str))
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
