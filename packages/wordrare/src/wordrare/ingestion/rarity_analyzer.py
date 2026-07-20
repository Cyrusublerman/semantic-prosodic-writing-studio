"""
Frequency and rarity analysis using corpus data.
"""

import logging
from typing import Dict, Optional, List
import math
from pathlib import Path
from tqdm import tqdm
import json

from ..config import NGRAM_DATA_PATH
from ..database import FreqProfile, get_session

logger = logging.getLogger(__name__)


class RarityAnalyzer:
    """Analyzes word frequency and computes rarity scores."""

    def __init__(self, ngram_path: Path = None):
        self.ngram_path = ngram_path or NGRAM_DATA_PATH
        self.freq_cache = {}

        # Frequency thresholds for classification
        self.freq_thresholds = {
            'very_common': 1e-4,
            'common': 1e-5,
            'uncommon': 1e-6,
            'rare': 1e-7,
            'very_rare': 0
        }

    def load_frequency_data(self, source: str = 'web_corpus'):
        """
        Load frequency data from various sources.

        Args:
            source: Source corpus ('web_corpus', 'google_ngram', etc.)
        """
        # This is a placeholder - actual implementation would load from real corpus
        # For now, we'll use a simple heuristic based on word characteristics

        logger.info(f"Loading frequency data from {source}")

        # In production, you would load actual corpus frequency data here
        # Example: load Google Books Ngram data, web corpus frequencies, etc.

    def estimate_frequency(self, word: str, word_data: Dict = None) -> float:
        """
        Estimate word frequency using heuristics.

        In production, this would query actual corpus data.
        For now, uses heuristics based on word characteristics.

        Args:
            word: The word to analyze
            word_data: Optional dictionary data for the word

        Returns:
            Estimated frequency (0.0 to 1.0)
        """
        # Simple heuristic-based estimation
        # Lower score = rarer word

        score = 1.0

        # Length penalty (longer words tend to be rarer)
        length_factor = min(len(word) / 15.0, 1.0)
        score *= (1.0 - length_factor * 0.7)

        # Archaic/obsolete labels suggest rarity
        if word_data and 'labels_raw' in word_data:
            labels = word_data.get('labels_raw', [])
            archaic_markers = ['archaic', 'obsolete', 'rare', 'historical', 'dated']

            for marker in archaic_markers:
                if any(marker in str(label).lower() for label in labels):
                    score *= 0.3
                    break

        # Technical/specialized domains suggest rarity
        if word_data and 'domain_tags' in word_data:
            domains = word_data.get('domain_tags', [])
            if domains and len(domains) > 0:
                score *= 0.6

        # Words from Phrontistery are by definition rare
        score *= 0.2

        return max(0.0001, min(1.0, score))

    def compute_rarity_score(self, freq_written: float, freq_spoken: float = None,
                            dispersion: float = None) -> float:
        """
        Compute rarity score from frequency data.

        Args:
            freq_written: Written corpus frequency
            freq_spoken: Spoken corpus frequency (optional)
            dispersion: Dispersion index (optional)

        Returns:
            Rarity score (0.0 = common, 1.0 = extremely rare)
        """
        # Invert frequency to get rarity
        # Use log scale for better distribution

        if freq_written <= 0:
            return 1.0

        # Log transform
        log_freq = math.log10(freq_written + 1e-10)

        # Normalize to 0-1 range
        # Assume frequency range from 1e-8 (very rare) to 1e-3 (common)
        min_log = -8
        max_log = -3

        normalized = (log_freq - min_log) / (max_log - min_log)
        rarity = 1.0 - max(0.0, min(1.0, normalized))

        # Adjust based on spoken frequency if available
        if freq_spoken is not None and freq_spoken > 0:
            spoken_rarity = 1.0 - math.log10(freq_spoken + 1e-10) / -3
            rarity = (rarity + spoken_rarity) / 2

        # Adjust based on dispersion (low dispersion = more specialized = rarer)
        if dispersion is not None:
            dispersion_factor = 1.0 - dispersion
            rarity = rarity * 0.7 + dispersion_factor * 0.3

        return rarity

    def classify_temporal_profile(self, historical_freq: List[float]) -> str:
        """
        Classify temporal usage profile.

        Args:
            historical_freq: List of frequency values over time

        Returns:
            Profile classification: 'archaic', 'declining', 'stable', 'emerging', 'modern'
        """
        if not historical_freq or len(historical_freq) < 3:
            return 'unknown'

        early = sum(historical_freq[:len(historical_freq)//3]) / (len(historical_freq)//3)
        recent = sum(historical_freq[-len(historical_freq)//3:]) / (len(historical_freq)//3)

        ratio = recent / (early + 1e-10)

        if ratio < 0.2:
            return 'archaic'
        elif ratio < 0.7:
            return 'declining'
        elif ratio > 2.0:
            return 'emerging'
        elif ratio > 1.3:
            return 'modern'
        else:
            return 'stable'

    def analyze_word(self, word: str, word_data: Dict = None) -> Dict:
        """
        Analyze a word and compute rarity profile.

        Args:
            word: The word to analyze
            word_data: Optional dictionary/semantic data

        Returns:
            Dictionary with rarity analysis
        """
        # Estimate frequency
        freq_written = self.estimate_frequency(word, word_data)

        # For now, use heuristic values
        # In production, query actual corpus data

        freq_spoken = freq_written * 0.8  # Approximation
        dispersion = 0.5  # Neutral dispersion
        historical_freq = [freq_written * (0.8 + i * 0.05) for i in range(10)]

        rarity_score = self.compute_rarity_score(freq_written, freq_spoken, dispersion)
        temporal_profile = self.classify_temporal_profile(historical_freq)

        return {
            'lemma': word,
            'freq_written': freq_written,
            'freq_spoken': freq_spoken,
            'freq_historical': historical_freq,
            'dispersion_index': dispersion,
            'rarity_score': rarity_score,
            'temporal_profile': temporal_profile
        }

    def analyze_from_rare_lexicon(self, limit: Optional[int] = None):
        """
        Analyze words from rare_lexicon and populate freq_profile table.

        Args:
            limit: Maximum number of words to analyze
        """
        with get_session() as session:
            from ..database import RareLexicon, Lexico

            # Get words that don't have frequency profiles yet
            query = session.query(RareLexicon.lemma).outerjoin(
                FreqProfile, RareLexicon.lemma == FreqProfile.lemma
            ).filter(FreqProfile.id.is_(None))

            if limit:
                query = query.limit(limit)

            words = [row[0] for row in query.all()]

            # Also fetch any available lexico data for better analysis
            word_data_map = {}
            for word in words:
                lexico_entry = session.query(Lexico).filter_by(lemma=word).first()
                if lexico_entry:
                    word_data_map[word] = {
                        'labels_raw': lexico_entry.labels_raw,
                        'definitions': lexico_entry.definitions
                    }

        logger.info(f"Analyzing rarity for {len(words)} words...")

        analyzed = 0

        for word in tqdm(words, desc="Analyzing rarity"):
            word_data = word_data_map.get(word)
            rarity_data = self.analyze_word(word, word_data)

            with get_session() as session:
                freq_profile = FreqProfile(**rarity_data)
                session.add(freq_profile)

            analyzed += 1

            # Commit in batches
            if analyzed % 100 == 0:
                session.commit()

        logger.info(f"Rarity analysis complete: {analyzed} words analyzed")

    def export_rarity_distribution(self, output_path: Path):
        """
        Export rarity score distribution for analysis.

        Args:
            output_path: Path to save distribution data
        """
        with get_session() as session:
            profiles = session.query(FreqProfile).all()

            distribution = {
                'very_rare': 0,
                'rare': 0,
                'uncommon': 0,
                'common': 0,
                'very_common': 0
            }

            for profile in profiles:
                score = profile.rarity_score

                if score > 0.8:
                    distribution['very_rare'] += 1
                elif score > 0.6:
                    distribution['rare'] += 1
                elif score > 0.4:
                    distribution['uncommon'] += 1
                elif score > 0.2:
                    distribution['common'] += 1
                else:
                    distribution['very_common'] += 1

            with open(output_path, 'w') as f:
                json.dump(distribution, f, indent=2)

            logger.info(f"Exported rarity distribution to {output_path}")
            logger.info(f"Distribution: {distribution}")


def main():
    """Command-line interface for rarity analysis."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze word rarity")
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of words to analyze'
    )
    parser.add_argument(
        '--export',
        type=Path,
        help='Export rarity distribution to file'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    analyzer = RarityAnalyzer()
    analyzer.analyze_from_rare_lexicon(limit=args.limit)

    if args.export:
        analyzer.export_rarity_distribution(args.export)


if __name__ == "__main__":
    main()
