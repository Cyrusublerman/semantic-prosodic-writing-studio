"""
Form debugger - annotate meter, rhyme, and semantic tags per line.
"""

import logging
from typing import List, Dict

from ..forms import MeterEngine, SoundEngine, FormLibrary
from ..metrics import MetricsAnalyzer
from ..database import WordRecord, get_session

logger = logging.getLogger(__name__)


class FormDebugger:
    """Debug and annotate poetic forms."""

    def __init__(self):
        self.meter_engine = MeterEngine()
        self.sound_engine = SoundEngine()
        self.form_library = FormLibrary()
        self.metrics_analyzer = MetricsAnalyzer()

    def debug_poem(self, lines: List[str], form_id: str = None):
        """
        Debug complete poem with annotations.

        Args:
            lines: List of line texts
            form_id: Form ID for validation
        """
        form = None
        if form_id:
            form = self.form_library.get_form(form_id)

        print("\n" + "=" * 80)
        print("FORM DEBUGGER")
        print("=" * 80)

        if form:
            print(f"\nForm: {form.name}")
            print(f"Expected meter: {form.meter_pattern}")
            print(f"Rhyme pattern: {form.rhyme_pattern}")

        print(f"\nTotal lines: {len(lines)}\n")

        # Analyze each line
        for i, line in enumerate(lines, 1):
            self.debug_line(line, i, form)

        # Overall metrics
        if form:
            print("\n" + "=" * 80)
            print("OVERALL METRICS")
            print("=" * 80)

            form_spec = {
                'meter': form.meter_pattern,
                'rhyme_pattern': form.rhyme_pattern
            }

            metrics = self.metrics_analyzer.analyze_poem(lines, form_spec)

            print(f"\nMeter Score: {metrics.meter.score:.2f}")
            print(f"  Foot Accuracy: {metrics.meter.foot_accuracy:.2%}")
            print(f"  Stability: {metrics.meter.stability:.2%}")

            print(f"\nRhyme Score: {metrics.rhyme.score:.2f}")
            print(f"  Density: {metrics.rhyme.density:.2%}")
            print(f"  Strictness: {metrics.rhyme.strictness:.2%}")

            print(f"\nSemantic Score: {metrics.semantic.score:.2f}")
            print(f"  Theme Coherence: {metrics.semantic.theme_coherence:.2%}")
            print(f"  Depth: {metrics.semantic.depth:.2%}")

            print(f"\nTotal Score: {metrics.total_score:.2f}")
            print()

    def debug_line(self, line: str, line_number: int, form = None):
        """Debug single line."""
        print(f"Line {line_number}: {line}")
        print("-" * 80)

        # Meter analysis
        if form:
            meter_pattern = form.meter_pattern
        else:
            meter_pattern = 'iambic_pentameter'

        analysis = self.meter_engine.analyze_line(line, meter_pattern)

        print(f"  Meter: {meter_pattern}")
        print(f"    Syllables: {analysis.syllable_count} "
              f"(target: {analysis.meter_pattern.expected_syllables if hasattr(analysis, 'meter_pattern') else 'N/A'})")
        print(f"    Stress: {analysis.stress_pattern}")
        print(f"    Foot Accuracy: {analysis.foot_accuracy:.2%}")
        print(f"    Valid: {'✓' if analysis.is_valid else '✗'}")

        # Sound devices
        devices = self.sound_engine.analyze_sound_devices(line)
        device_str = ', '.join([k for k, v in devices.items() if v])
        print(f"  Sound Devices: {device_str if device_str else 'None'}")

        # Word-level analysis
        words = line.split()
        print(f"  Words ({len(words)}):")

        with get_session() as session:
            for word in words[:5]:  # Show first 5
                clean_word = word.lower().strip('.,!?;:')
                record = session.query(WordRecord).filter_by(lemma=clean_word).first()

                if record:
                    tags = []
                    if record.domain_tags:
                        tags.extend(record.domain_tags[:2])
                    if record.affect_tags:
                        tags.extend(record.affect_tags[:1])

                    tag_str = ', '.join(tags) if tags else 'no tags'
                    rarity_str = f"{record.rarity_score:.2f}" if record.rarity_score else 'N/A'

                    print(f"    {clean_word}: syllables={record.syllable_count}, "
                          f"rarity={rarity_str}, tags=[{tag_str}]")

            if len(words) > 5:
                print(f"    ... and {len(words) - 5} more words")

        print()

    def validate_against_form(self, lines: List[str], form_id: str) -> Dict:
        """
        Validate poem against form specification.

        Args:
            lines: List of line texts
            form_id: Form ID

        Returns:
            Dictionary with validation results
        """
        form = self.form_library.get_form(form_id)

        if not form:
            return {'error': f'Form {form_id} not found'}

        results = {
            'form': form.name,
            'total_lines': len(lines),
            'expected_lines': form.total_lines,
            'line_count_valid': len(lines) == form.total_lines,
            'violations': []
        }

        # Check meter for each line
        for i, line in enumerate(lines, 1):
            analysis = self.meter_engine.analyze_line(line, form.meter_pattern)

            if not analysis.is_valid:
                results['violations'].append({
                    'line': i,
                    'type': 'meter',
                    'details': f"Meter invalid (foot_accuracy={analysis.foot_accuracy:.2%})"
                })

        return results


def main():
    """CLI for form debugger."""
    import argparse

    parser = argparse.ArgumentParser(description="Form Debugger")
    parser.add_argument(
        'file',
        help='File containing poem (one line per line)'
    )
    parser.add_argument(
        '--form',
        type=str,
        help='Form ID for validation'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validation mode'
    )

    args = parser.parse_args()

    debugger = FormDebugger()

    # Read poem
    with open(args.file, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    if args.validate and args.form:
        # Validation mode
        results = debugger.validate_against_form(lines, args.form)

        print(f"\nValidation Results:")
        print(f"  Form: {results['form']}")
        print(f"  Line Count: {results['total_lines']} / {results['expected_lines']} "
              f"({'✓' if results['line_count_valid'] else '✗'})")

        if results['violations']:
            print(f"\nViolations ({len(results['violations'])}):")
            for v in results['violations']:
                print(f"  Line {v['line']}: {v['type']} - {v['details']}")
        else:
            print(f"\n✓ No violations found")

    else:
        # Debug mode
        debugger.debug_poem(lines, args.form)


if __name__ == "__main__":
    main()
