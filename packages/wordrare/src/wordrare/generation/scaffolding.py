"""
Stanza and line scaffolding - builds structure from form specifications.
"""

import logging
from typing import List, Optional, Dict
from dataclasses import dataclass, field

from ..forms import FormLibrary, FormSpec, StanzaSpec
from ..forms import GrammarEngine, SyntacticTemplate
from ..forms.grammar_engine import mono_chain_template
from ..forms.rhyme_plan import RhymePlan, compile_rhyme_plan
from .generation_spec import GenerationSpec

logger = logging.getLogger(__name__)


@dataclass
class LineScaffold:
    """Scaffold for a single line."""
    line_number: int  # 1-indexed
    stanza_number: int  # 1-indexed
    rhyme_symbol: Optional[str]
    meter_pattern: str
    target_syllables: int
    syntactic_template: Optional[SyntacticTemplate] = None
    is_refrain: bool = False
    refrain_text: Optional[str] = None  # For villanelle refrains
    rhyme_code: Optional[str] = None
    rhyme_slots: list = field(default_factory=list)


@dataclass
class StanzaScaffold:
    """Scaffold for a stanza."""
    stanza_number: int  # 1-indexed
    lines: List[LineScaffold] = field(default_factory=list)

    def __len__(self):
        return len(self.lines)


@dataclass
class PoemScaffold:
    """Complete scaffold for a poem."""
    form: FormSpec
    stanzas: List[StanzaScaffold] = field(default_factory=list)
    rhyme_groups: Dict[str, List[int]] = field(default_factory=dict)  # symbol -> line numbers
    rhyme_plan: Optional[RhymePlan] = None

    def get_line(self, line_number: int) -> Optional[LineScaffold]:
        """Get line by number (1-indexed)."""
        current = 0
        for stanza in self.stanzas:
            if current + len(stanza.lines) >= line_number:
                local_index = line_number - current - 1
                return stanza.lines[local_index]
            current += len(stanza.lines)
        return None

    def get_total_lines(self) -> int:
        """Get total number of lines."""
        return sum(len(stanza.lines) for stanza in self.stanzas)


class Scaffolder:
    """Builds scaffolding from form specifications."""

    def __init__(self):
        self.form_library = FormLibrary()
        self.grammar_engine = GrammarEngine()

        # Meter syllable targets
        self.meter_syllables = {
            'iambic_pentameter': 10,
            'iambic_tetrameter': 8,
            'trochaic_tetrameter': 8,
            'anapestic_tetrameter': 12,
            'dactylic_hexameter': 18,
            'syllabic': None  # Will be determined by form rules
        }

    def build_scaffold(self, spec: GenerationSpec) -> PoemScaffold:
        """
        Build complete poem scaffold.

        Args:
            spec: Generation specification

        Returns:
            PoemScaffold
        """
        # Get form specification
        form = self.form_library.get_form(spec.form)

        if not form:
            raise ValueError(f"Unknown form: {spec.form}")

        logger.info(f"Building scaffold for {form.name}")

        scaffold = PoemScaffold(form=form)

        # Build stanza scaffolds
        line_number = 1

        for stanza_spec in form.stanza_specs:
            stanza = self._build_stanza_scaffold(
                stanza_spec,
                line_number,
                form,
                spec
            )

            scaffold.stanzas.append(stanza)
            line_number += len(stanza.lines)

        # Build rhyme groups
        scaffold.rhyme_groups = self._build_rhyme_groups(scaffold)

        # Handle refrains (for villanelle)
        self._apply_refrains(scaffold, form)

        # Compile RhymePlan (spec overrides > form special_rules)
        self._attach_rhyme_plan(scaffold, form, spec)

        logger.info(f"Built scaffold with {scaffold.get_total_lines()} lines")

        return scaffold

    def _attach_rhyme_plan(
        self, scaffold: PoemScaffold, form: FormSpec, spec: GenerationSpec
    ) -> None:
        lines: List[LineScaffold] = []
        for stanza in scaffold.stanzas:
            lines.extend(stanza.lines)
        symbols = [ln.rhyme_symbol for ln in lines]
        targets = [ln.target_syllables for ln in lines]

        rhyme_spans = spec.rhyme_spans or form.get_rhyme_spans()
        rhyme_map = spec.rhyme_map or form.get_rhyme_map()
        rhyme_span = spec.rhyme_span or form.get_rhyme_span()

        try:
            plan = compile_rhyme_plan(
                line_symbols=symbols,
                line_targets=targets,
                rhyme_span=rhyme_span,
                rhyme_map=rhyme_map,
                rhyme_spans=rhyme_spans,
                match_mode=spec.rhyme_match_mode,
                coalesce_runs=spec.rhyme_coalesce_runs,
            )
        except ValueError as e:
            logger.error("Rhyme plan compile failed: %s", e)
            plan = RhymePlan()

        scaffold.rhyme_plan = plan
        for ln in lines:
            ln.rhyme_code = plan.line_codes.get(ln.line_number)
            ln.rhyme_slots = plan.slots_for_line(ln.line_number)
            # Dense per-syllable maps need one slot per syllable
            if ln.rhyme_slots and len(ln.rhyme_slots) >= ln.target_syllables:
                ln.syntactic_template = mono_chain_template(ln.target_syllables)

    def _build_stanza_scaffold(self, stanza_spec: StanzaSpec,
                               start_line_number: int,
                               form: FormSpec,
                               gen_spec: GenerationSpec) -> StanzaScaffold:
        """Build scaffold for a single stanza."""
        stanza = StanzaScaffold(stanza_number=stanza_spec.stanza_id)

        for i in range(stanza_spec.lines):
            line_number = start_line_number + i
            rhyme_symbol = stanza_spec.rhyme_pattern[i]

            # Get target syllables
            target_syllables = self._get_target_syllables(
                stanza_spec.meter_pattern,
                form,
                i
            )

            # Prefer content-ending templates when the line participates in rhyme
            template = self._select_template(
                target_syllables=target_syllables,
                rhyme_symbol=rhyme_symbol,
                meter_pattern=stanza_spec.meter_pattern,
            )

            line = LineScaffold(
                line_number=line_number,
                stanza_number=stanza_spec.stanza_id,
                rhyme_symbol=rhyme_symbol,
                meter_pattern=stanza_spec.meter_pattern,
                target_syllables=target_syllables,
                syntactic_template=template
            )

            stanza.lines.append(line)

        return stanza

    def _select_template(
        self,
        target_syllables: int,
        rhyme_symbol: Optional[str],
        meter_pattern: str = "",
    ):
        """Pick a syntactic template; syllabic forms use short 5/7 templates."""
        import random

        if meter_pattern == "syllabic" or str(meter_pattern).startswith("syllabic"):
            if target_syllables <= 5:
                ids = [
                    "syl_5_art_adj_noun",
                    "syl_5_prep_art_adj_noun",
                    "syl_5_art_noun_verb",
                    "line_adj_noun",
                ]
            else:
                ids = [
                    "syl_7_art_noun_verb_art_noun",
                    "syl_7_prep_art_adj_noun",
                    "syl_7_art_adj_noun_verb_noun",
                    "line_np_verb_noun",
                ]
            pool = [self.grammar_engine.get_template(t) for t in ids]
            pool = [t for t in pool if t]
            if pool:
                return random.choice(pool)

        rhyme_templates = [
            'line_np_verb_noun',
            'line_svo_end_noun',
            'line_adj_noun',
            'line_prep_adj_noun',
            'line_svo_pp',
        ]
        if rhyme_symbol and rhyme_symbol != 'null':
            candidates = []
            for tid in rhyme_templates:
                template = self.grammar_engine.get_template(tid)
                if not template:
                    continue
                approx = len(template.pattern) * 2
                if abs(approx - target_syllables) <= 4:
                    candidates.append(template)
            if candidates:
                return random.choice(candidates)
            for tid in rhyme_templates:
                template = self.grammar_engine.get_template(tid)
                if template:
                    return template

        return self.grammar_engine.get_random_template(
            category='line',
            syllable_target=target_syllables,
        )

    def _get_target_syllables(self, meter_pattern: str,
                              form: FormSpec, line_index: int) -> int:
        """Get target syllable count for a line."""
        # Check special rules for syllable pattern (haiku)
        if 'special_rules' in form.special_rules:
            special = form.special_rules.get('special_rules', {})
            if 'syllable_pattern' in special:
                return special['syllable_pattern'][line_index]

        # Check special_rules at top level
        if 'syllable_pattern' in form.special_rules:
            pattern = form.special_rules['syllable_pattern']
            if line_index < len(pattern):
                return pattern[line_index]

        # Use meter-based target
        return self.meter_syllables.get(meter_pattern, 10)

    def _build_rhyme_groups(self, scaffold: PoemScaffold) -> Dict[str, List[int]]:
        """Build rhyme groups mapping symbols to line numbers."""
        groups = {}

        for stanza in scaffold.stanzas:
            for line in stanza.lines:
                if line.rhyme_symbol and line.rhyme_symbol != 'null':
                    # Extract base symbol (remove numbers for villanelle)
                    base_symbol = line.rhyme_symbol.rstrip('0123456789')

                    if base_symbol not in groups:
                        groups[base_symbol] = []

                    groups[base_symbol].append(line.line_number)

        return groups

    def _apply_refrains(self, scaffold: PoemScaffold, form: FormSpec):
        """Apply refrain rules (for villanelle)."""
        if 'refrains' not in form.special_rules:
            return

        refrains = form.special_rules['refrains']

        for refrain_id, refrain_spec in refrains.items():
            # Mark refrain lines
            base_line = refrain_spec['line_number']
            repetitions = refrain_spec['repetitions']

            # Mark all refrain occurrences
            for line_num in [base_line] + repetitions:
                line = scaffold.get_line(line_num)
                if line:
                    line.is_refrain = True
                    # The actual text will be set during generation

        logger.info(f"Applied {len(refrains)} refrain patterns")

    def assign_templates_to_scaffold(self, scaffold: PoemScaffold,
                                     template_strategy: str = 'varied') -> PoemScaffold:
        """
        Assign or reassign syntactic templates to lines.

        Args:
            scaffold: Poem scaffold
            template_strategy: 'varied', 'consistent', 'random'

        Returns:
            Updated scaffold
        """
        if template_strategy == 'consistent':
            # Use same template for all lines of same length
            template_cache = {}

            for stanza in scaffold.stanzas:
                for line in stanza.lines:
                    key = line.target_syllables

                    if key not in template_cache:
                        template_cache[key] = self.grammar_engine.get_random_template(
                            category='line',
                            syllable_target=line.target_syllables
                        )

                    line.syntactic_template = template_cache[key]

        elif template_strategy == 'random':
            # Random template for each line
            for stanza in scaffold.stanzas:
                for line in stanza.lines:
                    line.syntactic_template = self.grammar_engine.get_random_template(
                        category='line',
                        syllable_target=line.target_syllables
                    )

        # 'varied' is default - already assigned in build

        return scaffold


def main():
    """CLI for scaffolding testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Poem scaffolding utilities")
    parser.add_argument(
        '--form',
        type=str,
        default='shakespearean_sonnet',
        help='Poetic form'
    )
    parser.add_argument(
        '--show',
        action='store_true',
        help='Show scaffold details'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    from .generation_spec import create_default_spec

    spec = create_default_spec(form=args.form)
    scaffolder = Scaffolder()

    scaffold = scaffolder.build_scaffold(spec)

    if args.show:
        print(f"\nPoem Scaffold: {scaffold.form.name}")
        print(f"Total lines: {scaffold.get_total_lines()}")
        print(f"\nRhyme groups:")
        for symbol, lines in scaffold.rhyme_groups.items():
            print(f"  {symbol}: lines {lines}")

        print(f"\nLine details:")
        for stanza in scaffold.stanzas:
            print(f"\n  Stanza {stanza.stanza_number}:")
            for line in stanza.lines:
                template_name = line.syntactic_template.name if line.syntactic_template else 'None'
                print(f"    Line {line.line_number}: rhyme={line.rhyme_symbol}, "
                      f"syllables={line.target_syllables}, template={template_name}")


if __name__ == "__main__":
    main()
