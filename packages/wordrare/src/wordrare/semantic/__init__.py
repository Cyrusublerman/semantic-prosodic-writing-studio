"""
Semantic module for embeddings, tagging, and concept graphs.
"""

from .lexical_structure import LexicalStructure
from .embedder import SemanticEmbedder
from .tagger import SemanticTagger
from .concept_graph import ConceptGraphBuilder
from .word_record_builder import WordRecordBuilder

__all__ = [
    "LexicalStructure",
    "SemanticEmbedder",
    "SemanticTagger",
    "ConceptGraphBuilder",
    "WordRecordBuilder"
]
