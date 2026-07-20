"""
Generation engine - Input specification and configuration.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


@dataclass
class GenerationSpec:
    """Specification for poem generation."""

    # Form configuration
    form: str = "shakespearean_sonnet"

    # Thematic configuration
    theme: Optional[str] = None  # e.g., "nature", "death", "time"
    affect_profile: Optional[str] = None  # e.g., "melancholic", "joyful"

    # Word selection
    rarity_bias: float = 0.5  # 0.0 = common words, 1.0 = very rare words
    min_rarity: float = 0.3
    max_rarity: float = 0.9

    # Semantic constraints
    domain_tags: List[str] = field(default_factory=list)  # e.g., ["nautical", "botanical"]
    imagery_tags: List[str] = field(default_factory=list)  # e.g., ["visual", "auditory"]

    # Device configuration
    device_profile: Dict[str, float] = field(default_factory=dict)
    cross_domain: bool = False  # Allow metaphor bridges across domains
    motif_density: float = 0.3  # How much to repeat motifs

    # Constraint weights
    constraint_weights: Dict[str, float] = field(default_factory=lambda: {
        'rhyme': 0.25,
        'meter': 0.25,
        'semantics': 0.20,
        'affect': 0.15,
        'coherence': 0.10,
        'style': 0.05
    })

    # Generation parameters
    max_iterations: int = 10  # Max repair iterations per line
    temperature: float = 0.7  # Randomness in word selection (0.0-1.0)

    # Output options
    include_annotations: bool = False
    debug_mode: bool = False

    def validate(self) -> List[str]:
        """
        Validate the generation spec.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not 0.0 <= self.rarity_bias <= 1.0:
            errors.append(f"rarity_bias must be 0.0-1.0, got {self.rarity_bias}")

        if not 0.0 <= self.min_rarity <= 1.0:
            errors.append(f"min_rarity must be 0.0-1.0, got {self.min_rarity}")

        if not 0.0 <= self.max_rarity <= 1.0:
            errors.append(f"max_rarity must be 0.0-1.0, got {self.max_rarity}")

        if self.min_rarity > self.max_rarity:
            errors.append(f"min_rarity ({self.min_rarity}) > max_rarity ({self.max_rarity})")

        if not 0.0 <= self.motif_density <= 1.0:
            errors.append(f"motif_density must be 0.0-1.0, got {self.motif_density}")

        if not 0.0 <= self.temperature <= 1.0:
            errors.append(f"temperature must be 0.0-1.0, got {self.temperature}")

        # Validate constraint weights sum to 1.0
        weight_sum = sum(self.constraint_weights.values())
        if abs(weight_sum - 1.0) > 0.01:
            errors.append(f"constraint_weights must sum to 1.0, got {weight_sum}")

        return errors

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'form': self.form,
            'theme': self.theme,
            'affect_profile': self.affect_profile,
            'rarity_bias': self.rarity_bias,
            'min_rarity': self.min_rarity,
            'max_rarity': self.max_rarity,
            'domain_tags': self.domain_tags,
            'imagery_tags': self.imagery_tags,
            'device_profile': self.device_profile,
            'cross_domain': self.cross_domain,
            'motif_density': self.motif_density,
            'constraint_weights': self.constraint_weights,
            'max_iterations': self.max_iterations,
            'temperature': self.temperature,
            'include_annotations': self.include_annotations,
            'debug_mode': self.debug_mode
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'GenerationSpec':
        """Create from dictionary."""
        return cls(**data)

    @classmethod
    def preset_melancholic_nature(cls) -> 'GenerationSpec':
        """Preset for melancholic nature poem."""
        return cls(
            form='shakespearean_sonnet',
            theme='nature',
            affect_profile='melancholic',
            rarity_bias=0.6,
            domain_tags=['botanical'],
            imagery_tags=['visual'],
            motif_density=0.4
        )

    @classmethod
    def preset_joyful_simple(cls) -> 'GenerationSpec':
        """Preset for joyful, accessible poem."""
        return cls(
            form='haiku',
            theme='nature',
            affect_profile='joyful',
            rarity_bias=0.2,  # Use more common words
            min_rarity=0.0,
            max_rarity=0.5,
            imagery_tags=['visual', 'auditory']
        )

    @classmethod
    def preset_mysterious_archaic(cls) -> 'GenerationSpec':
        """Preset for mysterious, archaic-feeling poem."""
        return cls(
            form='villanelle',
            theme='mystery',
            affect_profile='mysterious',
            rarity_bias=0.8,
            min_rarity=0.6,
            cross_domain=True,
            motif_density=0.5
        )


def create_default_spec(form: str = "shakespearean_sonnet",
                       theme: str = None,
                       rarity: float = 0.5) -> GenerationSpec:
    """
    Create a default generation spec with minimal configuration.

    Args:
        form: Poetic form
        theme: Theme/topic
        rarity: Rarity bias (0.0-1.0)

    Returns:
        GenerationSpec
    """
    return GenerationSpec(
        form=form,
        theme=theme,
        rarity_bias=rarity
    )


def main():
    """CLI for testing generation specs."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Generation spec utilities")
    parser.add_argument(
        '--preset',
        choices=['melancholic_nature', 'joyful_simple', 'mysterious_archaic'],
        help='Use a preset configuration'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate the spec'
    )

    args = parser.parse_args()

    if args.preset:
        if args.preset == 'melancholic_nature':
            spec = GenerationSpec.preset_melancholic_nature()
        elif args.preset == 'joyful_simple':
            spec = GenerationSpec.preset_joyful_simple()
        else:
            spec = GenerationSpec.preset_mysterious_archaic()

        print(f"\nPreset: {args.preset}")
        print(json.dumps(spec.to_dict(), indent=2))

        if args.validate:
            errors = spec.validate()
            if errors:
                print("\nValidation errors:")
                for error in errors:
                    print(f"  - {error}")
            else:
                print("\n✓ Spec is valid")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
