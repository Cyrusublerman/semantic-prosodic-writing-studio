"""
Dictionary browser - inspect WORD_RECORD entries.
"""

import logging
from typing import Optional, List
import json

from ..database import WordRecord, get_session

logger = logging.getLogger(__name__)


class DictionaryBrowser:
    """Browse and inspect WORD_RECORD entries."""

    def __init__(self):
        pass

    def get_word(self, lemma: str) -> Optional[WordRecord]:
        """Get WORD_RECORD for a specific word."""
        with get_session() as session:
            return session.query(WordRecord).filter_by(lemma=lemma).first()

    def search(self, **filters) -> List[WordRecord]:
        """
        Search for words with filters.

        Supported filters:
        - pos: Part of speech
        - min_rarity: Minimum rarity score
        - max_rarity: Maximum rarity score
        - syllables: Syllable count
        - domain_tag: Domain tag to match
        - affect_tag: Affect tag to match
        - limit: Max results (default 20)
        """
        with get_session() as session:
            query = session.query(WordRecord)

            if 'pos' in filters:
                query = query.filter(WordRecord.pos_primary == filters['pos'])

            if 'min_rarity' in filters:
                query = query.filter(WordRecord.rarity_score >= filters['min_rarity'])

            if 'max_rarity' in filters:
                query = query.filter(WordRecord.rarity_score <= filters['max_rarity'])

            if 'syllables' in filters:
                query = query.filter(WordRecord.syllable_count == filters['syllables'])

            limit = filters.get('limit', 20)
            results = query.limit(limit).all()

            # Filter by tags (requires checking JSON fields)
            if 'domain_tag' in filters:
                results = [r for r in results if r.domain_tags and
                          filters['domain_tag'] in r.domain_tags]

            if 'affect_tag' in filters:
                results = [r for r in results if r.affect_tags and
                          filters['affect_tag'] in r.affect_tags]

            return results

    def display_word(self, word_record: WordRecord):
        """Display formatted word information."""
        print(f"\n{'=' * 70}")
        print(f"WORD: {word_record.lemma.upper()}")
        print(f"{'=' * 70}")

        print(f"\nPart of Speech: {word_record.pos_primary}")
        if word_record.pos_all and len(word_record.pos_all) > 1:
            print(f"  All POS: {', '.join(word_record.pos_all)}")

        print(f"\nPhonetics:")
        print(f"  IPA (US): {word_record.ipa_us or 'N/A'}")
        print(f"  Syllables: {word_record.syllable_count or 'N/A'}")
        print(f"  Stress Pattern: {word_record.stress_pattern or 'N/A'}")
        print(f"  Rhyme Key: {word_record.rhyme_key or 'N/A'}")

        print(f"\nRarity:")
        print(f"  Score: {word_record.rarity_score:.3f}" if word_record.rarity_score else "  Score: N/A")
        print(f"  Temporal Profile: {word_record.temporal_profile or 'N/A'}")

        print(f"\nSemantic Tags:")
        if word_record.domain_tags:
            print(f"  Domain: {', '.join(word_record.domain_tags)}")
        if word_record.register_tags:
            print(f"  Register: {', '.join(word_record.register_tags)}")
        if word_record.affect_tags:
            print(f"  Affect: {', '.join(word_record.affect_tags)}")
        if word_record.imagery_tags:
            print(f"  Imagery: {', '.join(word_record.imagery_tags)}")

        if word_record.definitions:
            print(f"\nDefinitions:")
            for i, defn in enumerate(word_record.definitions[:3], 1):
                print(f"  {i}. {defn}")
            if len(word_record.definitions) > 3:
                print(f"  ... and {len(word_record.definitions) - 3} more")

        if word_record.examples:
            print(f"\nExamples:")
            for i, ex in enumerate(word_record.examples[:2], 1):
                print(f"  {i}. {ex}")

        print(f"\n{'=' * 70}\n")

    def display_search_results(self, results: List[WordRecord]):
        """Display search results in table format."""
        if not results:
            print("\nNo results found.")
            return

        print(f"\nFound {len(results)} words:")
        print(f"\n{'Lemma':<20} {'POS':<10} {'Syllables':<10} {'Rarity':<10} {'Tags'}")
        print("-" * 80)

        for word in results:
            tags = []
            if word.domain_tags:
                tags.extend(word.domain_tags[:2])
            if word.affect_tags:
                tags.extend(word.affect_tags[:1])

            tag_str = ', '.join(tags[:3]) if tags else '-'

            print(f"{word.lemma:<20} "
                  f"{word.pos_primary or 'N/A':<10} "
                  f"{word.syllable_count or 'N/A':<10} "
                  f"{word.rarity_score:.2f if word.rarity_score else 'N/A':<10} "
                  f"{tag_str}")

        print()

    def browse_by_rarity(self, min_rarity: float = 0.7, limit: int = 20):
        """Browse words by rarity."""
        results = self.search(min_rarity=min_rarity, limit=limit)
        self.display_search_results(results)

    def browse_by_domain(self, domain: str, limit: int = 20):
        """Browse words by domain tag."""
        results = self.search(domain_tag=domain, limit=limit)
        self.display_search_results(results)


def main():
    """CLI for dictionary browser."""
    import argparse

    parser = argparse.ArgumentParser(description="Dictionary Browser")
    parser.add_argument(
        'word',
        nargs='?',
        help='Word to look up'
    )
    parser.add_argument(
        '--search',
        action='store_true',
        help='Search mode'
    )
    parser.add_argument(
        '--pos',
        type=str,
        help='Filter by part of speech'
    )
    parser.add_argument(
        '--min-rarity',
        type=float,
        help='Minimum rarity score'
    )
    parser.add_argument(
        '--max-rarity',
        type=float,
        help='Maximum rarity score'
    )
    parser.add_argument(
        '--syllables',
        type=int,
        help='Filter by syllable count'
    )
    parser.add_argument(
        '--domain',
        type=str,
        help='Filter by domain tag'
    )
    parser.add_argument(
        '--affect',
        type=str,
        help='Filter by affect tag'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=20,
        help='Max results'
    )

    args = parser.parse_args()

    browser = DictionaryBrowser()

    if args.word and not args.search:
        # Look up specific word
        word_record = browser.get_word(args.word)

        if word_record:
            browser.display_word(word_record)
        else:
            print(f"\nWord '{args.word}' not found in dictionary.")

    elif args.search or any([args.pos, args.min_rarity, args.domain, args.affect]):
        # Search mode
        filters = {'limit': args.limit}

        if args.pos:
            filters['pos'] = args.pos
        if args.min_rarity is not None:
            filters['min_rarity'] = args.min_rarity
        if args.max_rarity is not None:
            filters['max_rarity'] = args.max_rarity
        if args.syllables:
            filters['syllables'] = args.syllables
        if args.domain:
            filters['domain_tag'] = args.domain
        if args.affect:
            filters['affect_tag'] = args.affect

        results = browser.search(**filters)
        browser.display_search_results(results)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
