"""
Database models for WordRare system.
"""

from sqlalchemy import (
    Column, Integer, String, Float, JSON, Text, ForeignKey,
    Table, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class RareLexicon(Base):
    """Rare words from Phrontistery and other sources."""
    __tablename__ = "rare_lexicon"

    id = Column(Integer, primary_key=True)
    lemma = Column(String(255), unique=True, nullable=False, index=True)
    phrontistery_definition = Column(Text)
    source_url = Column(String(512))
    phrontistery_list_id = Column(String(128))
    created_at = Column(String(32), default=lambda: datetime.now().isoformat())

    __table_args__ = (
        Index('idx_rare_lexicon_lemma', 'lemma'),
    )


class Lexico(Base):
    """Lexicographic data from dictionary APIs."""
    __tablename__ = "lexico"

    id = Column(Integer, primary_key=True)
    lemma = Column(String(255), nullable=False, index=True)
    definitions = Column(JSON)  # List of definition strings
    examples = Column(JSON)  # List of example sentences
    labels_raw = Column(JSON)  # List of usage labels
    etymology_raw = Column(Text)
    pos_raw = Column(JSON)  # List of part-of-speech tags
    source = Column(String(64))  # API source name
    created_at = Column(String(32), default=lambda: datetime.now().isoformat())

    __table_args__ = (
        Index('idx_lexico_lemma', 'lemma'),
    )


class Phonetics(Base):
    """Phonetic and IPA data."""
    __tablename__ = "phonetics"

    id = Column(Integer, primary_key=True)
    lemma = Column(String(255), nullable=False, index=True)
    ipa_us_cmu = Column(String(255))
    ipa_dict_uk = Column(String(255))
    ipa_dict_us = Column(String(255))
    stress_pattern = Column(String(64))  # e.g., "010"
    syllable_count = Column(Integer)
    rhyme_key = Column(String(128), index=True)  # For rhyme matching
    onset = Column(String(128))  # For alliteration
    nucleus = Column(String(128))  # For assonance
    coda = Column(String(128))  # For consonance
    created_at = Column(String(32), default=lambda: datetime.now().isoformat())

    __table_args__ = (
        Index('idx_phonetics_lemma', 'lemma'),
        Index('idx_phonetics_rhyme_key', 'rhyme_key'),
    )


class FreqProfile(Base):
    """Frequency and rarity data."""
    __tablename__ = "freq_profile"

    id = Column(Integer, primary_key=True)
    lemma = Column(String(255), unique=True, nullable=False, index=True)
    freq_written = Column(Float, default=0.0)
    freq_spoken = Column(Float, default=0.0)
    freq_historical = Column(JSON)  # Time-series data
    dispersion_index = Column(Float)
    rarity_score = Column(Float, index=True)
    temporal_profile = Column(String(64))  # e.g., "archaic", "modern", "stable"
    created_at = Column(String(32), default=lambda: datetime.now().isoformat())

    __table_args__ = (
        Index('idx_freq_profile_rarity', 'rarity_score'),
    )


class Semantics(Base):
    """Semantic embeddings and tags."""
    __tablename__ = "semantics"

    id = Column(Integer, primary_key=True)
    lemma = Column(String(255), unique=True, nullable=False, index=True)
    embedding = Column(JSON)  # Vector representation
    domain_tags = Column(JSON)  # e.g., ["medical", "nautical"]
    register_tags = Column(JSON)  # e.g., ["formal", "archaic"]
    affect_tags = Column(JSON)  # e.g., ["melancholic", "joyful"]
    imagery_tags = Column(JSON)  # e.g., ["visual", "auditory"]
    theme_tags = Column(JSON)  # e.g., ["nature", "death"]
    synonyms = Column(JSON)
    antonyms = Column(JSON)
    hypernyms = Column(JSON)
    hyponyms = Column(JSON)
    created_at = Column(String(32), default=lambda: datetime.now().isoformat())


class ConceptNode(Base):
    """Nodes in the concept graph."""
    __tablename__ = "concept_node"

    id = Column(Integer, primary_key=True)
    label = Column(String(255), unique=True, nullable=False)
    node_type = Column(String(32))  # "concept" or "motif"
    centroid_embedding = Column(JSON)  # Average of member embeddings
    ontology_refs = Column(JSON)  # References to external ontologies
    concept_ids = Column(JSON)  # For motif nodes: list of concept IDs
    created_at = Column(String(32), default=lambda: datetime.now().isoformat())


class ConceptEdge(Base):
    """Edges in the concept graph."""
    __tablename__ = "concept_edge"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("concept_node.id"), nullable=False)
    target_id = Column(Integer, ForeignKey("concept_node.id"), nullable=False)
    edge_type = Column(String(64))  # "ASSOCIATES_WITH", "CONTRASTS_WITH", "METAPHOR_BRIDGE", "PART_OF"
    weight = Column(Float, default=1.0)
    created_at = Column(String(32), default=lambda: datetime.now().isoformat())

    source = relationship("ConceptNode", foreign_keys=[source_id])
    target = relationship("ConceptNode", foreign_keys=[target_id])

    __table_args__ = (
        Index('idx_concept_edge_source', 'source_id'),
        Index('idx_concept_edge_target', 'target_id'),
    )


class PoeticForm(Base):
    """Poetic form specifications."""
    __tablename__ = "poetic_forms"

    id = Column(Integer, primary_key=True)
    form_id = Column(String(64), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    stanza_specs = Column(JSON)  # List of stanza specifications
    rhyme_pattern = Column(String(128))  # e.g., "ABAB CDCD EFEF GG"
    meter_pattern = Column(String(128))  # e.g., "iambic pentameter"
    special_rules = Column(JSON)  # Volta, refrains, etc.
    device_profile_defaults = Column(JSON)
    description = Column(Text)
    created_at = Column(String(32), default=lambda: datetime.now().isoformat())


class WordRecord(Base):
    """Unified WORD_RECORD combining all data sources."""
    __tablename__ = "word_record"

    id = Column(Integer, primary_key=True)
    lemma = Column(String(255), unique=True, nullable=False, index=True)
    pos_primary = Column(String(32))
    pos_all = Column(JSON)

    # Phonetics
    ipa_us = Column(String(255))
    ipa_uk = Column(String(255))
    stress_pattern = Column(String(64))
    syllable_count = Column(Integer)
    rhyme_key = Column(String(128), index=True)

    # Frequency/Rarity
    rarity_score = Column(Float, index=True)
    temporal_profile = Column(String(64))

    # Semantics
    domain_tags = Column(JSON)
    register_tags = Column(JSON)
    affect_tags = Column(JSON)
    imagery_tags = Column(JSON)
    embedding = Column(JSON)
    concept_links = Column(JSON)  # List of concept node IDs

    # Definitions and examples
    definitions = Column(JSON)
    examples = Column(JSON)

    created_at = Column(String(32), default=lambda: datetime.now().isoformat())
    updated_at = Column(String(32), default=lambda: datetime.now().isoformat())

    __table_args__ = (
        Index('idx_word_record_rarity', 'rarity_score'),
        Index('idx_word_record_rhyme', 'rhyme_key'),
        Index('idx_word_record_syllables', 'syllable_count'),
    )


class GenerationRun(Base):
    """Logs of poem generation runs."""
    __tablename__ = "generation_runs"

    id = Column(Integer, primary_key=True)
    run_id = Column(String(64), unique=True, nullable=False)
    input_spec = Column(JSON)
    form_id = Column(String(64))
    theme = Column(String(128))
    parameter_snapshot = Column(JSON)
    poem_text = Column(Text)
    debug_annotations = Column(JSON)
    metrics = Column(JSON)
    created_at = Column(String(32), default=lambda: datetime.now().isoformat())

    __table_args__ = (
        Index('idx_generation_runs_form', 'form_id'),
        Index('idx_generation_runs_theme', 'theme'),
    )
