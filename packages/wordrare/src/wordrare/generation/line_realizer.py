"""
Line realization - fills scaffolds with actual words.

Selects words based on constraints: rhyme, meter, semantics, POS, rarity.
"""

import random
import logging
from typing import List, Optional, Dict, Tuple
import numpy as np

from ..database import WordRecord, get_session
from ..forms import SoundEngine, MeterEngine
from .scaffolding import LineScaffold, PoemScaffold
from .generation_spec import GenerationSpec

logger = logging.getLogger(__name__)


class WordSelector:
    """Selects words based on multiple constraints."""

    def __init__(self, spec: GenerationSpec, semantic_palette: Dict):
        self.spec = spec
        self.semantic_palette = semantic_palette
        self.sound_engine = SoundEngine()
        self.meter_engine = MeterEngine()

        # Cache for performance
        self._word_cache = {}
        self._rhyme_cache = {}

    def select_word(self, pos: str, constraints: Dict,
                   rhyme_word: Optional[str] = None) -> Optional[str]:
        """
        Select a word matching POS and constraints.

        Args:
            pos: Part of speech
            constraints: Dict of constraints (syllables, rhyme, tags, etc.)
            rhyme_word: Word to rhyme with (if applicable)

        Returns:
            Selected word or None
        """
        # Build cache key
        cache_key = (pos, str(constraints), rhyme_word)

        if cache_key in self._word_cache:
            cached = self._word_cache[cache_key]
            # Return random choice from cached candidates
            return random.choice(cached) if cached else None

        # Query candidates
        candidates = self._query_candidates(pos, constraints, rhyme_word)

        # Cache results
        self._word_cache[cache_key] = candidates

        if not candidates:
            logger.debug(f"No candidates found for pos={pos}, constraints={constraints}")
            return None

        # Apply temperature-based selection
        return self._select_with_temperature(candidates)

    def _query_candidates(self, pos: str, constraints: Dict,
                         rhyme_word: Optional[str] = None) -> List[str]:
        """Query database for candidate words."""
        with get_session() as session:
            query = session.query(WordRecord)

            # POS filter
            if pos and pos != 'any':
                query = query.filter(WordRecord.pos_primary == pos)

            # Rarity filter
            query = query.filter(
                WordRecord.rarity_score >= self.spec.min_rarity,
                WordRecord.rarity_score <= self.spec.max_rarity
            )

            # Syllable count filter
            if 'syllables' in constraints:
                query = query.filter(
                    WordRecord.syllable_count == constraints['syllables']
                )

            # Rhyme filter
            if rhyme_word:
                rhyme_key = self.sound_engine.get_rhyme_key(rhyme_word)
                if rhyme_key:
                    query = query.filter(WordRecord.rhyme_key == rhyme_key)

            # Get results
            results = query.limit(100).all()

            # Filter by semantic tags (requires checking JSON fields)
            filtered = []

            for word_record in results:
                # Check domain tags
                if self.spec.domain_tags:
                    if not word_record.domain_tags:
                        continue
                    if not any(tag in word_record.domain_tags for tag in self.spec.domain_tags):
                        continue

                # Check affect tags
                if self.spec.affect_profile:
                    if not word_record.affect_tags:
                        continue
                    if self.spec.affect_profile not in word_record.affect_tags:
                        continue

                filtered.append(word_record.lemma)

            return filtered if filtered else [r.lemma for r in results[:50]]

    def _select_with_temperature(self, candidates: List[str]) -> str:
        """Select from candidates using temperature."""
        if not candidates:
            return None

        if self.spec.temperature == 0.0:
            # Deterministic: always first
            return candidates[0]

        elif self.spec.temperature == 1.0:
            # Fully random
            return random.choice(candidates)

        else:
            # Temperature-based sampling
            # Higher temperature = more random
            n = len(candidates)
            weights = [(1.0 - i / n) ** (1.0 / self.spec.temperature) for i in range(n)]

            return random.choices(candidates, weights=weights)[0]

    def find_rhyming_words(self, rhyme_symbol: str,
                          existing_rhymes: Dict[str, str],
                          pos: str = None,
                          syllables: int = None) -> List[str]:
        """
        Find words that rhyme with existing words for a rhyme symbol.

        Args:
            rhyme_symbol: Rhyme symbol (e.g., 'A')
            existing_rhymes: Map of rhyme symbols to chosen words
            pos: Required part of speech
            syllables: Required syllable count

        Returns:
            List of rhyming candidates
        """
        # Get anchor word for this rhyme
        anchor_word = existing_rhymes.get(rhyme_symbol)

        if not anchor_word:
            # No anchor yet, select any word
            constraints = {}
            if syllables:
                constraints['syllables'] = syllables

            return self._query_candidates(pos, constraints, rhyme_word=None)

        # Find words that rhyme with anchor
        rhyme_key = self.sound_engine.get_rhyme_key(anchor_word)

        if not rhyme_key:
            logger.warning(f"No rhyme key for anchor word: {anchor_word}")
            return []

        # Query with rhyme constraint
        constraints = {}
        if syllables:
            constraints['syllables'] = syllables

        with get_session() as session:
            query = session.query(WordRecord).filter(
                WordRecord.rhyme_key == rhyme_key,
                WordRecord.rarity_score >= self.spec.min_rarity,
                WordRecord.rarity_score <= self.spec.max_rarity
            )

            if pos:
                query = query.filter(WordRecord.pos_primary == pos)

            if syllables:
                query = query.filter(WordRecord.syllable_count == syllables)

            results = query.limit(50).all()

            return [r.lemma for r in results if r.lemma != anchor_word]


class LineRealizer:
    """Realizes lines from scaffolds."""

    def __init__(self, spec: GenerationSpec, semantic_palette: Dict):
        self.spec = spec
        self.semantic_palette = semantic_palette
        self.word_selector = WordSelector(spec, semantic_palette)
        self.meter_engine = MeterEngine()
        self.sound_engine = SoundEngine()

        # Track rhyme assignments
        self.rhyme_assignments = {}  # symbol -> anchor word

    def realize_line(self, scaffold: LineScaffold,
                    max_iterations: int = 5) -> Optional[str]:
        """
        Realize a line from scaffold.

        Args:
            scaffold: Line scaffold
            max_iterations: Max attempts to generate valid line

        Returns:
            Generated line text or None
        """
        if scaffold.is_refrain and scaffold.refrain_text:
            return scaffold.refrain_text

        template = scaffold.syntactic_template

        if not template:
            logger.warning(f"No template for line {scaffold.line_number}")
            return None

        best_line = None
        best_score = -1

        for iteration in range(max_iterations):
            # Generate candidate line
            line = self._generate_candidate_line(scaffold, template)

            if not line:
                continue

            # Score the line
            score = self._score_line(line, scaffold)

            if score > best_score:
                best_score = score
                best_line = line

            # If score is good enough, stop
            if score > 0.8:
                break

        if best_line:
            logger.debug(f"Line {scaffold.line_number}: {best_line} (score={best_score:.2f})")

        return best_line

    def _generate_candidate_line(self, scaffold: LineScaffold,
                                 template) -> Optional[str]:
        """Generate a candidate line."""
        words = []

        for slot in template.pattern:
            # Build constraints
            constraints = slot.constraints.copy()

            # Add syllable constraint if needed
            # (Simple heuristic: distribute syllables across slots)
            remaining_syllables = scaffold.target_syllables - sum(
                self.meter_engine.get_word_syllables(w) for w in words
            )
            remaining_slots = len(template.pattern) - len(words)

            if remaining_slots > 0:
                avg_syllables = remaining_syllables / remaining_slots
                constraints['syllables'] = max(1, round(avg_syllables))

            # Get rhyme word if this is end of line
            rhyme_word = None
            if len(words) == len(template.pattern) - 1 and scaffold.rhyme_symbol:
                # This is the last word - handle rhyme
                rhyme_word = self.rhyme_assignments.get(scaffold.rhyme_symbol)

            # Select word
            word = self.word_selector.select_word(
                slot.pos,
                constraints,
                rhyme_word=rhyme_word
            )

            if not word and slot.required:
                return None

            if word:
                words.append(word)

        return ' '.join(words)

    def _score_line(self, line: str, scaffold: LineScaffold) -> float:
        """Score a line based on constraints."""
        scores = []

        # Meter score
        analysis = self.meter_engine.analyze_line(line, scaffold.meter_pattern)
        meter_score = 1.0 - analysis.stress_deviation
        scores.append(('meter', meter_score, self.spec.constraint_weights['meter']))

        # Syllable score
        syll_deviation = abs(analysis.syllable_count - scaffold.target_syllables)
        syll_score = max(0, 1.0 - syll_deviation / 3.0)
        scores.append(('syllables', syll_score, 0.1))

        # Rhyme score (if applicable)
        if scaffold.rhyme_symbol and scaffold.rhyme_symbol in self.rhyme_assignments:
            anchor = self.rhyme_assignments[scaffold.rhyme_symbol]
            words = line.split()
            if words:
                last_word = words[-1]
                rhyme_match = self.sound_engine.check_rhyme(anchor, last_word)
                rhyme_score = rhyme_match.similarity if rhyme_match else 0.0
                scores.append(('rhyme', rhyme_score, self.spec.constraint_weights['rhyme']))

        # Compute weighted average
        total_weight = sum(weight for _, _, weight in scores)
        if total_weight == 0:
            return 0.0

        weighted_score = sum(score * weight for _, score, weight in scores) / total_weight

        return weighted_score

    def realize_poem(self, scaffold: PoemScaffold) -> List[str]:
        """
        Realize complete poem from scaffold.

        Args:
            scaffold: Poem scaffold

        Returns:
            List of line texts
        """
        lines = []

        for stanza in scaffold.stanzas:
            for line_scaffold in stanza.lines:
                # Handle rhyme assignment
                if line_scaffold.rhyme_symbol and line_scaffold.rhyme_symbol not in self.rhyme_assignments:
                    # First occurrence of this rhyme - select anchor word
                    candidates = self.word_selector.find_rhyming_words(
                        line_scaffold.rhyme_symbol,
                        self.rhyme_assignments,
                        pos='noun',  # Prefer nouns for rhyme words
                        syllables=None
                    )

                    if candidates:
                        self.rhyme_assignments[line_scaffold.rhyme_symbol] = candidates[0]

                # Realize line
                line_text = self.realize_line(line_scaffold)

                if not line_text:
                    # Fallback: generate placeholder
                    line_text = f"[Line {line_scaffold.line_number} - generation failed]"

                lines.append(line_text)

        return lines


def main():
    """CLI for line realization testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Line realization utilities")
    parser.add_argument(
        '--form',
        type=str,
        default='haiku',  # Haiku is simpler to test
        help='Poetic form'
    )
    parser.add_argument(
        '--theme',
        type=str,
        default='nature',
        help='Theme'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    from .generation_spec import create_default_spec
    from .theme_selector import ThemeSelector
    from .scaffolding import Scaffolder

    # Create spec
    spec = create_default_spec(form=args.form, theme=args.theme)

    # Build semantic palette
    selector = ThemeSelector()
    palette = selector.build_semantic_palette(spec)

    # Build scaffold
    scaffolder = Scaffolder()
    scaffold = scaffolder.build_scaffold(spec)

    # Realize poem
    realizer = LineRealizer(spec, palette)
    lines = realizer.realize_poem(scaffold)

    print(f"\nGenerated {args.form}:")
    print("=" * 50)
    for line in lines:
        print(line)
    print("=" * 50)


if __name__ == "__main__":
    main()
