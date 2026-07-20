"""
Dictionary enrichment using external APIs (Wordnik, Wiktionary, etc.).
"""

import requests
from typing import Dict, Optional, List
import logging
import time
from tqdm import tqdm

from ..config import WORDNIK_API_KEY
from ..database import Lexico, get_session

logger = logging.getLogger(__name__)


class DictionaryEnricher:
    """Enriches words with dictionary data from various APIs."""

    def __init__(self, wordnik_api_key: str = None):
        self.wordnik_api_key = wordnik_api_key or WORDNIK_API_KEY
        self.wordnik_base_url = "https://api.wordnik.com/v4"
        self.session = requests.Session()

    def fetch_wordnik_data(self, word: str) -> Optional[Dict]:
        """
        Fetch comprehensive data for a word from Wordnik API.

        Args:
            word: The word to look up

        Returns:
            Dictionary containing word data or None if not found
        """
        if not self.wordnik_api_key:
            logger.warning("No Wordnik API key configured")
            return None

        try:
            # Get definitions
            definitions_url = f"{self.wordnik_base_url}/word.json/{word}/definitions"
            params = {
                'api_key': self.wordnik_api_key,
                'limit': 10,
                'includeRelated': 'true',
                'useCanonical': 'true',
                'includeTags': 'false'
            }

            definitions_response = self.session.get(
                definitions_url,
                params=params,
                timeout=10
            )

            if definitions_response.status_code == 404:
                return None

            definitions_response.raise_for_status()
            definitions_data = definitions_response.json()

            # Get examples
            examples_url = f"{self.wordnik_base_url}/word.json/{word}/examples"
            examples_response = self.session.get(
                examples_url,
                params={'api_key': self.wordnik_api_key, 'limit': 5},
                timeout=10
            )

            examples_data = []
            if examples_response.status_code == 200:
                examples_json = examples_response.json()
                if 'examples' in examples_json:
                    examples_data = [ex['text'] for ex in examples_json['examples']]

            # Parse definitions
            definitions = []
            pos_tags = set()
            labels = []

            for defn in definitions_data:
                definitions.append(defn.get('text', ''))
                if 'partOfSpeech' in defn:
                    pos_tags.add(defn['partOfSpeech'])
                if 'labels' in defn:
                    labels.extend(defn.get('labels', []))

            # Get etymology (separate endpoint)
            etymology_url = f"{self.wordnik_base_url}/word.json/{word}/etymologies"
            etymology_response = self.session.get(
                etymology_url,
                params={'api_key': self.wordnik_api_key},
                timeout=10
            )

            etymology = ""
            if etymology_response.status_code == 200:
                etymology_data = etymology_response.json()
                if etymology_data and len(etymology_data) > 0:
                    etymology = etymology_data[0]

            return {
                'lemma': word,
                'definitions': definitions,
                'examples': examples_data,
                'labels_raw': list(set(labels)),
                'etymology_raw': etymology,
                'pos_raw': list(pos_tags),
                'source': 'wordnik'
            }

        except requests.RequestException as e:
            logger.error(f"Error fetching Wordnik data for '{word}': {e}")
            return None

    def fetch_free_dictionary_api(self, word: str) -> Optional[Dict]:
        """
        Fetch data from Free Dictionary API (no key required).

        Args:
            word: The word to look up

        Returns:
            Dictionary containing word data or None if not found
        """
        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            response = self.session.get(url, timeout=10)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()

            if not data:
                return None

            # Parse the response
            entry = data[0]
            definitions = []
            examples = []
            pos_tags = set()
            labels = []

            for meaning in entry.get('meanings', []):
                pos = meaning.get('partOfSpeech')
                if pos:
                    pos_tags.add(pos)

                for defn in meaning.get('definitions', []):
                    definitions.append(defn.get('definition', ''))
                    if 'example' in defn:
                        examples.append(defn['example'])

            return {
                'lemma': word,
                'definitions': definitions,
                'examples': examples,
                'labels_raw': labels,
                'etymology_raw': '',
                'pos_raw': list(pos_tags),
                'source': 'free_dictionary_api'
            }

        except requests.RequestException as e:
            logger.error(f"Error fetching Free Dictionary API data for '{word}': {e}")
            return None

    def enrich_word(self, word: str) -> Optional[Dict]:
        """
        Enrich a word using available dictionary APIs.

        Tries Wordnik first, then falls back to Free Dictionary API.

        Args:
            word: The word to enrich

        Returns:
            Dictionary data or None
        """
        # Try Wordnik first
        if self.wordnik_api_key:
            data = self.fetch_wordnik_data(word)
            if data:
                return data

        # Fall back to Free Dictionary API
        data = self.fetch_free_dictionary_api(word)
        return data

    def enrich_from_rare_lexicon(self, limit: Optional[int] = None, delay: float = 0.5):
        """
        Enrich words from the rare_lexicon database.

        Args:
            limit: Maximum number of words to enrich (None for all)
            delay: Delay between API calls in seconds
        """
        with get_session() as session:
            # Get words from rare_lexicon that don't have lexico entries
            from ..database import RareLexicon

            query = session.query(RareLexicon.lemma).outerjoin(
                Lexico, RareLexicon.lemma == Lexico.lemma
            ).filter(Lexico.id.is_(None))

            if limit:
                query = query.limit(limit)

            words = [row[0] for row in query.all()]

        logger.info(f"Enriching {len(words)} words...")

        enriched = 0
        failed = 0

        for word in tqdm(words, desc="Enriching words"):
            data = self.enrich_word(word)

            if data:
                with get_session() as session:
                    lexico_entry = Lexico(**data)
                    session.add(lexico_entry)
                enriched += 1
            else:
                failed += 1

            time.sleep(delay)  # Rate limiting

            # Progress update every 100 words
            if (enriched + failed) % 100 == 0:
                logger.info(f"Progress: {enriched} enriched, {failed} failed")

        logger.info(f"Enrichment complete: {enriched} enriched, {failed} failed")

    def save_word_data(self, word_data: Dict):
        """Save enriched word data to database."""
        with get_session() as session:
            # Check if already exists
            existing = session.query(Lexico).filter_by(
                lemma=word_data['lemma'],
                source=word_data['source']
            ).first()

            if not existing:
                lexico_entry = Lexico(**word_data)
                session.add(lexico_entry)
                logger.debug(f"Added lexico entry for '{word_data['lemma']}'")


def main():
    """Command-line interface for dictionary enrichment."""
    import argparse

    parser = argparse.ArgumentParser(description="Enrich words with dictionary data")
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of words to enrich'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='Delay between API calls (seconds)'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    enricher = DictionaryEnricher()
    enricher.enrich_from_rare_lexicon(limit=args.limit, delay=args.delay)


if __name__ == "__main__":
    main()
