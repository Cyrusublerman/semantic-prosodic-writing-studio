"""
Parameter panel - interactive generation controls.
"""

import logging
from typing import Dict

from ..generation import GenerationSpec, PoemGenerator

logger = logging.getLogger(__name__)


class ParameterPanel:
    """Interactive parameter configuration for generation."""

    def __init__(self):
        self.generator = PoemGenerator()
        self.current_spec = GenerationSpec()

    def show_current_config(self):
        """Display current configuration."""
        print("\n" + "=" * 70)
        print("CURRENT CONFIGURATION")
        print("=" * 70)

        print(f"\nForm: {self.current_spec.form}")
        print(f"Theme: {self.current_spec.theme or 'Not set'}")
        print(f"Affect Profile: {self.current_spec.affect_profile or 'Not set'}")

        print(f"\nRarity Settings:")
        print(f"  Bias: {self.current_spec.rarity_bias:.2f}")
        print(f"  Range: {self.current_spec.min_rarity:.2f} - {self.current_spec.max_rarity:.2f}")

        if self.current_spec.domain_tags:
            print(f"\nDomain Tags: {', '.join(self.current_spec.domain_tags)}")

        if self.current_spec.imagery_tags:
            print(f"Imagery Tags: {', '.join(self.current_spec.imagery_tags)}")

        print(f"\nGeneration Parameters:")
        print(f"  Temperature: {self.current_spec.temperature:.2f}")
        print(f"  Max Iterations: {self.current_spec.max_iterations}")

        print(f"\nConstraint Weights:")
        for name, weight in self.current_spec.constraint_weights.items():
            print(f"  {name}: {weight:.2f}")

        print()

    def set_parameter(self, param: str, value):
        """Set a parameter value."""
        if not hasattr(self.current_spec, param):
            print(f"Unknown parameter: {param}")
            return False

        # Type conversion
        current_value = getattr(self.current_spec, param)

        if isinstance(current_value, float):
            value = float(value)
        elif isinstance(current_value, int):
            value = int(value)
        elif isinstance(current_value, list):
            value = value.split(',') if isinstance(value, str) else value

        setattr(self.current_spec, param, value)
        print(f"Set {param} = {value}")
        return True

    def load_preset(self, preset_name: str):
        """Load a preset configuration."""
        presets = {
            'melancholic_nature': GenerationSpec.preset_melancholic_nature(),
            'joyful_simple': GenerationSpec.preset_joyful_simple(),
            'mysterious_archaic': GenerationSpec.preset_mysterious_archaic()
        }

        if preset_name not in presets:
            print(f"Unknown preset: {preset_name}")
            print(f"Available presets: {', '.join(presets.keys())}")
            return False

        self.current_spec = presets[preset_name]
        print(f"Loaded preset: {preset_name}")
        return True

    def generate_with_current(self):
        """Generate poem with current configuration."""
        # Validate
        errors = self.current_spec.validate()

        if errors:
            print("\nConfiguration errors:")
            for error in errors:
                print(f"  - {error}")
            return None

        print("\nGenerating poem...")
        poem = self.generator.generate(self.current_spec)

        print("\n" + "=" * 70)
        print(poem.text)
        print("=" * 70)
        print(f"\nRun ID: {poem.run_id}")

        return poem

    def interactive_mode(self):
        """Run interactive configuration mode."""
        print("\n" + "=" * 70)
        print("INTERACTIVE PARAMETER PANEL")
        print("=" * 70)
        print("\nCommands:")
        print("  show - Show current configuration")
        print("  set <param> <value> - Set parameter")
        print("  preset <name> - Load preset")
        print("  generate - Generate poem")
        print("  help - Show this help")
        print("  quit - Exit")

        while True:
            try:
                cmd = input("\n> ").strip()

                if not cmd:
                    continue

                parts = cmd.split(maxsplit=2)
                command = parts[0].lower()

                if command == 'quit':
                    break

                elif command == 'show':
                    self.show_current_config()

                elif command == 'set':
                    if len(parts) < 3:
                        print("Usage: set <param> <value>")
                        continue

                    param = parts[1]
                    value = parts[2]
                    self.set_parameter(param, value)

                elif command == 'preset':
                    if len(parts) < 2:
                        print("Usage: preset <name>")
                        print("Available: melancholic_nature, joyful_simple, mysterious_archaic")
                        continue

                    self.load_preset(parts[1])

                elif command == 'generate':
                    self.generate_with_current()

                elif command == 'help':
                    print("\nCommands:")
                    print("  show - Show current configuration")
                    print("  set <param> <value> - Set parameter")
                    print("  preset <name> - Load preset")
                    print("  generate - Generate poem")
                    print("  quit - Exit")

                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for commands")

            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")


def main():
    """CLI for parameter panel."""
    import argparse

    parser = argparse.ArgumentParser(description="Parameter Panel")
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )
    parser.add_argument(
        '--preset',
        type=str,
        help='Load preset configuration'
    )
    parser.add_argument(
        '--generate',
        action='store_true',
        help='Generate poem with current config'
    )

    args = parser.parse_args()

    panel = ParameterPanel()

    if args.preset:
        panel.load_preset(args.preset)

    if args.generate:
        panel.show_current_config()
        panel.generate_with_current()

    elif args.interactive:
        panel.interactive_mode()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
