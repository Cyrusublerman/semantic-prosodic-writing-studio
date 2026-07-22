"""
Theme and motif selection from concept graph.

Queries the concept graph to select themes, motifs, and semantic clusters
for poem generation.
"""

import logging
import random
from typing import List, Optional, Dict, Tuple
import numpy as np

from ..database import ConceptNode, ConceptEdge, Semantics, WordRecord, get_session
from .generation_spec import GenerationSpec

logger = logging.getLogger(__name__)

# Deterministic seed lemmas when the concept graph yields no pools.
THEME_SEED_FALLBACKS: Dict[str, List[str]] = {
    "nature": [
        # Prefer 1-syl lemmas in multi-member rhyme cohorts
        "leaf", "stone", "wind", "bloom", "moss", "root", "sky", "oak", "dew", "glade",
    ],
    "death": [
        "ash", "dust", "grave", "bone", "veil", "night", "tomb", "shade", "dusk", "cold",
    ],
    "time": [
        "hour", "dawn", "dusk", "year", "tide", "age", "day", "night", "moon", "sun",
    ],
}

# Contrast lemmas for volta_pool when no second motif / CONTRASTS_WITH edges exist.
VOLTA_SEED_FALLBACKS: Dict[str, List[str]] = {
    "nature": ["steel", "flame", "void", "silence", "iron", "smoke"],
    "death": ["bloom", "dawn", "breath", "spring", "pulse", "light"],
    "time": ["stillness", "stone", "eternity", "pause", "freeze", "void"],
}


class ThemeSelector:
    """Selects themes and motifs from concept graph."""

    _MIN_GRAPH = 3

    def __init__(self):
        self.similarity_threshold = 0.6

    def ensure_seed_concepts(self) -> None:
        """Insert nature/death/time concept nodes when the graph is too small."""
        with get_session() as session:
            n = session.query(ConceptNode).filter_by(node_type="concept").count()
            if n >= self._MIN_GRAPH:
                return
            for label in ("nature", "death", "time"):
                existing = (
                    session.query(ConceptNode).filter_by(label=label).first()
                )
                if existing:
                    continue
                session.add(
                    ConceptNode(label=label, node_type="concept", ontology_refs={})
                )
            logger.info("Seeded nature/death/time concept nodes (graph was %s)", n)

    def select_theme_concepts(self, spec: GenerationSpec) -> List[int]:
        """
        Select concept nodes matching the theme and affect profile.

        Args:
            spec: Generation specification

        Returns:
            List of concept node IDs
        """
        self.ensure_seed_concepts()
        with get_session() as session:
            # Start with all concepts
            query = session.query(ConceptNode).filter_by(node_type='concept')

            # Filter by theme if specified
            if spec.theme:
                # Find concepts whose label contains the theme
                matching_concepts = []

                for concept in query.all():
                    label_lower = concept.label.lower()

                    if spec.theme.lower() in label_lower:
                        matching_concepts.append(concept.id)

                if matching_concepts:
                    return matching_concepts

            # Fallback: select random concepts
            all_concepts = query.all()

            if not all_concepts:
                logger.warning("No concepts found in database")
                return []

            # Select 3-5 random concepts
            n_concepts = min(random.randint(3, 5), len(all_concepts))
            selected = random.sample(all_concepts, n_concepts)

            return [c.id for c in selected]

    def select_motif_nodes(self, theme_concept_ids: List[int],
                          n_motifs: int = 3) -> List[int]:
        """
        Select motif nodes related to theme concepts.

        Args:
            theme_concept_ids: IDs of theme concepts
            n_motifs: Number of motifs to select

        Returns:
            List of concept/motif node IDs
        """
        if not theme_concept_ids:
            return []

        with get_session() as session:
            # Find associated concepts via edges
            associated_ids = set(theme_concept_ids)

            for concept_id in theme_concept_ids:
                # Get outgoing edges
                edges = session.query(ConceptEdge).filter_by(
                    source_id=concept_id
                ).filter(
                    ConceptEdge.edge_type == 'ASSOCIATES_WITH'
                ).all()

                for edge in edges[:5]:  # Limit to top 5
                    associated_ids.add(edge.target_id)

            # Select n_motifs from associated concepts
            associated_list = list(associated_ids)
            n_select = min(n_motifs, len(associated_list))

            return random.sample(associated_list, n_select)

    def _passes_tag_filters(self, record: WordRecord, spec: GenerationSpec) -> bool:
        """Apply domain/imagery filters when those tags exist on the WordRecord."""
        if spec.domain_tags and record.domain_tags:
            if not any(tag in record.domain_tags for tag in spec.domain_tags):
                return False
        if spec.imagery_tags and record.imagery_tags:
            if not any(tag in record.imagery_tags for tag in spec.imagery_tags):
                return False
        return True

    def get_words_for_concept(self, concept_id: int,
                             spec: GenerationSpec,
                             limit: int = 50) -> List[str]:
        """
        Get words associated with a concept.

        Args:
            concept_id: Concept node ID
            spec: Generation specification
            limit: Max words to return

        Returns:
            List of word lemmas
        """
        with get_session() as session:
            concept = session.query(ConceptNode).filter_by(id=concept_id).first()

            if not concept or not concept.centroid_embedding:
                return []

            # Get words with similar embeddings
            centroid = np.array(concept.centroid_embedding)

            # Query word records with embeddings
            word_records = session.query(WordRecord).filter(
                WordRecord.embedding.isnot(None)
            ).all()

            if not word_records:
                return []

            # Compute similarities
            similarities = []

            for record in word_records:
                if not record.embedding:
                    continue

                # Check rarity constraints
                if record.rarity_score is not None:
                    if record.rarity_score < spec.min_rarity or record.rarity_score > spec.max_rarity:
                        continue

                if not self._passes_tag_filters(record, spec):
                    continue

                # Compute similarity
                word_emb = np.array(record.embedding)
                similarity = float(np.dot(centroid, word_emb) /
                                 (np.linalg.norm(centroid) * np.linalg.norm(word_emb)))

                similarities.append((record.lemma, similarity))

            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)

            # Return top words
            return [word for word, sim in similarities[:limit]]

    def select_metaphor_bridges(self, concept_ids: List[int],
                                max_bridges: int = 3) -> List[Tuple[int, int]]:
        """
        Select metaphor bridge edges between concepts.

        Args:
            concept_ids: Concept node IDs to consider
            max_bridges: Maximum number of bridges

        Returns:
            List of (source_id, target_id) tuples
        """
        if len(concept_ids) < 2:
            return []

        with get_session() as session:
            bridges = []

            # Find METAPHOR_BRIDGE edges between concepts
            for source_id in concept_ids:
                edges = session.query(ConceptEdge).filter_by(
                    source_id=source_id,
                    edge_type='METAPHOR_BRIDGE'
                ).filter(
                    ConceptEdge.target_id.in_(concept_ids)
                ).all()

                for edge in edges:
                    bridges.append((edge.source_id, edge.target_id, edge.weight))

            # Sort by weight and select top bridges
            bridges.sort(key=lambda x: x[2], reverse=True)

            return [(src, tgt) for src, tgt, weight in bridges[:max_bridges]]

    @staticmethod
    def _dedupe_preserve(lemmas: List[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for lemma in lemmas:
            key = lemma.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(lemma)
        return out

    def _theme_seed_fallback(self, spec: GenerationSpec) -> List[str]:
        theme_key = (spec.theme or "").lower().strip()
        if theme_key in THEME_SEED_FALLBACKS:
            return list(THEME_SEED_FALLBACKS[theme_key])
        # Generic nature-adjacent seeds when theme unknown / empty graph
        return list(THEME_SEED_FALLBACKS["nature"])

    def _volta_seed_fallback(self, spec: GenerationSpec) -> List[str]:
        theme_key = (spec.theme or "").lower().strip()
        if theme_key in VOLTA_SEED_FALLBACKS:
            return list(VOLTA_SEED_FALLBACKS[theme_key])
        return list(VOLTA_SEED_FALLBACKS["nature"])

    def _build_volta_pool(
        self,
        spec: GenerationSpec,
        motifs: List[int],
        motif_word_map: Dict[int, List[str]],
        theme_concepts: List[int],
    ) -> List[str]:
        """Alternate lemmas for volta contrast."""
        # Prefer second motif's lemmas
        if len(motifs) >= 2:
            second = motif_word_map.get(motifs[1]) or []
            if second:
                return self._dedupe_preserve(list(second))

        # CONTRASTS_WITH edges from theme/motifs
        contrasts = self.get_contrast_concepts(theme_concepts + motifs)
        if contrasts:
            contrast_words: List[str] = []
            for cid in contrasts[:3]:
                contrast_words.extend(self.get_words_for_concept(cid, spec, limit=20))
            contrast_words = self._dedupe_preserve(contrast_words)
            if contrast_words:
                return contrast_words

        return self._volta_seed_fallback(spec)

    def build_semantic_palette(self, spec: GenerationSpec) -> Dict:
        """
        Build a semantic palette for generation.

        Args:
            spec: Generation specification

        Returns:
            Dictionary with theme concepts, motifs, word pools, and bridges
        """
        logger.info(f"Building semantic palette for theme: {spec.theme}")

        # Select theme concepts
        theme_concepts = self.select_theme_concepts(spec)
        logger.info(f"Selected {len(theme_concepts)} theme concepts")

        # Select motifs
        motifs = self.select_motif_nodes(theme_concepts, n_motifs=3)
        logger.info(f"Selected {len(motifs)} motif nodes")

        # Per-motif pools (internal), then flatten to lemma list for word_pools
        motif_word_map: Dict[int, List[str]] = {}
        flat_lemmas: List[str] = []

        for motif_id in motifs:
            words = self.get_words_for_concept(motif_id, spec, limit=50)
            motif_word_map[motif_id] = words
            flat_lemmas.extend(words)
            logger.info(f"Motif {motif_id}: {len(words)} words")

        # Include theme-concept lemmas as well
        for concept_id in theme_concepts:
            if concept_id in motif_word_map:
                continue
            words = self.get_words_for_concept(concept_id, spec, limit=30)
            flat_lemmas.extend(words)

        # Select metaphor bridges
        bridges = self.select_metaphor_bridges(theme_concepts + motifs, max_bridges=3)
        logger.info(f"Selected {len(bridges)} metaphor bridges")

        # cross_domain: fold metaphor-bridge lemmas into the pool
        if spec.cross_domain and bridges:
            bridge_ids = set()
            for src, tgt in bridges:
                bridge_ids.add(src)
                bridge_ids.add(tgt)
            for cid in bridge_ids:
                flat_lemmas.extend(self.get_words_for_concept(cid, spec, limit=20))

        word_pools = self._dedupe_preserve(flat_lemmas)

        # Deterministic seed fallback when concept graph / embeddings yield nothing
        if not word_pools:
            word_pools = self._theme_seed_fallback(spec)
            logger.info(
                "Using theme seed fallback (%s): %s lemmas",
                spec.theme,
                len(word_pools),
            )

        volta_pool = self._build_volta_pool(
            spec, motifs, motif_word_map, theme_concepts
        )
        # Ensure volta lemmas differ from primary pool when possible
        primary = {w.lower() for w in word_pools}
        volta_distinct = [w for w in volta_pool if w.lower() not in primary]
        if volta_distinct:
            volta_pool = volta_distinct
        elif not volta_pool:
            volta_pool = self._volta_seed_fallback(spec)

        # Average motif/theme centroids for embedding-aware ranking
        motif_centroid = None
        node_ids = motifs or theme_concepts
        vectors = []
        if node_ids:
            with get_session() as session:
                for nid in node_ids:
                    node = session.query(ConceptNode).filter_by(id=nid).first()
                    if node and node.centroid_embedding:
                        vectors.append(list(node.centroid_embedding))
        if vectors:
            dim = len(vectors[0])
            acc = [0.0] * dim
            usable = 0
            for vec in vectors:
                if len(vec) != dim:
                    continue
                usable += 1
                for i, v in enumerate(vec):
                    acc[i] += float(v)
            if usable:
                motif_centroid = [c / usable for c in acc]

        # Engine stub compat: motif_words / theme_words alias the same lemma list
        return {
            'theme_concepts': theme_concepts,
            'motifs': motifs,
            'word_pools': word_pools,
            'motif_words': word_pools,
            'theme_words': word_pools,
            'volta_pool': volta_pool,
            'metaphor_bridges': bridges,
            'motif_centroid': motif_centroid,
            'motif_density': spec.motif_density,
            'spec': spec
        }

    def get_contrast_concepts(self, concept_ids: List[int]) -> List[int]:
        """
        Get concepts that contrast with given concepts.

        Args:
            concept_ids: Base concept IDs

        Returns:
            List of contrasting concept IDs
        """
        with get_session() as session:
            contrasts = set()

            for concept_id in concept_ids:
                edges = session.query(ConceptEdge).filter_by(
                    source_id=concept_id,
                    edge_type='CONTRASTS_WITH'
                ).all()

                for edge in edges[:3]:  # Limit to top 3 contrasts
                    contrasts.add(edge.target_id)

            return list(contrasts)


def main():
    """CLI for theme selection testing."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Theme selection utilities")
    parser.add_argument(
        '--theme',
        type=str,
        help='Theme to select concepts for'
    )
    parser.add_argument(
        '--rarity',
        type=float,
        default=0.5,
        help='Rarity bias'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    from .generation_spec import create_default_spec

    spec = create_default_spec(theme=args.theme, rarity=args.rarity)

    selector = ThemeSelector()
    palette = selector.build_semantic_palette(spec)

    print(f"\nSemantic Palette:")
    print(f"  Theme concepts: {palette['theme_concepts']}")
    print(f"  Motifs: {palette['motifs']}")
    print(f"  Metaphor bridges: {palette['metaphor_bridges']}")
    print(f"  Motif density: {palette['motif_density']}")
    print(f"\nWord pools ({len(palette['word_pools'])} lemmas):")
    if palette['word_pools']:
        print(f"  Sample: {', '.join(palette['word_pools'][:10])}")
    print(f"Volta pool ({len(palette['volta_pool'])} lemmas):")
    if palette['volta_pool']:
        print(f"  Sample: {', '.join(palette['volta_pool'][:10])}")


if __name__ == "__main__":
    main()
