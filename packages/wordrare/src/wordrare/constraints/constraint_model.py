"""
Constraint model for multi-tier constraint satisfaction.

Implements the constraint framework from BuildGuide Section 3.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConstraintTier(Enum):
    """Constraint priority tiers."""
    HARD = "hard"  # Structure - must be satisfied
    SOFT_HIGH = "soft_high"  # Rhyme, meter - highly desirable
    SOFT_MED = "soft_med"  # Theme, affect - moderately desirable
    SOFT_LOW = "soft_low"  # Devices, rarity - nice to have


@dataclass
class Constraint:
    """Represents a single constraint."""
    name: str
    tier: ConstraintTier
    weight: float
    score: float = 0.0  # 0.0 to 1.0
    satisfied: bool = False

    def evaluate(self) -> float:
        """
        Evaluate constraint contribution to overall score.

        Returns:
            Weighted score
        """
        return self.score * self.weight


class ConstraintModel:
    """Manages constraints and computes utility scores."""

    def __init__(self, weights: Dict[str, float] = None):
        """
        Initialize constraint model.

        Args:
            weights: Custom constraint weights
        """
        self.weights = weights or {
            'rhyme': 0.25,
            'meter': 0.25,
            'semantics': 0.20,
            'affect': 0.15,
            'coherence': 0.10,
            'style': 0.05
        }

        # Constraint tier mappings
        self.tier_map = {
            'structure': ConstraintTier.HARD,
            'rhyme': ConstraintTier.SOFT_HIGH,
            'meter': ConstraintTier.SOFT_HIGH,
            'semantics': ConstraintTier.SOFT_MED,
            'affect': ConstraintTier.SOFT_MED,
            'coherence': ConstraintTier.SOFT_MED,
            'style': ConstraintTier.SOFT_LOW,
            'devices': ConstraintTier.SOFT_LOW,
            'rarity': ConstraintTier.SOFT_LOW
        }

    def create_constraint(self, name: str, score: float,
                         tier: ConstraintTier = None) -> Constraint:
        """
        Create a constraint.

        Args:
            name: Constraint name
            score: Score value (0.0-1.0)
            tier: Priority tier (auto-detected if None)

        Returns:
            Constraint object
        """
        if tier is None:
            tier = self.tier_map.get(name, ConstraintTier.SOFT_LOW)

        weight = self.weights.get(name, 0.0)
        satisfied = score >= 0.7  # 70% threshold for satisfaction

        return Constraint(
            name=name,
            tier=tier,
            weight=weight,
            score=score,
            satisfied=satisfied
        )

    def compute_utility(self, constraints: List[Constraint]) -> float:
        """
        Compute overall utility score.

        U = Σ w_i · S_i

        Args:
            constraints: List of constraints

        Returns:
            Utility score (0.0-1.0)
        """
        total_weight = sum(c.weight for c in constraints)

        if total_weight == 0:
            return 0.0

        weighted_sum = sum(c.evaluate() for c in constraints)

        return weighted_sum / total_weight

    def evaluate_line(self, line: str, target_spec: Dict) -> Dict[str, Constraint]:
        """
        Evaluate all constraints for a line.

        Args:
            line: Line text
            target_spec: Target specifications (rhyme, meter, etc.)

        Returns:
            Dictionary of constraint name -> Constraint
        """
        from ..forms import MeterEngine, SoundEngine

        constraints = {}

        # Meter constraint
        if 'meter' in target_spec:
            meter_engine = MeterEngine()
            analysis = meter_engine.analyze_line(line, target_spec['meter'])

            meter_score = 1.0 - analysis.stress_deviation
            constraints['meter'] = self.create_constraint('meter', meter_score)

        # Rhyme constraint (if applicable)
        if 'rhyme_word' in target_spec and target_spec['rhyme_word']:
            sound_engine = SoundEngine()
            words = line.split()

            if words:
                last_word = words[-1].strip('.,!?;:')
                match = sound_engine.check_rhyme(target_spec['rhyme_word'], last_word)

                rhyme_score = match.similarity if match else 0.0
                constraints['rhyme'] = self.create_constraint('rhyme', rhyme_score)

        # Semantic constraint (placeholder)
        # In full implementation, would check semantic coherence
        constraints['semantics'] = self.create_constraint('semantics', 0.8)

        # Affect constraint (placeholder)
        constraints['affect'] = self.create_constraint('affect', 0.7)

        return constraints

    def check_hard_constraints(self, constraints: List[Constraint]) -> bool:
        """
        Check if all hard constraints are satisfied.

        Args:
            constraints: List of constraints

        Returns:
            True if all hard constraints satisfied
        """
        for constraint in constraints:
            if constraint.tier == ConstraintTier.HARD and not constraint.satisfied:
                return False

        return True

    def get_violated_constraints(self, constraints: List[Constraint],
                                 min_score: float = 0.7) -> List[Constraint]:
        """
        Get list of violated constraints.

        Args:
            constraints: List of constraints
            min_score: Minimum score to be considered satisfied

        Returns:
            List of violated constraints
        """
        violated = []

        for constraint in constraints:
            if constraint.score < min_score:
                violated.append(constraint)

        # Sort by tier priority, then weight
        tier_order = {
            ConstraintTier.HARD: 0,
            ConstraintTier.SOFT_HIGH: 1,
            ConstraintTier.SOFT_MED: 2,
            ConstraintTier.SOFT_LOW: 3
        }

        violated.sort(key=lambda c: (tier_order[c.tier], -c.weight))

        return violated


class SteeringPolicy:
    """Defines behavior for constraint satisfaction."""

    def __init__(self, name: str, allow_slant: bool = True,
                 allow_pivot: bool = False, allow_breaks: bool = False,
                 max_repairs: int = 5):
        """
        Initialize steering policy.

        Args:
            name: Policy name
            allow_slant: Allow slant rhyme
            allow_pivot: Allow rhyme-class pivot
            allow_breaks: Allow controlled form-breaking
            max_repairs: Maximum repair iterations
        """
        self.name = name
        self.allow_slant = allow_slant
        self.allow_pivot = allow_pivot
        self.allow_breaks = allow_breaks
        self.max_repairs = max_repairs

    @classmethod
    def strict_sonnet(cls) -> 'SteeringPolicy':
        """Strict sonnet policy."""
        return cls(
            name="strict_sonnet",
            allow_slant=False,
            allow_pivot=False,
            allow_breaks=False,
            max_repairs=10
        )

    @classmethod
    def loose_tercet(cls) -> 'SteeringPolicy':
        """Loose tercet policy."""
        return cls(
            name="loose_tercet",
            allow_slant=True,
            allow_pivot=True,
            allow_breaks=False,
            max_repairs=5
        )

    @classmethod
    def free_verse(cls) -> 'SteeringPolicy':
        """Free verse policy."""
        return cls(
            name="free_verse",
            allow_slant=True,
            allow_pivot=True,
            allow_breaks=True,
            max_repairs=3
        )


def main():
    """CLI for constraint model testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Constraint model utilities")
    parser.add_argument(
        '--line',
        type=str,
        help='Line to evaluate'
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

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    model = ConstraintModel()

    if args.line:
        target_spec = {'meter': args.meter}

        if args.rhyme_word:
            target_spec['rhyme_word'] = args.rhyme_word

        constraints = model.evaluate_line(args.line, target_spec)

        print(f"\nConstraint Evaluation for: '{args.line}'")
        print("=" * 60)

        for name, constraint in constraints.items():
            status = "✓" if constraint.satisfied else "✗"
            print(f"{status} {name.upper()}: {constraint.score:.2f} "
                  f"(weight={constraint.weight:.2f}, tier={constraint.tier.value})")

        utility = model.compute_utility(list(constraints.values()))
        print(f"\nOverall Utility: {utility:.2f}")

        violated = model.get_violated_constraints(list(constraints.values()))

        if violated:
            print("\nViolated Constraints:")
            for c in violated:
                print(f"  - {c.name}: {c.score:.2f}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
