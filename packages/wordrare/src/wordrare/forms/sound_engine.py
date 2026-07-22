"""
Sound engine for rhyme classification and sound devices.

Handles:
- Rhyme detection (perfect, slant, internal)
- Alliteration detection
- Assonance detection
- Consonance detection
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass

from ..database import Phonetics, WordRecord, get_session
from ..phonetics.ipa_processor import IPAProcessor

logger = logging.getLogger(__name__)


@dataclass
class RhymeMatch:
    """Represents a rhyme match between two words."""
    word1: str
    word2: str
    rhyme_type: str  # 'perfect', 'slant', 'assonance', 'consonance'
    similarity: float  # 0.0 to 1.0


@dataclass
class LineSyllable:
    """One syllable aligned on a line."""
    lemma: str
    word_syl_i: int
    line_syl_i: int
    phones: List[str]
    key: str


class SoundEngine:
    """Analyzes and detects sound patterns in words."""

    def __init__(self):
        # Thresholds for rhyme classification
        self.perfect_rhyme_threshold = 0.95
        self.slant_rhyme_threshold = 0.7
        self._ipa = IPAProcessor()
        self._syl_cache: Dict[str, List[List[str]]] = {}

    def get_rhyme_key(self, word: str) -> Optional[str]:
        """
        Get rhyme key for a word from database.

        Args:
            word: The word

        Returns:
            Rhyme key or None
        """
        with get_session() as session:
            phonetics = session.query(Phonetics).filter_by(lemma=word).first()

            if phonetics:
                return phonetics.rhyme_key

            # Try word_record as fallback
            word_record = session.query(WordRecord).filter_by(lemma=word).first()
            if word_record:
                return word_record.rhyme_key

        # Runtime CMU fallback
        phones = self._ipa.get_cmu_phones(word)
        if phones:
            return self._ipa.extract_rhyme_key(phones)
        return None

    def get_word_syllables_phones(self, lemma: str) -> List[List[str]]:
        """Syllabified ARPAbet for a lemma (cached)."""
        key = lemma.lower().strip(".,!?;:\"'")
        if key in self._syl_cache:
            return self._syl_cache[key]
        with get_session() as session:
            phon = session.query(Phonetics).filter_by(lemma=key).first()
            if phon and phon.syllable_phones:
                self._syl_cache[key] = phon.syllable_phones
                return phon.syllable_phones
        phones = self._ipa.get_cmu_phones(key)
        if not phones:
            est = self._ipa.estimate_oov(key)
            syls = est.get("syllable_phones") or []
            self._syl_cache[key] = syls
            return syls
        syls = self._ipa.syllabify_arpabet(phones)
        self._syl_cache[key] = syls
        return syls

    def get_end_span_key(self, lemma: str, n: int = 1, mode: str = "perfect") -> str:
        phones = self._ipa.get_cmu_phones(lemma)
        if not phones:
            syls = self.get_word_syllables_phones(lemma)
            flat = [p for s in syls for p in s]
            phones = flat
        if not phones:
            return ""
        if n <= 0:
            return self._ipa.line_span_key(phones, mode=mode)
        return self._ipa.end_span_key(phones, n=n, mode=mode)

    def get_span_key(
        self, lemma: str, syl_start: int, syl_end: int, mode: str = "perfect"
    ) -> str:
        phones = self._ipa.get_cmu_phones(lemma)
        if not phones:
            syls = self.get_word_syllables_phones(lemma)
            phones = [p for s in syls for p in s]
        if not phones:
            return ""
        return self._ipa.span_rhyme_key(phones, syl_start, syl_end, mode=mode)

    def align_line_syllables(
        self, tokens: List[str], mode: str = "perfect"
    ) -> List[LineSyllable]:
        """Map tokens to line-level syllable indices."""
        out: List[LineSyllable] = []
        line_i = 0
        for tok in tokens:
            lemma = tok.lower().strip(".,!?;:\"'")
            if not lemma:
                continue
            syls = self.get_word_syllables_phones(lemma)
            if not syls:
                syls = [[]]
            for wi, phones in enumerate(syls):
                key = self._ipa.syllable_rhyme_key(phones, mode=mode) if phones else ""
                out.append(
                    LineSyllable(
                        lemma=lemma,
                        word_syl_i=wi,
                        line_syl_i=line_i,
                        phones=list(phones),
                        key=key,
                    )
                )
                line_i += 1
        return out

    def line_span_key(
        self,
        tokens: List[str],
        syl_start: int = 0,
        syl_end: Optional[int] = None,
        mode: str = "perfect",
    ) -> str:
        aligned = self.align_line_syllables(tokens, mode=mode)
        if not aligned:
            return ""
        end = syl_end if syl_end is not None else len(aligned)
        parts = [
            a.key
            for a in aligned
            if syl_start <= a.line_syl_i < end and a.key
        ]
        return " | ".join(parts)

    def compare_span(self, key_a: str, key_b: str, mode: str = "perfect") -> float:
        if not key_a or not key_b:
            return 0.0
        if key_a == key_b:
            return 1.0
        if mode == "assonance":
            # compare nuclei only (already nucleus if mode used at extract)
            return 1.0 if key_a == key_b else self.compute_rhyme_similarity(
                key_a.replace(" | ", " "), key_b.replace(" | ", " ")
            )
        return self.compute_rhyme_similarity(
            key_a.replace(" | ", " "), key_b.replace(" | ", " ")
        )

    def compute_rhyme_similarity(self, rhyme_key1: str, rhyme_key2: str) -> float:
        """
        Compute similarity between two rhyme keys.

        Args:
            rhyme_key1: First rhyme key
            rhyme_key2: Second rhyme key

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not rhyme_key1 or not rhyme_key2:
            return 0.0

        # Convert to phone sequences
        phones1 = rhyme_key1.split()
        phones2 = rhyme_key2.split()

        if not phones1 or not phones2:
            return 0.0

        # Exact match
        if rhyme_key1 == rhyme_key2:
            return 1.0

        # Compute Levenshtein-based similarity
        # Simple version: count matching phones from the end
        matches = 0
        max_len = min(len(phones1), len(phones2))

        for i in range(1, max_len + 1):
            if phones1[-i] == phones2[-i]:
                matches += 1
            else:
                break

        similarity = matches / max(len(phones1), len(phones2))

        return similarity

    def check_rhyme(self, word1: str, word2: str) -> Optional[RhymeMatch]:
        """
        Check if two words rhyme.

        Args:
            word1: First word
            word2: Second word

        Returns:
            RhymeMatch object or None
        """
        rhyme_key1 = self.get_rhyme_key(word1)
        rhyme_key2 = self.get_rhyme_key(word2)

        if not rhyme_key1 or not rhyme_key2:
            return None

        similarity = self.compute_rhyme_similarity(rhyme_key1, rhyme_key2)

        if similarity >= self.perfect_rhyme_threshold:
            rhyme_type = 'perfect'
        elif similarity >= self.slant_rhyme_threshold:
            rhyme_type = 'slant'
        else:
            # Check for assonance/consonance
            rhyme_type = self._analyze_partial_rhyme(word1, word2)

            if rhyme_type is None:
                return None

        return RhymeMatch(
            word1=word1,
            word2=word2,
            rhyme_type=rhyme_type,
            similarity=similarity
        )

    def _analyze_partial_rhyme(self, word1: str, word2: str) -> Optional[str]:
        """
        Analyze partial rhyme (assonance/consonance).

        Returns:
            Rhyme type or None
        """
        k1 = self.get_end_span_key(word1, 1, mode="assonance")
        k2 = self.get_end_span_key(word2, 1, mode="assonance")
        if k1 and k2 and k1 == k2:
            return "assonance"

        with get_session() as session:
            p1 = session.query(Phonetics).filter_by(lemma=word1.lower()).first()
            p2 = session.query(Phonetics).filter_by(lemma=word2.lower()).first()
            c1 = (p1.coda if p1 else "") or ""
            c2 = (p2.coda if p2 else "") or ""
            if c1 and c2 and c1 == c2:
                return "consonance"
        return None

    def find_rhymes(self, word: str, candidate_words: List[str],
                   rhyme_type: str = 'any') -> List[RhymeMatch]:
        """
        Find rhyming words from a list of candidates.

        Args:
            word: Target word
            candidate_words: List of candidate words
            rhyme_type: Type of rhyme to find ('perfect', 'slant', 'any')

        Returns:
            List of RhymeMatch objects
        """
        matches = []

        for candidate in candidate_words:
            if candidate == word:
                continue

            match = self.check_rhyme(word, candidate)

            if match:
                if rhyme_type == 'any':
                    matches.append(match)
                elif match.rhyme_type == rhyme_type:
                    matches.append(match)

        # Sort by similarity
        matches.sort(key=lambda m: m.similarity, reverse=True)

        return matches

    def check_alliteration(self, words: List[str]) -> bool:
        """
        Check if words exhibit alliteration.

        Args:
            words: List of words to check

        Returns:
            True if alliteration detected
        """
        if len(words) < 2:
            return False

        with get_session() as session:
            # Get onset (initial consonant cluster) for each word
            onsets = []

            for word in words:
                phonetics = session.query(Phonetics).filter_by(lemma=word).first()

                if phonetics and phonetics.onset:
                    onsets.append(phonetics.onset)
                else:
                    # Fallback to first letter
                    onsets.append(word[0].lower() if word else '')

        # Check if onsets match
        if not onsets:
            return False

        first_onset = onsets[0]

        # Allow partial matching (first phone/letter)
        first_phone = first_onset.split()[0] if ' ' in first_onset else first_onset

        for onset in onsets[1:]:
            onset_phone = onset.split()[0] if ' ' in onset else onset

            if onset_phone == first_phone:
                continue
            else:
                return False

        return True

    def check_assonance(self, words: List[str]) -> bool:
        """
        Check if words exhibit assonance (vowel repetition).

        Args:
            words: List of words to check

        Returns:
            True if assonance detected
        """
        if len(words) < 2:
            return False

        with get_session() as session:
            # Get nucleus (vowel sounds) for each word
            nuclei = []

            for word in words:
                phonetics = session.query(Phonetics).filter_by(lemma=word).first()

                if phonetics and phonetics.nucleus:
                    nuclei.append(phonetics.nucleus)

        if len(nuclei) < 2:
            return False

        # Check for common vowel sounds
        # Extract individual vowel phones
        vowel_sets = []

        for nucleus in nuclei:
            vowels = set(nucleus.split())
            vowel_sets.append(vowels)

        # Check for intersection
        common_vowels = vowel_sets[0]

        for vs in vowel_sets[1:]:
            common_vowels = common_vowels & vs

        return len(common_vowels) > 0

    def check_consonance(self, words: List[str]) -> bool:
        """
        Check if words exhibit consonance (consonant repetition).

        Args:
            words: List of words to check

        Returns:
            True if consonance detected
        """
        if len(words) < 2:
            return False

        with get_session() as session:
            # Get coda (final consonants) for each word
            codas = []

            for word in words:
                phonetics = session.query(Phonetics).filter_by(lemma=word).first()

                if phonetics and phonetics.coda:
                    codas.append(phonetics.coda)

        if len(codas) < 2:
            return False

        # Check for common consonant sounds
        consonant_sets = []

        for coda in codas:
            consonants = set(coda.split())
            consonant_sets.append(consonants)

        # Check for intersection
        common_consonants = consonant_sets[0]

        for cs in consonant_sets[1:]:
            common_consonants = common_consonants & cs

        return len(common_consonants) > 0

    def analyze_sound_devices(self, line: str) -> Dict[str, bool]:
        """
        Analyze a line for various sound devices.

        Args:
            line: Text of the line

        Returns:
            Dictionary of detected sound devices
        """
        # Tokenize (simple word splitting)
        words = [w.lower().strip('.,!?;:') for w in line.split()]
        words = [w for w in words if w]

        if len(words) < 2:
            return {
                'alliteration': False,
                'assonance': False,
                'consonance': False
            }

        # Check consecutive word pairs for devices
        has_alliteration = False
        has_assonance = False
        has_consonance = False

        for i in range(len(words) - 1):
            pair = [words[i], words[i + 1]]

            if self.check_alliteration(pair):
                has_alliteration = True

            if self.check_assonance(pair):
                has_assonance = True

            if self.check_consonance(pair):
                has_consonance = True

        return {
            'alliteration': has_alliteration,
            'assonance': has_assonance,
            'consonance': has_consonance
        }


def main():
    """Command-line interface for sound engine."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze sound patterns")
    parser.add_argument(
        '--rhyme',
        nargs=2,
        metavar=('WORD1', 'WORD2'),
        help='Check if two words rhyme'
    )
    parser.add_argument(
        '--find-rhymes',
        type=str,
        metavar='WORD',
        help='Find rhyming words (requires word list)'
    )
    parser.add_argument(
        '--alliteration',
        nargs='+',
        help='Check alliteration in words'
    )
    parser.add_argument(
        '--analyze-line',
        type=str,
        help='Analyze sound devices in a line'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    engine = SoundEngine()

    if args.rhyme:
        word1, word2 = args.rhyme
        match = engine.check_rhyme(word1, word2)

        if match:
            print(f"\n'{word1}' and '{word2}' rhyme:")
            print(f"  Type: {match.rhyme_type}")
            print(f"  Similarity: {match.similarity:.3f}")
        else:
            print(f"\n'{word1}' and '{word2}' do not rhyme")

    elif args.find_rhymes:
        # This would need a word list - placeholder
        print("Find-rhymes requires a word list (not implemented in CLI)")

    elif args.alliteration:
        has_alliteration = engine.check_alliteration(args.alliteration)
        print(f"\nAlliteration: {has_alliteration}")

    elif args.analyze_line:
        devices = engine.analyze_sound_devices(args.analyze_line)
        print(f"\nSound devices in line:")
        for device, present in devices.items():
            print(f"  {device}: {present}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
