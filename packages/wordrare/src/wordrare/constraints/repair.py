"""
Conflict detection and repair strategies.

Implements repair strategies from BuildGuide Section 3.3.
"""

import logging
from typing import List, Optional, Dict, Tuple
from enum import Enum

from .constraint_model import Constraint, ConstraintModel, SteeringPolicy
from ..forms import MeterEngine, SoundEngine
from ..forms.grammar_engine import choose_indefinite_article, resolve_articles
from ..forms.meter_engine import expected_stress_bits, stress_fit_score
from ..database import WordRecord, get_session

logger = logging.getLogger(__name__)

_FUNCTION_WORDS = frozenset({
    "the", "a", "an", "of", "to", "in", "on", "at", "for", "and", "or", "but", "with",
})


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
        # (class_id, new_key, surface) when RHYME_CLASS_PIVOT succeeds
        self.last_pivot: Optional[Tuple[str, str, str]] = None

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
        self.last_pivot = None
        strategies = self._select_strategies(conflict)

        for strategy in strategies:
            repaired = self._apply_strategy(line, target_spec, strategy)

            if repaired and repaired != line:
                repaired = " ".join(resolve_articles(repaired.split()))
                # Verify repair improved the line
                new_conflict = self.detector.detect_conflict(repaired, target_spec)

                if new_conflict is None or new_conflict != conflict:
                    logger.debug(f"Repair successful using {strategy.value}")
                    return repaired
                # Pivot always accepted when it produced a line + signal
                if strategy == RepairStrategy.RHYME_CLASS_PIVOT and self.last_pivot:
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

            if self.policy.allow_breaks:
                strategies.append(RepairStrategy.STRUCTURAL_RELAXATION)

            return strategies

        elif conflict == ConflictType.METER:
            strats = [
                RepairStrategy.METER_MICRO_EDITS,
                RepairStrategy.LOCAL_SUBSTITUTION,
            ]
            if self.policy.allow_breaks:
                strats.append(RepairStrategy.STRUCTURAL_RELAXATION)
            return strats

        elif conflict == ConflictType.SEMANTIC:
            return [
                RepairStrategy.SEMANTIC_CORRECTION,
                RepairStrategy.COHERENCE_SMOOTHING,
                RepairStrategy.LOCAL_SUBSTITUTION,
            ]

        else:  # COHERENCE
            return [
                RepairStrategy.COHERENCE_SMOOTHING,
                RepairStrategy.LOCAL_SUBSTITUTION,
            ]

    def _apply_strategy(self, line: str, target_spec: Dict,
                       strategy: RepairStrategy) -> Optional[str]:
        """Apply a specific repair strategy."""
        if strategy == RepairStrategy.LOCAL_SUBSTITUTION:
            return self._local_substitution(line, target_spec)

        elif strategy == RepairStrategy.SLANT_RHYME_TOLERANCE:
            return self._slant_rhyme_tolerance(line, target_spec)

        elif strategy == RepairStrategy.RHYME_CLASS_PIVOT:
            return self._rhyme_class_pivot(line, target_spec)

        elif strategy == RepairStrategy.METER_MICRO_EDITS:
            return self._meter_micro_edits(line, target_spec)

        elif strategy == RepairStrategy.SEMANTIC_CORRECTION:
            return self._semantic_correction(line, target_spec)

        elif strategy == RepairStrategy.COHERENCE_SMOOTHING:
            return self._coherence_smoothing(line, target_spec)

        elif strategy == RepairStrategy.STRUCTURAL_RELAXATION:
            return self._structural_relaxation(line, target_spec)

        return None

    def _slant_rhyme_tolerance(self, line: str, target_spec: Dict) -> Optional[str]:
        """Replace end token with a slant match to the rhyme anchor."""
        rhyme_word = (target_spec.get("rhyme_word") or "").lower()
        if not rhyme_word:
            return None
        words = line.split()
        if not words:
            return None
        end = words[-1].lower().strip(".,!?;:")
        if end == rhyme_word:
            return None
        match = self.sound_engine.check_rhyme(rhyme_word, end)
        if match and match.similarity >= self.sound_engine.slant_rhyme_threshold:
            return line  # already slant-ok
        syll = self.meter_engine.get_word_syllables(end)
        pos = self._guess_pos(end)
        candidates: List[str] = []
        with get_session() as session:
            rows = (
                session.query(WordRecord)
                .filter(
                    WordRecord.syllable_count == syll,
                    WordRecord.pos_primary == pos,
                    WordRecord.lemma != end,
                    WordRecord.lemma != rhyme_word,
                )
                .limit(40)
                .all()
            )
            candidates = [rec.lemma for rec in rows]
        for lemma in candidates:
            m = self.sound_engine.check_rhyme(rhyme_word, lemma)
            if m and m.similarity >= self.sound_engine.slant_rhyme_threshold:
                if m.rhyme_type in ("slant", "perfect", "assonance"):
                    trial = words[:-1] + [lemma]
                    return " ".join(trial)
        return None

    def _rhyme_class_pivot(self, line: str, target_spec: Dict) -> Optional[str]:
        """
        Establish a new end/span anchor; signal realizer via last_pivot.
        Returns changed line when end token is replaced with a fresh cohort member.
        """
        words = line.split()
        if not words:
            return None
        class_id = target_spec.get("rhyme_class") or target_spec.get("rhyme_symbol")
        if not class_id:
            return None
        end = words[-1].lower().strip(".,!?;:")
        syll = self.meter_engine.get_word_syllables(end)
        pos = self._guess_pos(end)
        banned = {end}
        rw = (target_spec.get("rhyme_word") or "").lower()
        if rw:
            banned.add(rw)
        by_key: Dict[str, List[str]] = {}
        with get_session() as session:
            rows = (
                session.query(WordRecord)
                .filter(
                    WordRecord.syllable_count == syll,
                    WordRecord.pos_primary == pos,
                    WordRecord.rhyme_key.isnot(None),
                )
                .limit(60)
                .all()
            )
            for rec in rows:
                if rec.lemma.lower() in banned:
                    continue
                by_key.setdefault(rec.rhyme_key, []).append(rec.lemma)
        multi = [(k, v) for k, v in by_key.items() if len(v) >= 2]
        pool = multi or list(by_key.items())
        if not pool:
            return None
        key, lemmas = pool[0]
        new_end = lemmas[0]
        if new_end.lower() == end:
            return None
        trial = words[:-1] + [new_end]
        surface = new_end
        self.last_pivot = (str(class_id), key, surface)
        return " ".join(trial)

    def _coherence_smoothing(self, line: str, target_spec: Dict) -> Optional[str]:
        """Replace an outlier content word toward palette pool."""
        palette = target_spec.get("palette_lemmas") or target_spec.get("semantic_palette") or []
        if isinstance(palette, dict):
            lemmas: List[str] = []
            for v in palette.values():
                lemmas.extend(list(v)[:8])
            palette = lemmas
        palette = [str(p) for p in palette if p]
        if not palette:
            return None
        words = line.split()
        if len(words) < 2:
            return None
        closed = _FUNCTION_WORDS
        # Find content word not in palette (prefer non-final)
        idxs = [
            i
            for i, w in enumerate(words[:-1])
            if w.lower().strip(".,!?;:") not in closed
            and w.lower().strip(".,!?;:") not in {p.lower() for p in palette}
        ]
        if not idxs:
            return None
        i = idxs[len(idxs) // 2]
        orig = words[i].lower().strip(".,!?;:")
        syll = self.meter_engine.get_word_syllables(orig)
        for seed in palette:
            if seed.lower() == orig:
                continue
            if self.meter_engine.get_word_syllables(seed) == syll:
                trial = words.copy()
                trial[i] = seed
                return " ".join(trial)
        # Syllable-mismatched last resort (non-final only)
        trial = words.copy()
        trial[i] = palette[0]
        return " ".join(trial)

    def _structural_relaxation(self, line: str, target_spec: Dict) -> Optional[str]:
        """Drop an optional/function word or shorten when policy.allow_breaks."""
        if not (self.policy.allow_breaks or target_spec.get("allow_breaks")):
            return None
        words = line.split()
        if len(words) < 3:
            return None
        target_syl = target_spec.get("target_syllables")
        # Prefer dropping a medial article/preposition (never final token)
        for i in range(len(words) - 1):
            w = words[i].lower().strip(".,!?;:")
            if w in {"the", "a", "an", "of", "in", "on", "to"}:
                trial = words[:i] + words[i + 1 :]
                if target_syl:
                    n = sum(self.meter_engine.get_word_syllables(x) for x in trial)
                    if abs(n - int(target_syl)) <= abs(
                        sum(self.meter_engine.get_word_syllables(x) for x in words)
                        - int(target_syl)
                    ):
                        return " ".join(trial)
                else:
                    return " ".join(trial)
        # Drop first non-final adjective-ish long word
        for i in range(len(words) - 1):
            w = words[i].lower().strip(".,!?;:")
            if w not in _FUNCTION_WORDS and self.meter_engine.get_word_syllables(w) >= 2:
                return " ".join(words[:i] + words[i + 1 :])
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

        banned_end = None
        rhyme_word = (target_spec.get("rhyme_word") or "").lower()
        if rhyme_word:
            banned_end = rhyme_word

        # Prefer substituting non-final words; final word may change only if not
        # identical to the rhyme anchor.
        for i in range(len(words)):
            original_word = words[i]
            syllables = self.meter_engine.get_word_syllables(original_word)

            with get_session() as session:
                rows = session.query(WordRecord).filter(
                    WordRecord.syllable_count == syllables,
                    WordRecord.pos_primary == self._guess_pos(original_word),
                    WordRecord.lemma != original_word.lower(),
                ).limit(10).all()
                candidate_lemmas = [r.lemma for r in rows]

            if not candidate_lemmas:
                continue

            for lemma in candidate_lemmas:
                if i == len(words) - 1 and banned_end and lemma.lower() == banned_end:
                    continue
                test_words = words.copy()
                test_words[i] = lemma
                test_line = " ".join(test_words)
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
        meter_name = target_spec.get('meter', 'iambic_pentameter')
        target_syllables = target_spec.get('target_syllables')
        analysis = self.meter_engine.analyze_line(
            line,
            meter_name,
            target_syllables=target_syllables,
        )

        if target_syllables is None:
            pattern = self.meter_engine.meter_patterns.get(meter_name)
            target_syllables = pattern.expected_syllables if pattern else analysis.syllable_count

        # If too many syllables, try removing articles
        if analysis.syllable_count > target_syllables:
            words = line.split()
            filtered = [w for w in words if w.lower() not in ['the', 'a', 'an']]
            if len(filtered) < len(words):
                return ' '.join(filtered)

        # If too few syllables, prepend an onset-correct indefinite article
        elif analysis.syllable_count < target_syllables:
            words = line.split()
            if words and words[0].lower() not in ['the', 'a', 'an']:
                art = choose_indefinite_article(words[0])
                return ' '.join(resolve_articles([art] + words))

        # Non-syllabic: swap a content word for closer syllable + better stress fit
        if meter_name != 'syllabic' and not str(meter_name).startswith('syllabic'):
            swapped = self._meter_stress_swap(line, meter_name, target_syllables)
            if swapped:
                return swapped

        return None

    def _meter_stress_swap(
        self,
        line: str,
        meter_name: str,
        target_syllables: int,
    ) -> Optional[str]:
        """Swap one content word for a DB lemma with closer syllables and better stress."""
        words = line.split()
        if not words or not target_syllables:
            return None

        expected = expected_stress_bits(meter_name, target_syllables)
        if not expected:
            return None

        # Per-token offsets into the line stress bitstream
        offsets: List[Tuple[int, int, str]] = []
        cursor = 0
        for w in words:
            clean = w.lower().strip(".,!?;:'\"")
            raw = self.meter_engine.get_word_stress(clean)
            if raw:
                bits = "".join("1" if c == "1" else "0" for c in raw)
            else:
                syll = self.meter_engine.get_word_syllables(clean)
                bits = "0" * syll
            offsets.append((cursor, len(bits), bits))
            cursor += len(bits)

        total = cursor
        delta = total - target_syllables
        best_line: Optional[str] = None
        best_score = 0.0

        for i, w in enumerate(words):
            clean = w.lower().strip(".,!?;:'\"")
            if not clean or clean in _FUNCTION_WORDS:
                continue

            start, syll, bits = offsets[i]
            exp_slice = expected[start : start + syll] if start < len(expected) else ""
            current_fit = stress_fit_score(bits, exp_slice)
            pos_guess = self._guess_pos(clean)

            if delta > 0:
                syll_options = [max(1, syll - 1), max(1, syll - 2), syll]
            elif delta < 0:
                syll_options = [syll + 1, syll + 2, syll]
            else:
                syll_options = [syll, max(1, syll - 1), syll + 1]

            # Deduplicate while preserving order
            seen = set()
            syll_options = [s for s in syll_options if not (s in seen or seen.add(s))]

            with get_session() as session:
                for want_syll in syll_options:
                    new_exp = expected[start : start + want_syll]
                    rows = (
                        session.query(WordRecord)
                        .filter(
                            WordRecord.syllable_count == want_syll,
                            WordRecord.pos_primary == pos_guess,
                            WordRecord.lemma != clean,
                            WordRecord.stress_pattern.isnot(None),
                        )
                        .limit(15)
                        .all()
                    )
                    for rec in rows:
                        fit = stress_fit_score(rec.stress_pattern or "", new_exp)
                        new_total = total - syll + want_syll
                        syll_improve = abs(total - target_syllables) - abs(
                            new_total - target_syllables
                        )
                        fit_improve = fit - current_fit
                        if want_syll == syll and fit_improve <= 0:
                            continue
                        if want_syll != syll and fit < current_fit - 0.05:
                            continue
                        if syll_improve < 0 and fit_improve <= 0:
                            continue
                        score = fit_improve + 0.3 * syll_improve
                        if score > best_score:
                            trial = words.copy()
                            trial[i] = rec.lemma
                            best_line = " ".join(trial)
                            best_score = score

        return best_line

    def _semantic_correction(self, line: str, target_spec: Dict) -> Optional[str]:
        """
        Adjust semantic alignment by swapping a content word toward palette.
        """
        palette = target_spec.get("semantic_palette") or target_spec.get("palette_lemmas") or []
        if isinstance(palette, dict):
            lemmas = []
            for v in palette.values():
                lemmas.extend(list(v)[:5])
            palette = lemmas
        if not palette:
            return None
        words = line.split()
        if len(words) < 2:
            return None
        # Replace last content-ish token with a palette lemma of similar length
        idx = len(words) - 1
        seed = str(palette[0])
        if seed.lower() == words[idx].lower().strip(".,!?;:"):
            return None
        words[idx] = seed
        from ..forms.grammar_engine import resolve_articles

        return " ".join(resolve_articles(words))

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
