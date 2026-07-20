"""
Concept graph builder - clustering and relationship mapping.

Creates concept nodes from embedding clusters and builds edges for associations,
contrasts, and metaphor bridges.
"""

import logging
from typing import List, Dict, Optional, Tuple
import json
from tqdm import tqdm

try:
    import numpy as np
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available - concept graph building will be limited")

from ..database import Semantics, ConceptNode, ConceptEdge, get_session

logger = logging.getLogger(__name__)


class ConceptGraphBuilder:
    """Builds concept graph from semantic embeddings."""

    def __init__(self):
        self.similarity_threshold = 0.6  # For ASSOCIATES_WITH edges
        self.contrast_threshold = -0.3   # For CONTRASTS_WITH edges (negative similarity)
        self.metaphor_threshold = 0.4    # For METAPHOR_BRIDGE (cross-domain similarity)

    def cluster_embeddings(self, n_clusters: int = 50, method: str = 'kmeans') -> Dict[int, List[str]]:
        """
        Cluster word embeddings into concept groups.

        Args:
            n_clusters: Number of clusters to create
            method: Clustering method ('kmeans' or 'dbscan')

        Returns:
            Dictionary mapping cluster_id to list of words
        """
        if not SKLEARN_AVAILABLE:
            logger.error("scikit-learn not available")
            return {}

        # Load all embeddings
        with get_session() as session:
            all_semantics = session.query(Semantics).filter(
                Semantics.embedding.isnot(None)
            ).all()

        if not all_semantics:
            logger.warning("No embeddings found")
            return {}

        logger.info(f"Clustering {len(all_semantics)} words...")

        # Convert to numpy array
        embeddings = np.array([sem.embedding for sem in all_semantics])
        words = [sem.lemma for sem in all_semantics]

        # Cluster
        if method == 'kmeans':
            clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = clusterer.fit_predict(embeddings)
        elif method == 'dbscan':
            clusterer = DBSCAN(eps=0.3, min_samples=3, metric='cosine')
            labels = clusterer.fit_predict(embeddings)
        else:
            raise ValueError(f"Unknown clustering method: {method}")

        # Group words by cluster
        clusters = {}
        for word, label in zip(words, labels):
            if label == -1:  # Noise in DBSCAN
                continue

            if label not in clusters:
                clusters[label] = []

            clusters[label].append(word)

        logger.info(f"Created {len(clusters)} clusters")

        return clusters

    def compute_cluster_centroid(self, words: List[str]) -> Optional[List[float]]:
        """
        Compute centroid embedding for a cluster of words.

        Args:
            words: List of words in the cluster

        Returns:
            Centroid embedding vector
        """
        if not SKLEARN_AVAILABLE:
            return None

        with get_session() as session:
            embeddings = []

            for word in words:
                sem = session.query(Semantics).filter_by(lemma=word).first()
                if sem and sem.embedding:
                    embeddings.append(sem.embedding)

        if not embeddings:
            return None

        # Compute mean
        centroid = np.mean(np.array(embeddings), axis=0)

        return centroid.tolist()

    def create_concept_nodes(self, clusters: Dict[int, List[str]]) -> Dict[int, int]:
        """
        Create concept nodes from clusters.

        Args:
            clusters: Dictionary mapping cluster_id to words

        Returns:
            Dictionary mapping cluster_id to concept_node.id
        """
        cluster_to_node = {}

        with get_session() as session:
            for cluster_id, words in tqdm(clusters.items(), desc="Creating concept nodes"):
                # Compute centroid
                centroid = self.compute_cluster_centroid(words)

                # Generate label (use most common domain tag or first few words)
                domain_tags = []
                for word in words:
                    sem = session.query(Semantics).filter_by(lemma=word).first()
                    if sem and sem.domain_tags:
                        domain_tags.extend(sem.domain_tags)

                if domain_tags:
                    # Use most common domain tag
                    from collections import Counter
                    label = Counter(domain_tags).most_common(1)[0][0]
                else:
                    # Use first few words as label
                    label = f"concept_{cluster_id}_{words[0]}"

                # Create concept node
                concept_node = ConceptNode(
                    label=label,
                    node_type='concept',
                    centroid_embedding=centroid,
                    ontology_refs={'cluster_id': cluster_id, 'size': len(words)},
                    concept_ids=None
                )

                session.add(concept_node)
                session.flush()  # Get the ID

                cluster_to_node[cluster_id] = concept_node.id

        logger.info(f"Created {len(cluster_to_node)} concept nodes")

        return cluster_to_node

    def create_association_edges(self, threshold: float = None):
        """
        Create ASSOCIATES_WITH edges between similar concepts.

        Args:
            threshold: Similarity threshold (uses default if None)
        """
        if not SKLEARN_AVAILABLE:
            logger.error("scikit-learn not available")
            return

        threshold = threshold or self.similarity_threshold

        with get_session() as session:
            # Get all concept nodes
            nodes = session.query(ConceptNode).filter_by(node_type='concept').all()

            if len(nodes) < 2:
                logger.warning("Not enough concept nodes for edges")
                return

            logger.info(f"Creating association edges for {len(nodes)} nodes...")

            # Compute pairwise similarities
            centroids = np.array([node.centroid_embedding for node in nodes])
            similarities = cosine_similarity(centroids)

            edges_created = 0

            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    similarity = similarities[i, j]

                    if similarity >= threshold:
                        # Create edge
                        edge = ConceptEdge(
                            source_id=nodes[i].id,
                            target_id=nodes[j].id,
                            edge_type='ASSOCIATES_WITH',
                            weight=float(similarity)
                        )
                        session.add(edge)
                        edges_created += 1

            session.commit()

        logger.info(f"Created {edges_created} ASSOCIATES_WITH edges")

    def create_contrast_edges(self, threshold: float = None):
        """
        Create CONTRASTS_WITH edges between dissimilar concepts.

        Args:
            threshold: Dissimilarity threshold (uses default if None)
        """
        if not SKLEARN_AVAILABLE:
            logger.error("scikit-learn not available")
            return

        threshold = threshold or self.contrast_threshold

        with get_session() as session:
            nodes = session.query(ConceptNode).filter_by(node_type='concept').all()

            if len(nodes) < 2:
                return

            logger.info(f"Creating contrast edges...")

            centroids = np.array([node.centroid_embedding for node in nodes])
            similarities = cosine_similarity(centroids)

            edges_created = 0

            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    similarity = similarities[i, j]

                    if similarity <= threshold:
                        # Create contrast edge
                        edge = ConceptEdge(
                            source_id=nodes[i].id,
                            target_id=nodes[j].id,
                            edge_type='CONTRASTS_WITH',
                            weight=float(-similarity)  # Store as positive weight
                        )
                        session.add(edge)
                        edges_created += 1

            session.commit()

        logger.info(f"Created {edges_created} CONTRASTS_WITH edges")

    def create_metaphor_bridges(self, threshold: float = None):
        """
        Create METAPHOR_BRIDGE edges between concepts from different domains
        that have moderate similarity (potential metaphor connections).

        Args:
            threshold: Similarity threshold for metaphor (uses default if None)
        """
        if not SKLEARN_AVAILABLE:
            logger.error("scikit-learn not available")
            return

        threshold = threshold or self.metaphor_threshold

        with get_session() as session:
            nodes = session.query(ConceptNode).filter_by(node_type='concept').all()

            logger.info(f"Creating metaphor bridges...")

            # Group nodes by domain (from label)
            domain_nodes = {}
            for node in nodes:
                domain = node.label.split('_')[0] if '_' in node.label else 'general'
                if domain not in domain_nodes:
                    domain_nodes[domain] = []
                domain_nodes[domain].append(node)

            centroids = np.array([node.centroid_embedding for node in nodes])
            similarities = cosine_similarity(centroids)

            node_to_idx = {node.id: i for i, node in enumerate(nodes)}

            edges_created = 0

            # Create bridges between different domains
            for domain1, nodes1 in domain_nodes.items():
                for domain2, nodes2 in domain_nodes.items():
                    if domain1 >= domain2:  # Avoid duplicates
                        continue

                    for node1 in nodes1:
                        for node2 in nodes2:
                            idx1 = node_to_idx[node1.id]
                            idx2 = node_to_idx[node2.id]

                            similarity = similarities[idx1, idx2]

                            # Metaphor bridges: moderate similarity between different domains
                            if threshold <= similarity < self.similarity_threshold:
                                edge = ConceptEdge(
                                    source_id=node1.id,
                                    target_id=node2.id,
                                    edge_type='METAPHOR_BRIDGE',
                                    weight=float(similarity)
                                )
                                session.add(edge)
                                edges_created += 1

            session.commit()

        logger.info(f"Created {edges_created} METAPHOR_BRIDGE edges")

    def build_graph(self, n_clusters: int = 50):
        """
        Build complete concept graph.

        Args:
            n_clusters: Number of concept clusters to create
        """
        logger.info("Building concept graph...")

        # Cluster embeddings
        clusters = self.cluster_embeddings(n_clusters=n_clusters)

        if not clusters:
            logger.error("Failed to create clusters")
            return

        # Create concept nodes
        cluster_to_node = self.create_concept_nodes(clusters)

        # Create edges
        self.create_association_edges()
        self.create_contrast_edges()
        self.create_metaphor_bridges()

        logger.info("Concept graph building complete!")

    def get_graph_statistics(self) -> Dict:
        """
        Get statistics about the concept graph.

        Returns:
            Dictionary of graph statistics
        """
        with get_session() as session:
            node_count = session.query(ConceptNode).count()

            edges = session.query(ConceptEdge).all()

            edge_types = {}
            for edge in edges:
                edge_types[edge.edge_type] = edge_types.get(edge.edge_type, 0) + 1

        return {
            'nodes': node_count,
            'total_edges': len(edges),
            'edge_types': edge_types
        }


def main():
    """Command-line interface for concept graph building."""
    import argparse

    parser = argparse.ArgumentParser(description="Build concept graph")
    parser.add_argument(
        '--clusters',
        type=int,
        default=50,
        help='Number of clusters to create'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show graph statistics'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    builder = ConceptGraphBuilder()

    if args.stats:
        stats = builder.get_graph_statistics()
        print("\nConcept Graph Statistics:")
        print(json.dumps(stats, indent=2))
    else:
        builder.build_graph(n_clusters=args.clusters)


if __name__ == "__main__":
    main()
