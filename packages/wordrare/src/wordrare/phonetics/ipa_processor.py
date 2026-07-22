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

VOWELS = frozenset({
    "AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
    "IH", "IY", "OW", "OY", "UH", "UW",
})


def _clean_phone(phone: str) -> str:
    return re.sub(r"[012]", "", phone)


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

    def syllabify_arpabet(self, arpabet: List[str]) -> List[List[str]]:
        """
        Split ARPAbet into syllables (vowel nuclei + maximal onset).

        Each vowel phone starts a syllable. Intervocalic consonants: keep
        at most one coda on the previous syllable; remainder as next onset.
        """
        if not arpabet:
            return []
        return self._syllabify_sequential(arpabet)

    def _syllabify_sequential(self, arpabet: List[str]) -> List[List[str]]:
        """Deterministic syllabify: split before each vowel after the first."""
        vowel_idxs = [
            i for i, p in enumerate(arpabet) if _clean_phone(p) in VOWELS
        ]
        if not vowel_idxs:
            return [list(arpabet)]

        # Boundaries: for each vowel after first, place cut so onset gets
        # all but at most one coda consonant from the preceding cluster.
        cuts = [0]
        for vi in range(1, len(vowel_idxs)):
            prev_v = vowel_idxs[vi - 1]
            cur_v = vowel_idxs[vi]
            cluster_len = cur_v - prev_v - 1
            if cluster_len <= 0:
                cut = cur_v
            elif cluster_len == 1:
                cut = cur_v  # consonant as onset
            else:
                cut = prev_v + 2  # one coda, rest onset
            cuts.append(cut)
        cuts.append(len(arpabet))

        return [list(arpabet[cuts[i] : cuts[i + 1]]) for i in range(len(cuts) - 1)]

    def syllable_rhyme_key(self, syl_phones: List[str], mode: str = "perfect") -> str:
        """Key for one syllable: nucleus→coda (perfect) or nucleus only (assonance)."""
        if not syl_phones:
            return ""
        vidx = -1
        for i, p in enumerate(syl_phones):
            if _clean_phone(p) in VOWELS:
                vidx = i
                break
        if vidx < 0:
            return " ".join(_clean_phone(p) for p in syl_phones)
        if mode == "assonance":
            return _clean_phone(syl_phones[vidx])
        return " ".join(_clean_phone(p) for p in syl_phones[vidx:])

    def span_rhyme_key(
        self,
        arpabet: List[str],
        syl_start: int,
        syl_end: int,
        mode: str = "perfect",
    ) -> str:
        """Joined syllable keys for syllables [syl_start, syl_end)."""
        syls = self.syllabify_arpabet(arpabet)
        if not syls:
            return ""
        syl_start = max(0, syl_start)
        syl_end = min(len(syls), syl_end)
        if syl_start >= syl_end:
            return ""
        parts = [
            self.syllable_rhyme_key(syls[i], mode=mode) for i in range(syl_start, syl_end)
        ]
        return " | ".join(p for p in parts if p)

    def end_span_key(
        self, arpabet: List[str], n: int = 1, mode: str = "perfect"
    ) -> str:
        """Rhyme key over the last n syllables."""
        syls = self.syllabify_arpabet(arpabet)
        if not syls:
            return ""
        n = max(1, min(n, len(syls)))
        return self.span_rhyme_key(arpabet, len(syls) - n, len(syls), mode=mode)

    def line_span_key(self, arpabet: List[str], mode: str = "perfect") -> str:
        """Rhyme key over all syllables (whole word/line phone sequence)."""
        syls = self.syllabify_arpabet(arpabet)
        if not syls:
            return ""
        return self.span_rhyme_key(arpabet, 0, len(syls), mode=mode)

    def extract_rhyme_key(self, arpabet: List[str]) -> str:
        """
        Extract rhyme key (final stressed syllable + coda).

        Equivalent to classic CMU end-rhyme; also matches end_span_key(n=1)
        when the last syllable begins at the last stress.
        """
        # Find the last stressed vowel
        last_stress_idx = -1

        for i, phone in enumerate(arpabet):
            if '1' in phone or '2' in phone:
                last_stress_idx = i

        if last_stress_idx == -1:
            # No stress marker - use last vowel
            for i in range(len(arpabet) - 1, -1, -1):
                clean = _clean_phone(arpabet[i])
                if clean in VOWELS:
                    last_stress_idx = i
                    break

        if last_stress_idx == -1:
            return ''

        # Rhyme key is from stressed vowel to end
        rhyme_phones = arpabet[last_stress_idx:]
        # Remove stress markers for comparison
        rhyme_key = ' '.join(_clean_phone(p) for p in rhyme_phones)

        return rhyme_key

    def estimate_oov(self, word: str) -> Dict:
        """Heuristic phonetics for lemmas missing from CMU."""
        w = re.sub(r"[^a-z]", "", word.lower())
        if not w:
            w = "x"
        # crude syllable estimate by vowel groups
        groups = re.findall(r"[aeiouy]+", w)
        syl = max(1, len(groups))
        stress = ("0" * (syl - 1)) + "1"
        # fake phones: AH per syllable
        phones = []
        for i in range(syl):
            phones.append("AH1" if i == syl - 1 else "AH0")
        return {
            "lemma": word.lower(),
            "ipa_us_cmu": None,
            "ipa_dict_uk": None,
            "ipa_dict_us": None,
            "stress_pattern": stress,
            "syllable_count": syl,
            "rhyme_key": self.extract_rhyme_key(phones) or "AH",
            "onset": "",
            "nucleus": "AH",
            "coda": "",
            "syllable_phones": self.syllabify_arpabet(phones),
            "syllable_keys": [
                self.syllable_rhyme_key(s) for s in self.syllabify_arpabet(phones)
            ],
            "assonance_keys": [
                self.syllable_rhyme_key(s, mode="assonance")
                for s in self.syllabify_arpabet(phones)
            ],
            "end_keys": {
                "1": self.end_span_key(phones, 1),
                "2": self.end_span_key(phones, 2),
                "3": self.end_span_key(phones, 3),
            },
            "phonetic_source": "estimated",
        }

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
            return self.estimate_oov(word)

        ipa = self.arpabet_to_ipa_convert(arpabet)
        stress_pattern = self.extract_stress_pattern(arpabet)
        syllable_count = self.count_syllables(arpabet)
        rhyme_key = self.extract_rhyme_key(arpabet)
        onset, nucleus, coda = self.extract_onset_nucleus_coda(arpabet)
        syl_phones = self.syllabify_arpabet(arpabet)
        syllable_keys = [self.syllable_rhyme_key(s) for s in syl_phones]
        assonance_keys = [
            self.syllable_rhyme_key(s, mode="assonance") for s in syl_phones
        ]
        end_keys = {
            "1": self.end_span_key(arpabet, 1),
            "2": self.end_span_key(arpabet, 2),
            "3": self.end_span_key(arpabet, 3),
        }

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
            'coda': coda,
            'syllable_phones': syl_phones,
            'syllable_keys': syllable_keys,
            'assonance_keys': assonance_keys,
            'end_keys': end_keys,
            'phonetic_source': 'cmu',
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
                payload = {
                    k: v
                    for k, v in phonetic_data.items()
                    if k
                    in {
                        "lemma",
                        "ipa_us_cmu",
                        "ipa_dict_uk",
                        "ipa_dict_us",
                        "stress_pattern",
                        "syllable_count",
                        "rhyme_key",
                        "onset",
                        "nucleus",
                        "coda",
                        "syllable_phones",
                        "syllable_keys",
                        "assonance_keys",
                        "end_keys",
                    }
                }
                with get_session() as session:
                    phonetics_entry = Phonetics(**payload)
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
