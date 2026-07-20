"""
Phonetics and IPA processing using CMU Dictionary and other sources.
"""

import re
from typing import Dict, Optional, List, Tuple
import logging
from pathlib import Path
from tqdm import tqdm

try:
    import pronouncing
except ImportError:
    pronouncing = None

from ..config import CMU_DICT_PATH
from ..database import Phonetics, Lexico, get_session

logger = logging.getLogger(__name__)


class IPAProcessor:
    """Processes phonetic data and generates IPA representations."""

    def __init__(self, cmu_dict_path: Path = None):
        self.cmu_dict_path = cmu_dict_path or CMU_DICT_PATH
        self.cmu_dict = {}
        self.load_cmu_dict()

        # ARPAbet to IPA mapping (simplified)
        self.arpabet_to_ipa = {
            'AA': 'ɑ', 'AE': 'æ', 'AH': 'ʌ', 'AO': 'ɔ', 'AW': 'aʊ',
            'AY': 'aɪ', 'B': 'b', 'CH': 'tʃ', 'D': 'd', 'DH': 'ð',
            'EH': 'ɛ', 'ER': 'ɝ', 'EY': 'eɪ', 'F': 'f', 'G': 'ɡ',
            'HH': 'h', 'IH': 'ɪ', 'IY': 'i', 'JH': 'dʒ', 'K': 'k',
            'L': 'l', 'M': 'm', 'N': 'n', 'NG': 'ŋ', 'OW': 'oʊ',
            'OY': 'ɔɪ', 'P': 'p', 'R': 'ɹ', 'S': 's', 'SH': 'ʃ',
            'T': 't', 'TH': 'θ', 'UH': 'ʊ', 'UW': 'u', 'V': 'v',
            'W': 'w', 'Y': 'j', 'Z': 'z', 'ZH': 'ʒ'
        }

    def load_cmu_dict(self):
        """Load CMU Pronouncing Dictionary."""
        if pronouncing:
            # Use pronouncing library if available
            logger.info("Using pronouncing library for CMU dictionary")
            return

        # Otherwise load from file
        if not self.cmu_dict_path.exists():
            logger.warning(f"CMU dictionary not found at {self.cmu_dict_path}")
            return

        logger.info(f"Loading CMU dictionary from {self.cmu_dict_path}")

        with open(self.cmu_dict_path, 'r', encoding='latin-1') as f:
            for line in f:
                if line.startswith(';;;'):
                    continue

                parts = line.strip().split('  ')
                if len(parts) >= 2:
                    word = parts[0].lower()
                    # Remove alternative pronunciation markers like (2)
                    word = re.sub(r'\(\d+\)$', '', word)
                    phones = parts[1].split()

                    if word not in self.cmu_dict:
                        self.cmu_dict[word] = []
                    self.cmu_dict[word].append(phones)

        logger.info(f"Loaded {len(self.cmu_dict)} words from CMU dictionary")

    def get_cmu_phones(self, word: str) -> Optional[List[str]]:
        """
        Get ARPAbet phones for a word from CMU dictionary.

        Args:
            word: The word to look up

        Returns:
            List of ARPAbet phones or None
        """
        word = word.lower()

        if pronouncing:
            phones_list = pronouncing.phones_for_word(word)
            if phones_list:
                return phones_list[0].split()

        if word in self.cmu_dict:
            return self.cmu_dict[word][0]

        return None

    def arpabet_to_ipa_convert(self, arpabet: List[str]) -> str:
        """
        Convert ARPAbet phones to IPA.

        Args:
            arpabet: List of ARPAbet phone symbols

        Returns:
            IPA string
        """
        ipa_symbols = []

        for phone in arpabet:
            # Remove stress markers (0, 1, 2)
            clean_phone = re.sub(r'[012]', '', phone)

            # Convert to IPA
            ipa = self.arpabet_to_ipa.get(clean_phone, phone)

            # Add stress markers
            if '1' in phone:  # Primary stress
                ipa = 'ˈ' + ipa
            elif '2' in phone:  # Secondary stress
                ipa = 'ˌ' + ipa

            ipa_symbols.append(ipa)

        return ''.join(ipa_symbols)

    def extract_stress_pattern(self, arpabet: List[str]) -> str:
        """
        Extract stress pattern from ARPAbet phones.

        Args:
            arpabet: List of ARPAbet phone symbols

        Returns:
            Stress pattern string (e.g., "010" for unstressed-stressed-unstressed)
        """
        pattern = []

        for phone in arpabet:
            if '1' in phone:  # Primary stress
                pattern.append('1')
            elif '2' in phone:  # Secondary stress
                pattern.append('2')
            elif any(vowel in phone for vowel in ['AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW']):
                pattern.append('0')

        return ''.join(pattern)

    def count_syllables(self, arpabet: List[str]) -> int:
        """
        Count syllables in ARPAbet representation.

        Args:
            arpabet: List of ARPAbet phone symbols

        Returns:
            Number of syllables
        """
        # Count vowel phones (which represent syllable nuclei)
        vowels = ['AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW']

        count = 0
        for phone in arpabet:
            clean_phone = re.sub(r'[012]', '', phone)
            if clean_phone in vowels:
                count += 1

        return count

    def extract_rhyme_key(self, arpabet: List[str]) -> str:
        """
        Extract rhyme key (final stressed syllable + coda).

        Args:
            arpabet: List of ARPAbet phone symbols

        Returns:
            Rhyme key string
        """
        # Find the last stressed vowel
        last_stress_idx = -1

        for i, phone in enumerate(arpabet):
            if '1' in phone or '2' in phone:
                last_stress_idx = i

        if last_stress_idx == -1:
            # No stress marker - use last vowel
            for i in range(len(arpabet) - 1, -1, -1):
                clean = re.sub(r'[012]', '', arpabet[i])
                if clean in ['AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW']:
                    last_stress_idx = i
                    break

        if last_stress_idx == -1:
            return ''

        # Rhyme key is from stressed vowel to end
        rhyme_phones = arpabet[last_stress_idx:]
        # Remove stress markers for comparison
        rhyme_key = ' '.join(re.sub(r'[012]', '', p) for p in rhyme_phones)

        return rhyme_key

    def extract_onset_nucleus_coda(self, arpabet: List[str]) -> Tuple[str, str, str]:
        """
        Extract onset, nucleus, and coda for sound device analysis.

        Args:
            arpabet: List of ARPAbet phone symbols

        Returns:
            Tuple of (onset, nucleus, coda) strings
        """
        vowels = ['AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW']

        # Find first vowel
        first_vowel_idx = -1
        for i, phone in enumerate(arpabet):
            clean = re.sub(r'[012]', '', phone)
            if clean in vowels:
                first_vowel_idx = i
                break

        if first_vowel_idx == -1:
            return ('', '', '')

        # Find last vowel
        last_vowel_idx = first_vowel_idx
        for i in range(len(arpabet) - 1, first_vowel_idx, -1):
            clean = re.sub(r'[012]', '', arpabet[i])
            if clean in vowels:
                last_vowel_idx = i
                break

        onset = ' '.join(re.sub(r'[012]', '', p) for p in arpabet[:first_vowel_idx])
        nucleus = ' '.join(re.sub(r'[012]', '', p) for p in arpabet[first_vowel_idx:last_vowel_idx + 1])
        coda = ' '.join(re.sub(r'[012]', '', p) for p in arpabet[last_vowel_idx + 1:])

        return (onset, nucleus, coda)

    def process_word(self, word: str) -> Optional[Dict]:
        """
        Process a word and extract all phonetic information.

        Args:
            word: The word to process

        Returns:
            Dictionary of phonetic data or None
        """
        arpabet = self.get_cmu_phones(word)

        if not arpabet:
            logger.debug(f"No phonetic data found for '{word}'")
            return None

        ipa = self.arpabet_to_ipa_convert(arpabet)
        stress_pattern = self.extract_stress_pattern(arpabet)
        syllable_count = self.count_syllables(arpabet)
        rhyme_key = self.extract_rhyme_key(arpabet)
        onset, nucleus, coda = self.extract_onset_nucleus_coda(arpabet)

        return {
            'lemma': word,
            'ipa_us_cmu': ipa,
            'ipa_dict_uk': None,  # Would come from external dictionary
            'ipa_dict_us': None,
            'stress_pattern': stress_pattern,
            'syllable_count': syllable_count,
            'rhyme_key': rhyme_key,
            'onset': onset,
            'nucleus': nucleus,
            'coda': coda
        }

    def process_from_rare_lexicon(self, limit: Optional[int] = None):
        """
        Process phonetics for words in rare_lexicon.

        Args:
            limit: Maximum number of words to process
        """
        with get_session() as session:
            from ..database import RareLexicon

            query = session.query(RareLexicon.lemma).outerjoin(
                Phonetics, RareLexicon.lemma == Phonetics.lemma
            ).filter(Phonetics.id.is_(None))

            if limit:
                query = query.limit(limit)

            words = [row[0] for row in query.all()]

        logger.info(f"Processing phonetics for {len(words)} words...")

        processed = 0
        failed = 0

        for word in tqdm(words, desc="Processing phonetics"):
            phonetic_data = self.process_word(word)

            if phonetic_data:
                with get_session() as session:
                    phonetics_entry = Phonetics(**phonetic_data)
                    session.add(phonetics_entry)
                processed += 1
            else:
                failed += 1

        logger.info(f"Phonetics processing complete: {processed} processed, {failed} failed")


def main():
    """Command-line interface for phonetics processing."""
    import argparse

    parser = argparse.ArgumentParser(description="Process word phonetics")
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of words to process'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    processor = IPAProcessor()
    processor.process_from_rare_lexicon(limit=args.limit)


if __name__ == "__main__":
    main()
