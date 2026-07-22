"""Analysis fan-out components (D002 / D016)."""

from .lexical import analyse_lexical
from .prosodic import analyse_prosodic
from .provenance import analyse_provenance
from .repetition_motif import analyse_repetition_motif
from .semantic import analyse_semantic
from .structural import analyse_structural

COMPONENT_ANALYSERS = {
    "lexical": analyse_lexical,
    "prosodic": analyse_prosodic,
    "semantic": analyse_semantic,
    "structural": analyse_structural,
    "repetition_motif": analyse_repetition_motif,
    "provenance": analyse_provenance,
}

__all__ = [
    "COMPONENT_ANALYSERS",
    "analyse_lexical",
    "analyse_prosodic",
    "analyse_provenance",
    "analyse_repetition_motif",
    "analyse_semantic",
    "analyse_structural",
]
