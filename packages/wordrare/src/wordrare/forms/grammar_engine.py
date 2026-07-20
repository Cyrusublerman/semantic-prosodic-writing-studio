"""
Grammar engine for syntactic template management.

Handles:
- Syntactic pattern definitions (NP/VP/PP/clause patterns)
- Line template generation
- POS role assignment
"""

import random
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class POSSlot:
    """Represents a part-of-speech slot in a template."""
    pos: str  # e.g., "noun", "adjective", "verb"
    required: bool = True
    constraints: Dict = None  # Additional constraints (e.g., syllable count)

    def __post_init__(self):
        if self.constraints is None:
            self.constraints = {}


@dataclass
class SyntacticTemplate:
    """Represents a syntactic template for a line."""
    template_id: str
    name: str
    pattern: List[POSSlot]
    description: str

    def get_pos_sequence(self) -> List[str]:
        """Get sequence of POS tags."""
        return [slot.pos for slot in self.pattern]


# Common syntactic templates
TEMPLATES = {
    # Noun phrase patterns
    'np_simple': SyntacticTemplate(
        'np_simple',
        'Simple NP',
        [POSSlot('article'), POSSlot('noun')],
        'Article + Noun'
    ),

    'np_adj': SyntacticTemplate(
        'np_adj',
        'NP with Adjective',
        [POSSlot('article'), POSSlot('adjective'), POSSlot('noun')],
        'Article + Adjective + Noun'
    ),

    'np_complex': SyntacticTemplate(
        'np_complex',
        'Complex NP',
        [POSSlot('article'), POSSlot('adjective'), POSSlot('adjective'), POSSlot('noun')],
        'Article + Adjective + Adjective + Noun'
    ),

    # Verb phrase patterns
    'vp_simple': SyntacticTemplate(
        'vp_simple',
        'Simple VP',
        [POSSlot('verb'), POSSlot('article'), POSSlot('noun')],
        'Verb + NP'
    ),

    'vp_adverb': SyntacticTemplate(
        'vp_adverb',
        'VP with Adverb',
        [POSSlot('adverb'), POSSlot('verb'), POSSlot('article'), POSSlot('noun')],
        'Adverb + Verb + NP'
    ),

    # Clause patterns
    'svo': SyntacticTemplate(
        'svo',
        'Subject-Verb-Object',
        [
            POSSlot('article'), POSSlot('noun'),  # Subject
            POSSlot('verb'),  # Verb
            POSSlot('article'), POSSlot('noun')   # Object
        ],
        'Simple SVO clause'
    ),

    'svo_adj': SyntacticTemplate(
        'svo_adj',
        'SVO with Adjectives',
        [
            POSSlot('article'), POSSlot('adjective'), POSSlot('noun'),  # Subject
            POSSlot('verb'),  # Verb
            POSSlot('article'), POSSlot('adjective'), POSSlot('noun')   # Object
        ],
        'SVO with adjectives'
    ),

    'svoc': SyntacticTemplate(
        'svoc',
        'Subject-Verb-Object-Complement',
        [
            POSSlot('article'), POSSlot('noun'),  # Subject
            POSSlot('verb'),  # Verb
            POSSlot('article'), POSSlot('noun'),  # Object
            POSSlot('adjective')  # Complement
        ],
        'SVO with complement'
    ),

    # Prepositional phrase patterns
    'pp': SyntacticTemplate(
        'pp',
        'Prepositional Phrase',
        [POSSlot('preposition'), POSSlot('article'), POSSlot('noun')],
        'Preposition + NP'
    ),

    'pp_adj': SyntacticTemplate(
        'pp_adj',
        'PP with Adjective',
        [POSSlot('preposition'), POSSlot('article'), POSSlot('adjective'), POSSlot('noun')],
        'Preposition + Adjective + NP'
    ),

    # Full line patterns
    'line_svo_pp': SyntacticTemplate(
        'line_svo_pp',
        'SVO + PP',
        [
            POSSlot('article'), POSSlot('noun'),  # Subject
            POSSlot('verb'),  # Verb
            POSSlot('article'), POSSlot('noun'),  # Object
            POSSlot('preposition'), POSSlot('article'), POSSlot('noun')  # PP
        ],
        'SVO clause with prepositional phrase'
    ),

    'line_adj_n_v_adv': SyntacticTemplate(
        'line_adj_n_v_adv',
        'Adjective-Noun-Verb-Adverb',
        [
            POSSlot('article'), POSSlot('adjective'), POSSlot('noun'),  # Subject
            POSSlot('verb'),  # Verb
            POSSlot('adverb')  # Adverb
        ],
        'Descriptive subject with adverbial verb'
    ),
}


class GrammarEngine:
    """Manages syntactic templates and patterns."""

    def __init__(self):
        self.templates = TEMPLATES

    def get_template(self, template_id: str) -> Optional[SyntacticTemplate]:
        """
        Get a template by ID.

        Args:
            template_id: Template identifier

        Returns:
            SyntacticTemplate or None
        """
        return self.templates.get(template_id)

    def list_templates(self, category: str = None) -> List[str]:
        """
        List available templates.

        Args:
            category: Filter by category prefix (e.g., 'np', 'vp', 'line')

        Returns:
            List of template IDs
        """
        if category:
            return [tid for tid in self.templates.keys() if tid.startswith(category)]

        return list(self.templates.keys())

    def get_random_template(self, category: str = None,
                           syllable_target: int = None) -> SyntacticTemplate:
        """
        Get a random template.

        Args:
            category: Filter by category prefix
            syllable_target: Target syllable count (approximate)

        Returns:
            Random SyntacticTemplate
        """
        candidates = self.list_templates(category)

        if not candidates:
            # Fallback to all templates
            candidates = self.list_templates()

        if syllable_target:
            # Filter by approximate length
            # (Rough heuristic: each slot ~2 syllables)
            filtered = []

            for tid in candidates:
                template = self.templates[tid]
                approx_syllables = len(template.pattern) * 2

                # Allow ±3 syllables tolerance
                if abs(approx_syllables - syllable_target) <= 3:
                    filtered.append(tid)

            if filtered:
                candidates = filtered

        template_id = random.choice(candidates)

        return self.templates[template_id]

    def create_template(self, template_id: str, name: str,
                       pattern: List[Dict], description: str = '') -> SyntacticTemplate:
        """
        Create a custom template.

        Args:
            template_id: Unique identifier
            name: Human-readable name
            pattern: List of slot dictionaries
            description: Template description

        Returns:
            Created SyntacticTemplate
        """
        # Convert pattern dicts to POSSlot objects
        slots = []

        for slot_dict in pattern:
            slot = POSSlot(
                pos=slot_dict['pos'],
                required=slot_dict.get('required', True),
                constraints=slot_dict.get('constraints', {})
            )
            slots.append(slot)

        template = SyntacticTemplate(
            template_id=template_id,
            name=name,
            pattern=slots,
            description=description
        )

        # Add to templates
        self.templates[template_id] = template

        return template

    def expand_template(self, template: SyntacticTemplate,
                       word_selector) -> Optional[str]:
        """
        Expand a template into actual words.

        Args:
            template: The template to expand
            word_selector: Function to select words for POS (pos -> word)

        Returns:
            Generated text or None
        """
        words = []

        for slot in template.pattern:
            word = word_selector(slot.pos, slot.constraints)

            if word is None and slot.required:
                logger.warning(f"Could not fill required slot: {slot.pos}")
                return None

            if word:
                words.append(word)

        return ' '.join(words)

    def analyze_line_syntax(self, line: str, expected_template: str = None) -> Dict:
        """
        Analyze syntactic structure of a line.

        Args:
            line: Text of the line
            expected_template: Expected template ID

        Returns:
            Dictionary with analysis results
        """
        # This would require POS tagging
        # For now, return placeholder

        words = line.split()

        return {
            'word_count': len(words),
            'expected_template': expected_template,
            'matches_template': None,  # Would need POS tagger
            'pos_sequence': None  # Would need POS tagger
        }

    def suggest_template_for_meter(self, meter_pattern: str) -> List[str]:
        """
        Suggest templates suitable for a meter pattern.

        Args:
            meter_pattern: Meter pattern name (e.g., 'iambic_pentameter')

        Returns:
            List of suitable template IDs
        """
        # Map meter to approximate syllable count
        meter_syllables = {
            'iambic_pentameter': 10,
            'iambic_tetrameter': 8,
            'trochaic_tetrameter': 8,
            'anapestic_tetrameter': 12,
        }

        target = meter_syllables.get(meter_pattern, 10)

        # Find templates with appropriate length
        suitable = []

        for tid, template in self.templates.items():
            approx_syllables = len(template.pattern) * 2

            if abs(approx_syllables - target) <= 2:
                suitable.append(tid)

        return suitable


def main():
    """Command-line interface for grammar engine."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage syntactic templates")
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all templates'
    )
    parser.add_argument(
        '--show',
        type=str,
        help='Show template details'
    )
    parser.add_argument(
        '--category',
        type=str,
        help='Filter by category'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    engine = GrammarEngine()

    if args.list:
        templates = engine.list_templates(category=args.category)
        print("\nAvailable Templates:")
        for tid in templates:
            template = engine.get_template(tid)
            print(f"  {tid}: {template.name}")
            print(f"    Pattern: {' '.join(template.get_pos_sequence())}")

    elif args.show:
        template = engine.get_template(args.show)
        if template:
            print(f"\nTemplate: {template.name}")
            print(f"ID: {template.template_id}")
            print(f"Description: {template.description}")
            print(f"Pattern:")
            for i, slot in enumerate(template.pattern, 1):
                print(f"  {i}. {slot.pos} (required: {slot.required})")
        else:
            print(f"Template '{args.show}' not found")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
