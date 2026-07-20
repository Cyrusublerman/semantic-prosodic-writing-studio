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


class ThemeSelector:
    """Selects themes and motifs from concept graph."""

    def __init__(self):
        self.similarity_threshold = 0.6

    def select_theme_concepts(self, spec: GenerationSpec) -> List[int]:
        """
        Select concept nodes matching the theme and affect profile.

        Args:
            spec: Generation specification

        Returns:
            List of concept node IDs
        """
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

        # Get word pools for each motif
        word_pools = {}
        for motif_id in motifs:
            words = self.get_words_for_concept(motif_id, spec, limit=50)
            word_pools[motif_id] = words
            logger.info(f"Motif {motif_id}: {len(words)} words")

        # Select metaphor bridges
        bridges = self.select_metaphor_bridges(theme_concepts + motifs, max_bridges=3)
        logger.info(f"Selected {len(bridges)} metaphor bridges")

        return {
            'theme_concepts': theme_concepts,
            'motifs': motifs,
            'word_pools': word_pools,
            'metaphor_bridges': bridges,
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
    print(f"\nWord pools:")
    for motif_id, words in palette['word_pools'].items():
        print(f"  Motif {motif_id}: {len(words)} words")
        if words:
            print(f"    Sample: {', '.join(words[:10])}")


if __name__ == "__main__":
    main()
