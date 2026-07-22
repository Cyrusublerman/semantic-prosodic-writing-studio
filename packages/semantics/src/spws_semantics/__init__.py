"""SPWS meaning gauge: unitise, encode, index, similar."""

from .encode import EmbeddingService, TaggingService
from .index import MeaningStore
from .service import MeaningGauge
from .similarity import hybrid_score, similar
from .unitise import unitise_text

__all__ = [
    "EmbeddingService",
    "MeaningGauge",
    "MeaningStore",
    "TaggingService",
    "hybrid_score",
    "similar",
    "unitise_text",
]

__version__ = "0.1.0"
