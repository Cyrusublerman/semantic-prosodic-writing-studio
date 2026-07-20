"""
WORD_RECORD builder - unifies all data sources into final schema.

Combines data from rare_lexicon, lexico, phonetics, freq_profile, and semantics
into the unified word_record table.
"""

import logging
from typing import Optional
from tqdm import tqdm

from ..database import (
    WordRecord, RareLexicon, Lexico, Phonetics,
    FreqProfile, Semantics, get_session
)

logger = logging.getLogger(__name__)


class WordRecordBuilder:
    """Builds unified WORD_RECORD entries from multiple data sources."""

    def __init__(self):
        pass

    def build_word_record(self, lemma: str) -> Optional[dict]:
        """
        Build a unified WORD_RECORD for a word.

        Args:
            lemma: The word to build record for

        Returns:
            Dictionary with unified word data or None if insufficient data
        """
        with get_session() as session:
            # Fetch data from all sources
            rare_entry = session.query(RareLexicon).filter_by(lemma=lemma).first()
            lexico_entry = session.query(Lexico).filter_by(lemma=lemma).first()
            phonetics_entry = session.query(Phonetics).filter_by(lemma=lemma).first()
            freq_entry = session.query(FreqProfile).filter_by(lemma=lemma).first()
            semantics_entry = session.query(Semantics).filter_by(lemma=lemma).first()

            # Must have at least rare_entry to proceed
            if not rare_entry:
                logger.debug(f"No rare_lexicon entry for '{lemma}'")
                return None

            # Build unified record
            record_data = {
                'lemma': lemma,
                'pos_primary': None,
                'pos_all': [],
                'ipa_us': None,
                'ipa_uk': None,
                'stress_pattern': None,
                'syllable_count': None,
                'rhyme_key': None,
                'rarity_score': 0.8,  # Default for rare words
                'temporal_profile': 'unknown',
                'domain_tags': [],
                'register_tags': [],
                'affect_tags': [],
                'imagery_tags': [],
                'embedding': None,
                'concept_links': [],
                'definitions': [],
                'examples': []
            }

            # Add lexico data
            if lexico_entry:
                record_data['definitions'] = lexico_entry.definitions or []
                record_data['examples'] = lexico_entry.examples or []

                if lexico_entry.pos_raw:
                    record_data['pos_all'] = lexico_entry.pos_raw
                    record_data['pos_primary'] = lexico_entry.pos_raw[0]

            # Add phonetics data
            if phonetics_entry:
                record_data['ipa_us'] = phonetics_entry.ipa_us_cmu
                record_data['ipa_uk'] = phonetics_entry.ipa_dict_uk
                record_data['stress_pattern'] = phonetics_entry.stress_pattern
                record_data['syllable_count'] = phonetics_entry.syllable_count
                record_data['rhyme_key'] = phonetics_entry.rhyme_key

            # Add frequency/rarity data
            if freq_entry:
                record_data['rarity_score'] = freq_entry.rarity_score
                record_data['temporal_profile'] = freq_entry.temporal_profile

            # Add semantics data
            if semantics_entry:
                record_data['domain_tags'] = semantics_entry.domain_tags or []
                record_data['register_tags'] = semantics_entry.register_tags or []
                record_data['affect_tags'] = semantics_entry.affect_tags or []
                record_data['imagery_tags'] = semantics_entry.imagery_tags or []
                record_data['embedding'] = semantics_entry.embedding

                # Concept links would be populated by linking to concept_node table
                # For now, leave empty
                record_data['concept_links'] = []

            return record_data

    def build_all_records(self, limit: Optional[int] = None, force_rebuild: bool = False):
        """
        Build WORD_RECORD entries for all words in rare_lexicon.

        Args:
            limit: Maximum number of records to build
            force_rebuild: If True, rebuild existing records
        """
        with get_session() as session:
            # Get words from rare_lexicon
            if force_rebuild:
                query = session.query(RareLexicon.lemma)
            else:
                # Only build for words without word_record
                query = session.query(RareLexicon.lemma).outerjoin(
                    WordRecord, RareLexicon.lemma == WordRecord.lemma
                ).filter(WordRecord.id.is_(None))

            if limit:
                query = query.limit(limit)

            words = [row[0] for row in query.all()]

        logger.info(f"Building WORD_RECORD entries for {len(words)} words...")

        built = 0
        failed = 0

        for word in tqdm(words, desc="Building word records"):
            record_data = self.build_word_record(word)

            if record_data:
                with get_session() as session:
                    # Check if exists (in case of force_rebuild)
                    existing = session.query(WordRecord).filter_by(lemma=word).first()

                    if existing and force_rebuild:
                        # Update existing
                        for key, value in record_data.items():
                            setattr(existing, key, value)
                    elif not existing:
                        # Create new
                        word_record = WordRecord(**record_data)
                        session.add(word_record)

                built += 1
            else:
                failed += 1

            # Commit in batches
            if (built + failed) % 100 == 0:
                with get_session() as session:
                    session.commit()

        logger.info(f"WORD_RECORD building complete: {built} built, {failed} failed")

    def get_word_record(self, lemma: str) -> Optional[WordRecord]:
        """
        Get a WORD_RECORD for a word.

        Args:
            lemma: The word

        Returns:
            WordRecord object or None
        """
        with get_session() as session:
            return session.query(WordRecord).filter_by(lemma=lemma).first()

    def search_words(self, **filters) -> list:
        """
        Search for words with specific criteria.

        Args:
            **filters: Filter criteria (e.g., rarity_score, domain_tags, etc.)

        Returns:
            List of matching WordRecord objects
        """
        with get_session() as session:
            query = session.query(WordRecord)

            # Apply filters
            if 'min_rarity' in filters:
                query = query.filter(WordRecord.rarity_score >= filters['min_rarity'])

            if 'max_rarity' in filters:
                query = query.filter(WordRecord.rarity_score <= filters['max_rarity'])

            if 'syllable_count' in filters:
                query = query.filter(WordRecord.syllable_count == filters['syllable_count'])

            if 'rhyme_key' in filters:
                query = query.filter(WordRecord.rhyme_key == filters['rhyme_key'])

            if 'pos' in filters:
                query = query.filter(WordRecord.pos_primary == filters['pos'])

            # Domain/affect/theme tag filters would require JSON querying
            # (implementation depends on database backend)

            results = query.all()

        return results

    def get_statistics(self) -> dict:
        """
        Get statistics about WORD_RECORD entries.

        Returns:
            Dictionary of statistics
        """
        with get_session() as session:
            total = session.query(WordRecord).count()

            # Count by POS
            pos_counts = {}
            records = session.query(WordRecord).all()

            for record in records:
                pos = record.pos_primary or 'unknown'
                pos_counts[pos] = pos_counts.get(pos, 0) + 1

            # Rarity distribution
            rarity_dist = {
                'very_rare': 0,
                'rare': 0,
                'uncommon': 0,
                'common': 0
            }

            for record in records:
                score = record.rarity_score or 0.5

                if score > 0.7:
                    rarity_dist['very_rare'] += 1
                elif score > 0.5:
                    rarity_dist['rare'] += 1
                elif score > 0.3:
                    rarity_dist['uncommon'] += 1
                else:
                    rarity_dist['common'] += 1

        return {
            'total': total,
            'pos_distribution': pos_counts,
            'rarity_distribution': rarity_dist
        }


def main():
    """Command-line interface for WORD_RECORD building."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Build unified WORD_RECORD entries")
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of records to build'
    )
    parser.add_argument(
        '--rebuild',
        action='store_true',
        help='Force rebuild existing records'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics'
    )
    parser.add_argument(
        '--word',
        type=str,
        help='Show record for specific word'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    builder = WordRecordBuilder()

    if args.stats:
        stats = builder.get_statistics()
        print("\nWORD_RECORD Statistics:")
        print(json.dumps(stats, indent=2))
    elif args.word:
        record = builder.get_word_record(args.word)
        if record:
            print(f"\nWORD_RECORD for '{args.word}':")
            print(f"  POS: {record.pos_primary} {record.pos_all}")
            print(f"  IPA: {record.ipa_us}")
            print(f"  Syllables: {record.syllable_count}")
            print(f"  Rarity: {record.rarity_score:.3f}")
            print(f"  Domain tags: {record.domain_tags}")
            print(f"  Affect tags: {record.affect_tags}")
            print(f"  Definitions: {len(record.definitions or [])}")
        else:
            print(f"No WORD_RECORD found for '{args.word}'")
    else:
        builder.build_all_records(limit=args.limit, force_rebuild=args.rebuild)


if __name__ == "__main__":
    main()
