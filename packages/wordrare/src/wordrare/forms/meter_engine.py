"""
Meter engine for stress pattern validation and repair.

Handles:
- Meter validation (iambic, trochaic, anapestic, etc.)
- Syllable counting
- Stress pattern matching
- Line repair suggestions
"""

import re
import logging
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

from ..database import Phonetics, WordRecord, get_session

logger = logging.getLogger(__name__)


@dataclass
class MeterPattern:
    """Represents a meter pattern."""
    name: str
    foot_pattern: str  # e.g., "01" for iambic
    syllables_per_foot: int
    feet_per_line: int

    @property
    def expected_syllables(self) -> int:
        return self.syllables_per_foot * self.feet_per_line

    def get_expected_stress_pattern(self) -> str:
        """Get expected stress pattern for a complete line."""
        return self.foot_pattern * self.feet_per_line


# Common meter patterns
METER_PATTERNS = {
    'iambic_pentameter': MeterPattern('Iambic Pentameter', '01', 2, 5),  # 10 syllables
    'iambic_tetrameter': MeterPattern('Iambic Tetrameter', '01', 2, 4),  # 8 syllables
    'trochaic_tetrameter': MeterPattern('Trochaic Tetrameter', '10', 2, 4),  # 8 syllables
    'anapestic_tetrameter': MeterPattern('Anapestic Tetrameter', '001', 3, 4),  # 12 syllables
    'dactylic_hexameter': MeterPattern('Dactylic Hexameter', '100', 3, 6),  # 18 syllables
}


@dataclass
class LineAnalysis:
    """Results of meter analysis for a line."""
    line_text: str
    syllable_count: int
    stress_pattern: str
    meter_match: Optional[str]  # Name of matched meter
    foot_accuracy: float  # Proportion of correct feet
    syllable_deviation: int  # Deviation from expected
    stress_deviation: float  # Hamming distance normalized
    is_valid: bool


class MeterEngine:
    """Analyzes and repairs meter patterns."""

    def __init__(self):
        self.meter_patterns = METER_PATTERNS
        self.stress_tolerance = 0.2  # Allow 20% deviation

    def get_word_stress(self, word: str) -> Optional[str]:
        """
        Get stress pattern for a word.

        Args:
            word: The word

        Returns:
            Stress pattern string (e.g., "010") or None
        """
        with get_session() as session:
            phonetics = session.query(Phonetics).filter_by(lemma=word).first()

            if phonetics and phonetics.stress_pattern:
                return phonetics.stress_pattern

            # Try word_record as fallback
            word_record = session.query(WordRecord).filter_by(lemma=word).first()
            if word_record and word_record.stress_pattern:
                return word_record.stress_pattern

        return None

    def get_word_syllables(self, word: str) -> int:
        """
        Get syllable count for a word.

        Args:
            word: The word

        Returns:
            Syllable count
        """
        with get_session() as session:
            phonetics = session.query(Phonetics).filter_by(lemma=word).first()

            if phonetics and phonetics.syllable_count:
                return phonetics.syllable_count

            # Try word_record as fallback
            word_record = session.query(WordRecord).filter_by(lemma=word).first()
            if word_record and word_record.syllable_count:
                return word_record.syllable_count

        # Fallback: simple heuristic
        return self._estimate_syllables(word)

    def _estimate_syllables(self, word: str) -> int:
        """
        Estimate syllable count using simple heuristic.

        Args:
            word: The word

        Returns:
            Estimated syllable count
        """
        # Count vowel groups
        word = word.lower()
        vowels = 'aeiouy'
        syllable_count = 0
        previous_was_vowel = False

        for char in word:
            is_vowel = char in vowels

            if is_vowel and not previous_was_vowel:
                syllable_count += 1

            previous_was_vowel = is_vowel

        # Silent e
        if word.endswith('e'):
            syllable_count -= 1

        # Minimum 1 syllable
        return max(1, syllable_count)

    def analyze_line(self, line: str, target_meter: str = 'iambic_pentameter') -> LineAnalysis:
        """
        Analyze meter of a line.

        Args:
            line: Text of the line
            target_meter: Target meter pattern name

        Returns:
            LineAnalysis object
        """
        # Tokenize
        words = [w.lower().strip('.,!?;:\'"') for w in line.split()]
        words = [w for w in words if w]

        if not words:
            return LineAnalysis(
                line_text=line,
                syllable_count=0,
                stress_pattern='',
                meter_match=None,
                foot_accuracy=0.0,
                syllable_deviation=0,
                stress_deviation=1.0,
                is_valid=False
            )

        # Build stress pattern
        stress_pattern = ''
        total_syllables = 0

        for word in words:
            word_stress = self.get_word_stress(word)

            if word_stress:
                stress_pattern += word_stress
                total_syllables += len(word_stress)
            else:
                # Estimate syllables and use neutral stress
                syllables = self.get_word_syllables(word)
                stress_pattern += '0' * syllables
                total_syllables += syllables

        # Get target meter
        meter_pattern = self.meter_patterns.get(target_meter)

        if not meter_pattern:
            logger.warning(f"Unknown meter pattern: {target_meter}")
            return LineAnalysis(
                line_text=line,
                syllable_count=total_syllables,
                stress_pattern=stress_pattern,
                meter_match=None,
                foot_accuracy=0.0,
                syllable_deviation=0,
                stress_deviation=0.0,
                is_valid=False
            )

        # Compute metrics
        expected_syllables = meter_pattern.expected_syllables
        syllable_deviation = abs(total_syllables - expected_syllables)

        # Compute foot accuracy
        foot_accuracy = self._compute_foot_accuracy(
            stress_pattern,
            meter_pattern.foot_pattern,
            meter_pattern.feet_per_line
        )

        # Compute stress deviation (Hamming distance)
        expected_pattern = meter_pattern.get_expected_stress_pattern()
        stress_deviation = self._compute_stress_deviation(
            stress_pattern,
            expected_pattern
        )

        # Determine if valid
        is_valid = (
            syllable_deviation <= 1 and
            stress_deviation <= self.stress_tolerance
        )

        return LineAnalysis(
            line_text=line,
            syllable_count=total_syllables,
            stress_pattern=stress_pattern,
            meter_match=target_meter if is_valid else None,
            foot_accuracy=foot_accuracy,
            syllable_deviation=syllable_deviation,
            stress_deviation=stress_deviation,
            is_valid=is_valid
        )

    def _compute_foot_accuracy(self, stress_pattern: str,
                               foot_pattern: str, feet_count: int) -> float:
        """
        Compute proportion of feet matching target pattern.

        Args:
            stress_pattern: Actual stress pattern
            foot_pattern: Target foot pattern
            feet_count: Expected number of feet

        Returns:
            Foot accuracy (0.0 to 1.0)
        """
        foot_length = len(foot_pattern)
        matching_feet = 0

        for i in range(feet_count):
            start = i * foot_length
            end = start + foot_length

            if end <= len(stress_pattern):
                foot = stress_pattern[start:end]

                if foot == foot_pattern:
                    matching_feet += 1

        return matching_feet / feet_count if feet_count > 0 else 0.0

    def _compute_stress_deviation(self, actual: str, expected: str) -> float:
        """
        Compute normalized Hamming distance.

        Args:
            actual: Actual stress pattern
            expected: Expected stress pattern

        Returns:
            Normalized deviation (0.0 to 1.0)
        """
        if not actual or not expected:
            return 1.0

        # Pad shorter pattern
        max_len = max(len(actual), len(expected))
        actual = actual.ljust(max_len, '0')
        expected = expected.ljust(max_len, '0')

        # Compute Hamming distance
        mismatches = sum(a != e for a, e in zip(actual, expected))

        return mismatches / max_len if max_len > 0 else 0.0

    def suggest_repairs(self, line: str, target_meter: str = 'iambic_pentameter') -> List[str]:
        """
        Suggest repairs for a line with meter issues.

        Args:
            line: Original line
            target_meter: Target meter

        Returns:
            List of suggested repairs
        """
        analysis = self.analyze_line(line, target_meter)

        if analysis.is_valid:
            return []

        suggestions = []

        # Suggest based on deviation type
        if analysis.syllable_deviation > 0:
            suggestions.append(
                f"Remove {analysis.syllable_deviation} syllable(s) to match meter"
            )
        elif analysis.syllable_deviation < 0:
            suggestions.append(
                f"Add {abs(analysis.syllable_deviation)} syllable(s) to match meter"
            )

        if analysis.foot_accuracy < 0.6:
            suggestions.append(
                "Rearrange words to improve stress pattern"
            )

        # Generic suggestion
        if not suggestions:
            suggestions.append(
                "Adjust word choice to better match meter"
            )

        return suggestions

    def validate_stanza(self, lines: List[str],
                       target_meter: str = 'iambic_pentameter') -> List[LineAnalysis]:
        """
        Validate meter for all lines in a stanza.

        Args:
            lines: List of line texts
            target_meter: Target meter pattern

        Returns:
            List of LineAnalysis objects
        """
        analyses = []

        for line in lines:
            analysis = self.analyze_line(line, target_meter)
            analyses.append(analysis)

        return analyses


def main():
    """Command-line interface for meter engine."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze meter")
    parser.add_argument(
        '--line',
        type=str,
        help='Analyze meter of a line'
    )
    parser.add_argument(
        '--meter',
        type=str,
        default='iambic_pentameter',
        choices=list(METER_PATTERNS.keys()),
        help='Target meter pattern'
    )
    parser.add_argument(
        '--repair',
        action='store_true',
        help='Suggest repairs for the line'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    engine = MeterEngine()

    if args.line:
        analysis = engine.analyze_line(args.line, args.meter)

        print(f"\nLine: {analysis.line_text}")
        print(f"Syllables: {analysis.syllable_count}")
        print(f"Stress pattern: {analysis.stress_pattern}")
        print(f"Foot accuracy: {analysis.foot_accuracy:.2%}")
        print(f"Syllable deviation: {analysis.syllable_deviation}")
        print(f"Stress deviation: {analysis.stress_deviation:.2%}")
        print(f"Valid: {analysis.is_valid}")

        if args.repair and not analysis.is_valid:
            suggestions = engine.suggest_repairs(args.line, args.meter)
            print("\nRepair suggestions:")
            for suggestion in suggestions:
                print(f"  - {suggestion}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
