"""
Lexical structure parsing and normalization.

Parses dictionary data into structured sense lists, usage notes, and labels.
Optionally integrates WordNet for lexical relations.
"""

import re
from typing import Dict, List, Optional, Set
import logging
from tqdm import tqdm

try:
    from nltk.corpus import wordnet as wn
    WORDNET_AVAILABLE = True
except ImportError:
    WORDNET_AVAILABLE = False
    logging.warning("WordNet not available - lexical relations will be limited")

from ..database import Lexico, Semantics, get_session

logger = logging.getLogger(__name__)


class LexicalStructure:
    """Parses and structures lexical information."""

    def __init__(self):
        self.label_normalizations = {
            # Register
            'archaic': 'archaic',
            'obsolete': 'archaic',
            'dated': 'archaic',
            'historical': 'archaic',
            'formal': 'formal',
            'literary': 'formal',
            'informal': 'informal',
            'colloquial': 'informal',
            'slang': 'informal',
            'vulgar': 'vulgar',
            'offensive': 'vulgar',

            # Domain
            'medical': 'medical',
            'medicine': 'medical',
            'anatomy': 'medical',
            'biology': 'scientific',
            'chemistry': 'scientific',
            'physics': 'scientific',
            'botany': 'botanical',
            'zoology': 'zoological',
            'nautical': 'nautical',
            'maritime': 'nautical',
            'legal': 'legal',
            'law': 'legal',
            'music': 'musical',
            'architecture': 'architectural',
            'religious': 'religious',
            'theological': 'religious',

            # Usage
            'rare': 'rare',
            'dialectal': 'dialectal',
            'regional': 'regional',
            'technical': 'technical',
            'specialist': 'technical',
        }

    def normalize_labels(self, raw_labels: List[str]) -> Dict[str, Set[str]]:
        """
        Normalize and categorize usage labels.

        Args:
            raw_labels: List of raw label strings

        Returns:
            Dictionary with categorized normalized labels
        """
        categorized = {
            'register': set(),
            'domain': set(),
            'usage': set(),
            'other': set()
        }

        for label in raw_labels:
            label_lower = label.lower().strip()

            # Check for known normalizations
            normalized = self.label_normalizations.get(label_lower, label_lower)

            # Categorize
            if normalized in ['archaic', 'formal', 'informal', 'vulgar']:
                categorized['register'].add(normalized)
            elif normalized in ['medical', 'scientific', 'botanical', 'zoological',
                               'nautical', 'legal', 'musical', 'architectural', 'religious']:
                categorized['domain'].add(normalized)
            elif normalized in ['rare', 'dialectal', 'regional', 'technical']:
                categorized['usage'].add(normalized)
            else:
                categorized['other'].add(normalized)

        return {k: list(v) for k, v in categorized.items()}

    def parse_sense_list(self, definitions: List[str], examples: List[str] = None) -> List[Dict]:
        """
        Parse definitions and examples into structured sense list.

        Args:
            definitions: List of definition strings
            examples: List of example sentences

        Returns:
            List of sense dictionaries
        """
        senses = []

        for i, definition in enumerate(definitions):
            sense = {
                'sense_id': i + 1,
                'definition': definition.strip(),
                'examples': []
            }

            # Try to associate examples with senses
            # (Simple heuristic - in production, use more sophisticated matching)
            if examples and i < len(examples):
                sense['examples'].append(examples[i])

            senses.append(sense)

        return senses

    def extract_usage_notes(self, definitions: List[str], labels: List[str]) -> List[str]:
        """
        Extract usage notes from definitions and labels.

        Args:
            definitions: List of definition strings
            labels: List of usage labels

        Returns:
            List of usage notes
        """
        notes = []

        # Extract parenthetical notes from definitions
        for definition in definitions:
            # Look for usage notes in parentheses
            matches = re.findall(r'\((usually|often|sometimes|rarely|mainly|chiefly|especially)[^)]+\)', definition)
            notes.extend(matches)

        # Convert labels to usage notes
        for label in labels:
            if label:
                notes.append(f"Marked as: {label}")

        return notes

    def get_wordnet_relations(self, word: str, pos: str = None) -> Dict[str, List[str]]:
        """
        Get lexical relations from WordNet.

        Args:
            word: The word to look up
            pos: Part of speech filter

        Returns:
            Dictionary of lexical relations
        """
        if not WORDNET_AVAILABLE:
            return {
                'synonyms': [],
                'antonyms': [],
                'hypernyms': [],
                'hyponyms': []
            }

        # Map our POS tags to WordNet POS
        pos_map = {
            'noun': wn.NOUN,
            'verb': wn.VERB,
            'adjective': wn.ADJ,
            'adverb': wn.ADV
        }

        synsets = wn.synsets(word)
        if pos and pos.lower() in pos_map:
            synsets = wn.synsets(word, pos=pos_map[pos.lower()])

        if not synsets:
            return {
                'synonyms': [],
                'antonyms': [],
                'hypernyms': [],
                'hyponyms': []
            }

        # Use the first synset (most common sense)
        synset = synsets[0]

        # Get relations
        synonyms = set()
        antonyms = set()
        hypernyms = set()
        hyponyms = set()

        # Synonyms (lemmas in the synset)
        for lemma in synset.lemmas():
            if lemma.name() != word:
                synonyms.add(lemma.name().replace('_', ' '))

            # Antonyms
            for ant in lemma.antonyms():
                antonyms.add(ant.name().replace('_', ' '))

        # Hypernyms (more general terms)
        for hypernym in synset.hypernyms():
            hypernyms.add(hypernym.lemmas()[0].name().replace('_', ' '))

        # Hyponyms (more specific terms)
        for hyponym in synset.hyponyms():
            if len(hyponyms) < 5:  # Limit to avoid too many
                hyponyms.add(hyponym.lemmas()[0].name().replace('_', ' '))

        return {
            'synonyms': list(synonyms)[:10],
            'antonyms': list(antonyms)[:10],
            'hypernyms': list(hypernyms)[:5],
            'hyponyms': list(hyponyms)[:5]
        }

    def process_word(self, lemma: str, lexico_data: Dict) -> Dict:
        """
        Process lexical structure for a word.

        Args:
            lemma: The word
            lexico_data: Dictionary data from lexico table

        Returns:
            Structured lexical data
        """
        definitions = lexico_data.get('definitions', [])
        examples = lexico_data.get('examples', [])
        labels_raw = lexico_data.get('labels_raw', [])
        pos_raw = lexico_data.get('pos_raw', [])

        # Parse sense list
        sense_list = self.parse_sense_list(definitions, examples)

        # Normalize labels
        labels_categorized = self.normalize_labels(labels_raw)

        # Extract usage notes
        usage_notes = self.extract_usage_notes(definitions, labels_raw)

        # Get WordNet relations (use first POS if available)
        pos = pos_raw[0] if pos_raw else None
        wordnet_relations = self.get_wordnet_relations(lemma, pos)

        return {
            'lemma': lemma,
            'sense_list': sense_list,
            'usage_notes': usage_notes,
            'labels_norm': labels_categorized,
            'synonyms': wordnet_relations['synonyms'],
            'antonyms': wordnet_relations['antonyms'],
            'hypernyms': wordnet_relations['hypernyms'],
            'hyponyms': wordnet_relations['hyponyms']
        }

    def process_from_lexico(self, limit: Optional[int] = None):
        """
        Process lexical structure for words in lexico table.

        Args:
            limit: Maximum number of words to process
        """
        with get_session() as session:
            query = session.query(Lexico)

            if limit:
                query = query.limit(limit)

            lexico_entries = query.all()

        logger.info(f"Processing lexical structure for {len(lexico_entries)} words...")

        processed = 0

        for entry in tqdm(lexico_entries, desc="Processing lexical structure"):
            lexico_data = {
                'definitions': entry.definitions,
                'examples': entry.examples,
                'labels_raw': entry.labels_raw or [],
                'pos_raw': entry.pos_raw or []
            }

            structured_data = self.process_word(entry.lemma, lexico_data)

            # Check if semantics entry exists
            with get_session() as session:
                existing = session.query(Semantics).filter_by(lemma=entry.lemma).first()

                if existing:
                    # Update existing entry
                    existing.synonyms = structured_data['synonyms']
                    existing.antonyms = structured_data['antonyms']
                    existing.hypernyms = structured_data['hypernyms']
                    existing.hyponyms = structured_data['hyponyms']
                else:
                    # Create new entry (partial - will be completed in later phases)
                    semantics_entry = Semantics(
                        lemma=structured_data['lemma'],
                        synonyms=structured_data['synonyms'],
                        antonyms=structured_data['antonyms'],
                        hypernyms=structured_data['hypernyms'],
                        hyponyms=structured_data['hyponyms'],
                        domain_tags=[],  # Will be populated by tagger
                        register_tags=structured_data['labels_norm']['register'],
                        affect_tags=[],
                        imagery_tags=[],
                        theme_tags=[],
                        embedding=None  # Will be populated by embedder
                    )
                    session.add(semantics_entry)

            processed += 1

        logger.info(f"Lexical structure processing complete: {processed} words processed")


def main():
    """Command-line interface for lexical structure processing."""
    import argparse

    parser = argparse.ArgumentParser(description="Process lexical structure")
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of words to process'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # Ensure WordNet is downloaded
    if WORDNET_AVAILABLE:
        try:
            import nltk
            nltk.data.find('corpora/wordnet')
        except LookupError:
            logger.info("Downloading WordNet corpus...")
            import nltk
            nltk.download('wordnet')
            nltk.download('omw-1.4')

    processor = LexicalStructure()
    processor.process_from_lexico(limit=args.limit)


if __name__ == "__main__":
    main()
