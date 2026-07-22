"""
Form debugger - annotate meter, rhyme, IPA, and semantic tags per line.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from ..forms import FormLibrary, MeterEngine, SoundEngine
from ..generation.annotator import PoemAnnotator
from ..metrics import MetricsAnalyzer

logger = logging.getLogger(__name__)


class FormDebugger:
    """Debug and annotate poetic forms."""

    def __init__(self):
        self.meter_engine = MeterEngine()
        self.sound_engine = SoundEngine()
        self.form_library = FormLibrary()
        self.metrics_analyzer = MetricsAnalyzer()
        self.annotator = PoemAnnotator()

    def debug_poem(self, lines: List[str], form_id: str = None):
        """Debug complete poem with phonetic/stress strips and metrics."""
        form = self.form_library.get_form(form_id) if form_id else None

        print("\n" + "=" * 80)
        print("FORM DEBUGGER")
        print("=" * 80)

        if form:
            print(f"\nForm: {form.name}")
            print(f"Expected meter: {form.meter_pattern}")
            print(f"Rhyme pattern: {form.rhyme_pattern}")

        print(f"\nTotal lines: {len(lines)}\n")

        annotations = self.annotator.annotate(lines, scaffold=None, form_id=form_id)

        # Per-line syllable targets for syllabic forms
        if form and form.meter_pattern == "syllabic":
            pattern = form.special_rules.get("syllable_pattern") or []
            for i, line_ann in enumerate(annotations.get("per_line", [])):
                if i < len(pattern):
                    target = pattern[i]
                    analysis = self.meter_engine.analyze_line(
                        line_ann["text"], "syllabic", target_syllables=target
                    )
                    line_ann["target_syllables"] = target
                    line_ann["meter_valid"] = analysis.is_valid
                    line_ann["syllable_count"] = analysis.syllable_count
                    line_ann["stress_bits"] = analysis.stress_pattern
                    line_ann["expected_bits"] = "x" * target
                    line_ann["foot_accuracy"] = analysis.foot_accuracy

        print(self.annotator.format_columns(annotations))

        # Extra per-line sound devices
        for i, line in enumerate(lines, 1):
            devices = self.sound_engine.analyze_sound_devices(line)
            device_str = ", ".join([k for k, v in devices.items() if v])
            if device_str:
                print(f"Line {i} sound devices: {device_str}")

        if form:
            print("\n" + "=" * 80)
            print("OVERALL METRICS")
            print("=" * 80)
            form_spec = {
                "meter": form.meter_pattern,
                "rhyme_pattern": form.rhyme_pattern,
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

        return annotations

    def debug_line(
        self,
        line: str,
        line_number: int,
        form=None,
        target_syllables: Optional[int] = None,
    ):
        """Debug single line (legacy helper)."""
        meter_pattern = form.meter_pattern if form else "iambic_pentameter"
        analysis = self.meter_engine.analyze_line(
            line, meter_pattern, target_syllables=target_syllables
        )
        print(f"Line {line_number}: {line}")
        print(f"  Stress: {analysis.stress_pattern}")
        print(f"  Syllables: {analysis.syllable_count}")
        print(f"  Valid: {'✓' if analysis.is_valid else '✗'}")

    def validate_against_form(self, lines: List[str], form_id: str) -> Dict:
        form = self.form_library.get_form(form_id)
        if not form:
            return {"error": f"Form {form_id} not found"}

        results = {
            "form": form.name,
            "total_lines": len(lines),
            "expected_lines": form.total_lines,
            "line_count_valid": len(lines) == form.total_lines,
            "violations": [],
        }

        syllable_pattern = []
        if form.meter_pattern == "syllabic":
            syllable_pattern = form.special_rules.get("syllable_pattern") or []

        for i, line in enumerate(lines):
            target_syll = syllable_pattern[i] if i < len(syllable_pattern) else None
            analysis = self.meter_engine.analyze_line(
                line, form.meter_pattern, target_syllables=target_syll
            )
            if not analysis.is_valid:
                results["violations"].append(
                    {
                        "line": i + 1,
                        "type": "meter",
                        "details": (
                            f"Meter invalid (foot_accuracy={analysis.foot_accuracy:.2%}, "
                            f"syllables={analysis.syllable_count})"
                        ),
                    }
                )

        # Identical end-word check for shared rhyme symbols when pattern known
        ends = [ln.split()[-1].lower().strip(".,!?;:") for ln in lines if ln.split()]
        seen = {}
        for i, end in enumerate(ends):
            if end in seen:
                results["violations"].append(
                    {
                        "line": i + 1,
                        "type": "identical_rhyme",
                        "details": f"End lemma '{end}' repeats line {seen[end]}",
                    }
                )
            else:
                seen[end] = i + 1

        return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Form Debugger")
    parser.add_argument("file", help="File containing poem (one line per line)")
    parser.add_argument("--form", type=str, help="Form ID for validation")
    parser.add_argument("--validate", action="store_true", help="Validation mode")
    args = parser.parse_args()

    debugger = FormDebugger()
    with open(args.file, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    if args.validate and args.form:
        results = debugger.validate_against_form(lines, args.form)
        print("\nValidation Results:")
        print(f"  Form: {results['form']}")
        print(
            f"  Line Count: {results['total_lines']} / {results['expected_lines']} "
            f"({'✓' if results['line_count_valid'] else '✗'})"
        )
        if results["violations"]:
            print(f"\nViolations ({len(results['violations'])}):")
            for v in results["violations"]:
                print(f"  Line {v['line']}: {v['type']} - {v['details']}")
        else:
            print("\n✓ No violations found")
    else:
        debugger.debug_poem(lines, args.form)


if __name__ == "__main__":
    main()
