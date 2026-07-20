"""
Semantic embedding generation using sentence-transformers.
"""

import logging
from typing import List, Dict, Optional
import json
from tqdm import tqdm

try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available - embeddings will be disabled")

from ..config import EMBEDDING_MODEL
from ..database import Lexico, Semantics, get_session

logger = logging.getLogger(__name__)


class SemanticEmbedder:
    """Generates semantic embeddings for words using sentence-transformers."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or EMBEDDING_MODEL

        if not TRANSFORMERS_AVAILABLE:
            logger.error("sentence-transformers not available")
            self.model = None
        else:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Model loaded successfully (dim={self.model.get_sentence_embedding_dimension()})")

    def build_semantic_text(self, word: str, definitions: List[str],
                           examples: List[str] = None,
                           labels: List[str] = None) -> str:
        """
        Build semantic text for embedding.

        Combines word, definitions, examples, and labels into a rich text representation.

        Args:
            word: The word
            definitions: List of definitions
            examples: List of example sentences
            labels: List of usage labels

        Returns:
            Semantic text string
        """
        parts = [word]

        # Add definitions
        if definitions:
            # Use top 3 definitions to avoid overly long text
            parts.extend(definitions[:3])

        # Add examples
        if examples:
            # Use top 2 examples
            parts.extend(examples[:2])

        # Add labels as context
        if labels:
            label_text = ' '.join(labels[:5])
            parts.append(label_text)

        return ' '.join(parts)

    def encode(self, text: str) -> Optional[List[float]]:
        """
        Encode text into embedding vector.

        Args:
            text: Text to encode

        Returns:
            Embedding vector as list of floats
        """
        if not self.model:
            return None

        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error encoding text: {e}")
            return None

    def encode_word(self, word: str, lexico_data: Dict) -> Optional[List[float]]:
        """
        Generate embedding for a word using its dictionary data.

        Args:
            word: The word
            lexico_data: Dictionary data

        Returns:
            Embedding vector
        """
        definitions = lexico_data.get('definitions', [])
        examples = lexico_data.get('examples', [])
        labels = lexico_data.get('labels_raw', [])

        if not definitions:
            logger.warning(f"No definitions available for '{word}'")
            return None

        semantic_text = self.build_semantic_text(word, definitions, examples, labels)
        embedding = self.encode(semantic_text)

        return embedding

    def embed_from_lexico(self, limit: Optional[int] = None, batch_size: int = 32):
        """
        Generate embeddings for words in lexico table.

        Args:
            limit: Maximum number of words to process
            batch_size: Batch size for encoding
        """
        if not self.model:
            logger.error("Cannot generate embeddings - model not available")
            return

        # Get words that need embeddings
        with get_session() as session:
            query = session.query(Lexico).outerjoin(
                Semantics, Lexico.lemma == Semantics.lemma
            ).filter(
                (Semantics.id.is_(None)) | (Semantics.embedding.is_(None))
            )

            if limit:
                query = query.limit(limit)

            lexico_entries = query.all()

        logger.info(f"Generating embeddings for {len(lexico_entries)} words...")

        # Process in batches for efficiency
        processed = 0
        failed = 0

        for i in tqdm(range(0, len(lexico_entries), batch_size), desc="Embedding words"):
            batch = lexico_entries[i:i + batch_size]

            # Build semantic texts
            semantic_texts = []
            words = []

            for entry in batch:
                lexico_data = {
                    'definitions': entry.definitions,
                    'examples': entry.examples,
                    'labels_raw': entry.labels_raw or []
                }

                if not lexico_data['definitions']:
                    continue

                semantic_text = self.build_semantic_text(
                    entry.lemma,
                    lexico_data['definitions'],
                    lexico_data['examples'],
                    lexico_data['labels_raw']
                )

                semantic_texts.append(semantic_text)
                words.append(entry.lemma)

            # Batch encode
            if semantic_texts:
                try:
                    embeddings = self.model.encode(semantic_texts, convert_to_numpy=True, batch_size=batch_size)

                    # Save to database
                    with get_session() as session:
                        for word, embedding in zip(words, embeddings):
                            embedding_list = embedding.tolist()

                            # Check if semantics entry exists
                            existing = session.query(Semantics).filter_by(lemma=word).first()

                            if existing:
                                existing.embedding = embedding_list
                            else:
                                semantics_entry = Semantics(
                                    lemma=word,
                                    embedding=embedding_list,
                                    domain_tags=[],
                                    register_tags=[],
                                    affect_tags=[],
                                    imagery_tags=[],
                                    theme_tags=[],
                                    synonyms=[],
                                    antonyms=[],
                                    hypernyms=[],
                                    hyponyms=[]
                                )
                                session.add(semantics_entry)

                    processed += len(words)

                except Exception as e:
                    logger.error(f"Error encoding batch: {e}")
                    failed += len(batch)

        logger.info(f"Embedding complete: {processed} processed, {failed} failed")

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity (-1 to 1)
        """
        if not embedding1 or not embedding2:
            return 0.0

        try:
            import numpy as np
            from numpy.linalg import norm

            v1 = np.array(embedding1)
            v2 = np.array(embedding2)

            return float(np.dot(v1, v2) / (norm(v1) * norm(v2)))

        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0

    def find_similar_words(self, word: str, top_k: int = 10) -> List[tuple]:
        """
        Find words similar to the given word.

        Args:
            word: The word to find similar words for
            top_k: Number of similar words to return

        Returns:
            List of (word, similarity) tuples
        """
        with get_session() as session:
            # Get embedding for target word
            target_semantics = session.query(Semantics).filter_by(lemma=word).first()

            if not target_semantics or not target_semantics.embedding:
                logger.warning(f"No embedding found for '{word}'")
                return []

            target_embedding = target_semantics.embedding

            # Get all other embeddings
            all_semantics = session.query(Semantics).filter(
                Semantics.lemma != word,
                Semantics.embedding.isnot(None)
            ).all()

        # Compute similarities
        similarities = []

        for sem in all_semantics:
            similarity = self.compute_similarity(target_embedding, sem.embedding)
            similarities.append((sem.lemma, similarity))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]


def main():
    """Command-line interface for embedding generation."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate semantic embeddings")
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of words to process'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for encoding'
    )
    parser.add_argument(
        '--model',
        type=str,
        help='Embedding model to use'
    )
    parser.add_argument(
        '--similar',
        type=str,
        help='Find similar words to this word'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    embedder = SemanticEmbedder(model_name=args.model)

    if args.similar:
        similar = embedder.find_similar_words(args.similar, top_k=10)
        print(f"\nWords similar to '{args.similar}':")
        for word, similarity in similar:
            print(f"  {word}: {similarity:.4f}")
    else:
        embedder.embed_from_lexico(limit=args.limit, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
