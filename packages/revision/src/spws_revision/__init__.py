"""Deterministic revision candidate generation and meaning-aware assist."""

from .candidates import RevisionCandidate, apply_decision, generate_candidates
from .decisions import record_decision
from .evaluation import ALL_CRITERIA, build_evaluation_bundle
from .export_pack import build_export_pack
from .rich_revise import (
    RestrictedSourceError,
    accept_candidate_to_manuscript,
    assist_reword,
    filter_restricted_source_hits,
    revise_poetry,
)
from .session import decide_revision, propose_revision

__all__ = [
    "ALL_CRITERIA",
    "RestrictedSourceError",
    "RevisionCandidate",
    "accept_candidate_to_manuscript",
    "apply_decision",
    "assist_reword",
    "build_evaluation_bundle",
    "build_export_pack",
    "decide_revision",
    "filter_restricted_source_hits",
    "generate_candidates",
    "propose_revision",
    "record_decision",
    "revise_poetry",
]
