"""SPWS preprocessing: normalisation and fragment catalogue proposals."""

from .catalogue import propose_fragments, to_promotion_draft
from .normalise import build_normalised_source, normalise_text
from .review_queue import list_pending, save_review_bundle

__all__ = [
    "build_normalised_source",
    "list_pending",
    "normalise_text",
    "propose_fragments",
    "save_review_bundle",
    "to_promotion_draft",
]

__version__ = "0.1.0"
