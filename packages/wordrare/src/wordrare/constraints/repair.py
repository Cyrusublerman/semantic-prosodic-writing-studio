"""
Conflict detection and repair strategies.

Implements repair strategies from BuildGuide Section 3.3.
"""

import logging
from typing import List, Optional, Dict, Tuple
from enum import Enum

from .constraint_model import Constraint, ConstraintModel, SteeringPolicy
from ..forms import MeterEngine, SoundEngine
from ..database import WordRecord, get_session

logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """Types of conflicts."""
    RHYME = "rhyme"
    METER = "meter"
    SEMANTIC = "semantic"
    COHERENCE = "coherence"


class RepairStrategy(Enum):
    """Repair strategies in priority order."""
    LOCAL_SUBSTITUTION = "local_substitution"
    SLANT_RHYME_TOLERANCE = "slant_rhyme_tolerance"
    RHYME_CLASS_PIVOT = "rhyme_class_pivot"
    METER_MICRO_EDITS = "meter_micro_edits"
    SEMANTIC_CORRECTION = "semantic_correction"
    COHERENCE_SMOOTHING = "coherence_smoothing"
    STRUCTURAL_RELAXATION = "structural_relaxation"


class ConflictDetector:
    """Detects conflicts in generated lines."""

    def __init__(self):
        self.constraint_model = ConstraintModel()
        self.meter_engine = MeterEngine()
        self.sound_engine = SoundEngine()

    def detect_conflict(self, line: str, target_spec: Dict) -> Optional[ConflictType]:
        """
        Detect primary conflict type in a line.

        Args:
            line: Generated line
            target_spec: Target specifications

        Returns:
            Primary conflict type or None
        """
        constraints = self.constraint_model.evaluate_line(line, target_spec)
        violated = self.constraint_model.get_violated_constraints(
            list(constraints.values())
        )

        if not violated:
            return None

        # Return highest-priority violation
        primary = violated[0]

        if primary.name == 'rhyme':
            return ConflictType.RHYME
        elif primary.name == 'meter':
            return ConflictType.METER
        elif primary.name == 'semantics':
            return ConflictType.SEMANTIC
        elif primary.name == 'coherence':
            return ConflictType.COHERENCE

        return ConflictType.METER  # Default


class LineRepairer:
    """Repairs lines using various strategies."""

    def __init__(self, policy: SteeringPolicy = None):
        """
        Initialize repairer.

        Args:
            policy: Steering policy (defaults to loose_tercet)
        """
        self.policy = policy or SteeringPolicy.loose_tercet()
        self.meter_engine = MeterEngine()
        self.sound_engine = SoundEngine()
        self.detector = ConflictDetector()

    def repair_line(self, line: str, target_spec: Dict,
                   conflict: ConflictType) -> Optional[str]:
        """
        Repair a line based on conflict type.

        Args:
            line: Original line
            target_spec: Target specifications
            conflict: Type of conflict

        Returns:
            Repaired line or None
        """
        strategies = self._select_strategies(conflict)

        for strategy in strategies:
            repaired = self._apply_strategy(line, target_spec, strategy)

            if repaired and repaired != line:
                # Verify repair improved the line
                new_conflict = self.detector.detect_conflict(repaired, target_spec)

                if new_conflict is None or new_conflict != conflict:
                    logger.debug(f"Repair successful using {strategy.value}")
                    return repaired

        return None

    def _select_strategies(self, conflict: ConflictType) -> List[RepairStrategy]:
        """Select appropriate repair strategies for conflict type."""
        if conflict == ConflictType.RHYME:
            strategies = [
                RepairStrategy.LOCAL_SUBSTITUTION,
            ]

            if self.policy.allow_slant:
                strategies.append(RepairStrategy.SLANT_RHYME_TOLERANCE)

            if self.policy.allow_pivot:
                strategies.append(RepairStrategy.RHYME_CLASS_PIVOT)

            return strategies

        elif conflict == ConflictType.METER:
            return [
                RepairStrategy.METER_MICRO_EDITS,
                RepairStrategy.LOCAL_SUBSTITUTION
            ]

        elif conflict == ConflictType.SEMANTIC:
            return [
                RepairStrategy.SEMANTIC_CORRECTION,
                RepairStrategy.LOCAL_SUBSTITUTION
            ]

        else:  # COHERENCE
            return [
                RepairStrategy.COHERENCE_SMOOTHING,
                RepairStrategy.LOCAL_SUBSTITUTION
            ]

    def _apply_strategy(self, line: str, target_spec: Dict,
                       strategy: RepairStrategy) -> Optional[str]:
        """Apply a specific repair strategy."""
        if strategy == RepairStrategy.LOCAL_SUBSTITUTION:
            return self._local_substitution(line, target_spec)

        elif strategy == RepairStrategy.SLANT_RHYME_TOLERANCE:
            # Accept slant rhyme - no change needed
            return line

        elif strategy == RepairStrategy.METER_MICRO_EDITS:
            return self._meter_micro_edits(line, target_spec)

        elif strategy == RepairStrategy.SEMANTIC_CORRECTION:
            return self._semantic_correction(line, target_spec)

        # Other strategies not yet implemented
        return None

    def _local_substitution(self, line: str, target_spec: Dict) -> Optional[str]:
        """
        Substitute words while maintaining rhyme/meter.

        Args:
            line: Original line
            target_spec: Target specifications

        Returns:
            Modified line or None
        """
        words = line.split()

        if not words:
            return None

        # Try substituting each word
        for i in range(len(words) - 1):  # Don't substitute rhyme word
            original_word = words[i]

            # Find synonym with similar syllable count
            syllables = self.meter_engine.get_word_syllables(original_word)

            # Query database for alternatives
            with get_session() as session:
                candidates = session.query(WordRecord).filter(
                    WordRecord.syllable_count == syllables,
                    WordRecord.pos_primary == self._guess_pos(original_word)
                ).limit(10).all()

            if not candidates:
                continue

            # Try each candidate
            for candidate in candidates:
                test_words = words.copy()
                test_words[i] = candidate.lemma
                test_line = ' '.join(test_words)

                # Check if this improves the line
                conflict = self.detector.detect_conflict(test_line, target_spec)

                if conflict is None:
                    return test_line

        return None

    def _meter_micro_edits(self, line: str, target_spec: Dict) -> Optional[str]:
        """
        Make small edits to improve meter.

        Args:
            line: Original line
            target_spec: Target specifications

        Returns:
            Modified line or None
        """
        # Analyze current meter
        analysis = self.meter_engine.analyze_line(
            line,
            target_spec.get('meter', 'iambic_pentameter')
        )

        # If too many syllables, try removing articles
        if analysis.syllable_count > analysis.meter_pattern.expected_syllables:
            words = line.split()

            # Remove articles
            filtered = [w for w in words if w.lower() not in ['the', 'a', 'an']]

            if len(filtered) < len(words):
                return ' '.join(filtered)

        # If too few syllables, try adding articles
        elif analysis.syllable_count < analysis.meter_pattern.expected_syllables:
            words = line.split()

            # Add article before first noun (simple heuristic)
            if words and words[0][0].isupper():
                return 'The ' + line

        return None

    def _semantic_correction(self, line: str, target_spec: Dict) -> Optional[str]:
        """
        Adjust semantic alignment.

        Args:
            line: Original line
            target_spec: Target specifications

        Returns:
            Modified line or None
        """
        # Placeholder - would implement semantic coherence checking
        # and word substitution to improve theme/affect alignment
        return None

    def _guess_pos(self, word: str) -> str:
        """Guess POS from word (simple heuristic)."""
        # Very simple heuristic
        if word.endswith('ly'):
            return 'adverb'
        elif word.endswith('ing'):
            return 'verb'
        elif word.endswith('ed'):
            return 'verb'
        else:
            return 'noun'


class IterativeRepairer:
    """Performs iterative repair with scoring."""

    def __init__(self, policy: SteeringPolicy = None):
        """
        Initialize iterative repairer.

        Args:
            policy: Steering policy
        """
        self.policy = policy or SteeringPolicy.loose_tercet()
        self.detector = ConflictDetector()
        self.repairer = LineRepairer(policy)
        self.constraint_model = ConstraintModel()

    def repair_with_iterations(self, line: str, target_spec: Dict) -> str:
        """
        Iteratively repair line until acceptable or max iterations.

        Implements the iteration loop from BuildGuide Section 3.5.

        Args:
            line: Original line
            target_spec: Target specifications

        Returns:
            Best line found
        """
        L0 = line
        constraints0 = self.constraint_model.evaluate_line(L0, target_spec)
        score0 = self.constraint_model.compute_utility(list(constraints0.values()))

        # Check if already acceptable
        if score0 >= 0.8:
            return L0

        best_line = L0
        best_score = score0

        # Iteration loop
        for iteration in range(self.policy.max_repairs):
            conflict = self.detector.detect_conflict(best_line, target_spec)

            if conflict is None:
                # No conflict - accept
                return best_line

            # Attempt repair
            L1 = self.repairer.repair_line(best_line, target_spec, conflict)

            if L1 is None:
                # Repair failed - keep current best
                break

            # Evaluate repaired line
            constraints1 = self.constraint_model.evaluate_line(L1, target_spec)
            score1 = self.constraint_model.compute_utility(list(constraints1.values()))

            # Accept if improved
            if score1 >= best_score:
                best_line = L1
                best_score = score1
                logger.debug(f"Iteration {iteration+1}: score improved to {score1:.2f}")
            else:
                # No improvement - stop
                break

        return best_line


def main():
    """CLI for repair testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Conflict detection and repair")
    parser.add_argument(
        '--line',
        type=str,
        required=True,
        help='Line to repair'
    )
    parser.add_argument(
        '--meter',
        type=str,
        default='iambic_pentameter',
        help='Target meter'
    )
    parser.add_argument(
        '--rhyme-word',
        type=str,
        help='Word to rhyme with'
    )
    parser.add_argument(
        '--policy',
        choices=['strict', 'loose', 'free'],
        default='loose',
        help='Steering policy'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    # Select policy
    if args.policy == 'strict':
        policy = SteeringPolicy.strict_sonnet()
    elif args.policy == 'free':
        policy = SteeringPolicy.free_verse()
    else:
        policy = SteeringPolicy.loose_tercet()

    # Build target spec
    target_spec = {'meter': args.meter}
    if args.rhyme_word:
        target_spec['rhyme_word'] = args.rhyme_word

    # Detect conflict
    detector = ConflictDetector()
    conflict = detector.detect_conflict(args.line, target_spec)

    print(f"\nOriginal: '{args.line}'")
    print(f"Conflict: {conflict.value if conflict else 'None'}")

    if conflict:
        # Attempt repair
        repairer = IterativeRepairer(policy)
        repaired = repairer.repair_with_iterations(args.line, target_spec)

        print(f"Repaired: '{repaired}'")

        # Show improvement
        model = ConstraintModel()

        orig_constraints = model.evaluate_line(args.line, target_spec)
        orig_score = model.compute_utility(list(orig_constraints.values()))

        rep_constraints = model.evaluate_line(repaired, target_spec)
        rep_score = model.compute_utility(list(rep_constraints.values()))

        print(f"\nScore: {orig_score:.2f} → {rep_score:.2f}")


if __name__ == "__main__":
    main()
