"""
Comprehensive poem metrics system.

Implements the ranking metrics from BuildGuide Section 4.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import numpy as np

from ..forms import MeterEngine, SoundEngine
from ..database import WordRecord, get_session

logger = logging.getLogger(__name__)


@dataclass
class MeterMetrics:
    """Meter-related metrics."""
    foot_accuracy: float = 0.0  # Proportion of feet matching target
    syllable_deviation: float = 0.0  # 1 - (avg_dev / D_max)
    stress_deviation: float = 0.0  # 1 - (hamming / n)
    rhythm_variance: float = 0.0  # Regularity of stress spacing
    downbeat_alignment: float = 0.0  # Alignment with expected stresses
    syncopation_index: float = 0.0  # Stress on unexpected positions
    stability: float = 0.0  # Consistency across poem
    score: float = 0.0  # Overall meter quality

    def compute_score(self, weights: Dict[str, float] = None) -> float:
        """Compute overall meter score."""
        if weights is None:
            weights = {
                'foot_accuracy': 0.30,
                'syllable_deviation': 0.25,
                'stress_deviation': 0.25,
                'stability': 0.20
            }

        self.score = (
            weights['foot_accuracy'] * self.foot_accuracy +
            weights['syllable_deviation'] * self.syllable_deviation +
            weights['stress_deviation'] * self.stress_deviation +
            weights['stability'] * self.stability
        )

        return self.score


@dataclass
class RhymeMetrics:
    """Rhyme-related metrics."""
    density: float = 0.0  # rhyme-linked positions / eligible positions
    economy: float = 0.0  # 1 - (num_rhyme_classes / max_classes)
    strictness: float = 0.0  # Proportion of perfect rhymes
    stability: float = 0.0  # Consistency of rhyme-class assignment
    score: float = 0.0

    def compute_score(self, weights: Dict[str, float] = None) -> float:
        """Compute overall rhyme score."""
        if weights is None:
            weights = {
                'density': 0.30,
                'strictness': 0.40,
                'economy': 0.15,
                'stability': 0.15
            }

        self.score = (
            weights['density'] * self.density +
            weights['strictness'] * self.strictness +
            weights['economy'] * self.economy +
            weights['stability'] * self.stability
        )

        return self.score


@dataclass
class SemanticMetrics:
    """Semantic coherence metrics."""
    motif_coherence: float = 0.0  # Mean similarity to motif centroid
    theme_coherence: float = 0.0  # 1 - variance of theme tags
    depth: float = 0.0  # rarity × definition complexity
    score: float = 0.0

    def compute_score(self, weights: Dict[str, float] = None) -> float:
        """Compute overall semantic score."""
        if weights is None:
            weights = {
                'motif_coherence': 0.40,
                'theme_coherence': 0.40,
                'depth': 0.20
            }

        self.score = (
            weights['motif_coherence'] * self.motif_coherence +
            weights['theme_coherence'] * self.theme_coherence +
            weights['depth'] * self.depth
        )

        return self.score


@dataclass
class TechniqueMetrics:
    """Metrics for specific technique (alliteration, assonance, etc.)."""
    intensity: float = 0.0  # Fraction of lines containing technique
    density: float = 0.0  # Avg events per line
    regularization: float = 0.0  # 1 - variance of event positions
    variation: float = 0.0  # Scheme distance from other techniques
    score: float = 0.0

    def compute_score(self, weights: Dict[str, float] = None) -> float:
        """Compute overall technique score."""
        if weights is None:
            weights = {
                'intensity': 0.30,
                'density': 0.30,
                'regularization': 0.20,
                'variation': 0.20
            }

        self.score = (
            weights['intensity'] * self.intensity +
            weights['density'] * self.density +
            weights['regularization'] * self.regularization +
            weights['variation'] * self.variation
        )

        return self.score


@dataclass
class LayeringMetrics:
    """Multi-technique layering metrics."""
    layers: float = 0.0  # active techniques / total techniques
    divergence: float = 0.0  # Average inter-technique scheme distance
    score: float = 0.0

    def compute_score(self, weights: Dict[str, float] = None) -> float:
        """Compute overall layering score."""
        if weights is None:
            weights = {'layers': 0.60, 'divergence': 0.40}

        self.score = (
            weights['layers'] * self.layers +
            weights['divergence'] * self.divergence
        )

        return self.score


@dataclass
class PoemMetrics:
    """Complete poem metrics."""
    meter: MeterMetrics = field(default_factory=MeterMetrics)
    rhyme: RhymeMetrics = field(default_factory=RhymeMetrics)
    semantic: SemanticMetrics = field(default_factory=SemanticMetrics)
    techniques: Dict[str, TechniqueMetrics] = field(default_factory=dict)
    layering: LayeringMetrics = field(default_factory=LayeringMetrics)
    total_score: float = 0.0

    def compute_total_score(self, weights: Dict[str, float] = None) -> float:
        """
        Compute overall poem score.

        TOTAL = Σ w_i · R_i
        """
        if weights is None:
            weights = {
                'meter': 0.20,
                'rhyme': 0.20,
                'semantic': 0.25,
                'depth': 0.15,
                'layers': 0.10,
                'variation': 0.10
            }

        # Compute sub-scores
        meter_score = self.meter.compute_score()
        rhyme_score = self.rhyme.compute_score()
        semantic_score = self.semantic.compute_score()
        layering_score = self.layering.compute_score()

        # Aggregate technique scores
        technique_scores = [t.compute_score() for t in self.techniques.values()]
        avg_technique = np.mean(technique_scores) if technique_scores else 0.0

        self.total_score = (
            weights['meter'] * meter_score +
            weights['rhyme'] * rhyme_score +
            weights['semantic'] * semantic_score +
            weights['layers'] * layering_score +
            weights['variation'] * avg_technique
        )

        return self.total_score


class MetricsAnalyzer:
    """Analyzes poems and computes comprehensive metrics."""

    def __init__(self):
        self.meter_engine = MeterEngine()
        self.sound_engine = SoundEngine()

    def analyze_poem(self, lines: List[str], form_spec: Dict = None) -> PoemMetrics:
        """
        Analyze complete poem.

        Args:
            lines: List of line texts
            form_spec: Form specification (meter, rhyme pattern, etc.)

        Returns:
            PoemMetrics object
        """
        metrics = PoemMetrics()

        # Analyze meter
        if form_spec and 'meter' in form_spec:
            metrics.meter = self.analyze_meter(lines, form_spec['meter'])

        # Analyze rhyme
        if form_spec and 'rhyme_pattern' in form_spec:
            metrics.rhyme = self.analyze_rhyme(lines, form_spec['rhyme_pattern'])

        # Analyze semantics
        metrics.semantic = self.analyze_semantics(lines)

        # Analyze techniques
        metrics.techniques = self.analyze_techniques(lines)

        # Analyze layering
        metrics.layering = self.analyze_layering(metrics.techniques)

        # Compute total score
        metrics.compute_total_score()

        return metrics

    def analyze_meter(self, lines: List[str], target_meter: str) -> MeterMetrics:
        """Analyze meter metrics."""
        metrics = MeterMetrics()

        if not lines:
            return metrics

        foot_accuracies = []
        syllable_deviations = []
        stress_deviations = []

        for line in lines:
            analysis = self.meter_engine.analyze_line(line, target_meter)

            foot_accuracies.append(analysis.foot_accuracy)
            syllable_deviations.append(analysis.syllable_deviation)
            stress_deviations.append(analysis.stress_deviation)

        # Aggregate metrics
        metrics.foot_accuracy = np.mean(foot_accuracies)
        metrics.syllable_deviation = 1.0 - np.mean(syllable_deviations) / 3.0
        metrics.syllable_deviation = max(0.0, min(1.0, metrics.syllable_deviation))
        metrics.stress_deviation = 1.0 - np.mean(stress_deviations)

        # Stability (consistency across lines)
        metrics.stability = 1.0 - np.var(foot_accuracies)
        metrics.stability = max(0.0, min(1.0, metrics.stability))

        return metrics

    def analyze_rhyme(self, lines: List[str], rhyme_pattern: str) -> RhymeMetrics:
        """Analyze rhyme metrics."""
        metrics = RhymeMetrics()

        if not lines or not rhyme_pattern:
            return metrics

        # Parse rhyme pattern
        symbols = rhyme_pattern.replace(' ', '')

        # Build rhyme groups
        rhyme_groups = {}
        for i, symbol in enumerate(symbols):
            if i >= len(lines):
                break

            if symbol not in rhyme_groups:
                rhyme_groups[symbol] = []

            # Get last word of line
            words = lines[i].split()
            if words:
                last_word = words[-1].strip('.,!?;:')
                rhyme_groups[symbol].append(last_word)

        # Compute density
        eligible_positions = len([s for s in symbols if s != '_'])
        rhymed_positions = sum(len(g) for g in rhyme_groups.values() if len(g) > 1)
        metrics.density = rhymed_positions / eligible_positions if eligible_positions > 0 else 0

        # Compute economy
        max_classes = len(set(symbols))
        actual_classes = len(rhyme_groups)
        metrics.economy = 1.0 - (actual_classes / max_classes) if max_classes > 0 else 0

        # Compute strictness (check rhyme quality)
        perfect_count = 0
        total_pairs = 0

        for group in rhyme_groups.values():
            if len(group) < 2:
                continue

            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    match = self.sound_engine.check_rhyme(group[i], group[j])
                    total_pairs += 1

                    if match and match.rhyme_type == 'perfect':
                        perfect_count += 1

        metrics.strictness = perfect_count / total_pairs if total_pairs > 0 else 0

        # Stability (placeholder - would check consistency of rhyme class)
        metrics.stability = 0.8

        return metrics

    def analyze_semantics(self, lines: List[str]) -> SemanticMetrics:
        """Analyze semantic metrics."""
        metrics = SemanticMetrics()

        if not lines:
            return metrics

        # Get words from lines
        all_words = []
        for line in lines:
            all_words.extend(line.split())

        # Query word records
        with get_session() as session:
            word_records = []
            for word in all_words:
                record = session.query(WordRecord).filter_by(lemma=word.lower()).first()
                if record:
                    word_records.append(record)

        if not word_records:
            return metrics

        # Compute depth (rarity × complexity)
        avg_rarity = np.mean([r.rarity_score or 0.5 for r in word_records])
        avg_definitions = np.mean([len(r.definitions or []) for r in word_records])

        metrics.depth = avg_rarity * min(1.0, avg_definitions / 3.0)

        # Theme coherence (variance of domain tags)
        all_tags = []
        for record in word_records:
            if record.domain_tags:
                all_tags.extend(record.domain_tags)

        if all_tags:
            # Compute tag diversity (lower = more coherent)
            unique_tags = len(set(all_tags))
            total_tags = len(all_tags)
            diversity = unique_tags / total_tags if total_tags > 0 else 1

            metrics.theme_coherence = 1.0 - diversity
        else:
            metrics.theme_coherence = 0.5

        # Motif coherence (placeholder - would use embeddings)
        metrics.motif_coherence = 0.7

        return metrics

    def analyze_techniques(self, lines: List[str]) -> Dict[str, TechniqueMetrics]:
        """Analyze sound device techniques."""
        techniques = {
            'alliteration': TechniqueMetrics(),
            'assonance': TechniqueMetrics(),
            'consonance': TechniqueMetrics()
        }

        if not lines:
            return techniques

        # Analyze each line for devices
        for line in lines:
            devices = self.sound_engine.analyze_sound_devices(line)

            for device_name, present in devices.items():
                if present and device_name in techniques:
                    techniques[device_name].intensity += 1

        # Normalize intensity
        for technique in techniques.values():
            technique.intensity /= len(lines)

        # Placeholder values for other metrics
        for technique in techniques.values():
            technique.density = technique.intensity * 0.8
            technique.regularization = 0.6
            technique.variation = 0.5

        return techniques

    def analyze_layering(self, techniques: Dict[str, TechniqueMetrics]) -> LayeringMetrics:
        """Analyze multi-technique layering."""
        metrics = LayeringMetrics()

        if not techniques:
            return metrics

        # Count active techniques (intensity > threshold)
        active = sum(1 for t in techniques.values() if t.intensity > 0.2)
        total = len(techniques)

        metrics.layers = active / total if total > 0 else 0

        # Divergence (placeholder - would compute scheme distances)
        metrics.divergence = 0.6

        return metrics


def main():
    """CLI for metrics analysis."""
    import argparse

    parser = argparse.ArgumentParser(description="Poem metrics analysis")
    parser.add_argument(
        '--file',
        type=str,
        help='File containing poem (one line per line)'
    )
    parser.add_argument(
        '--meter',
        type=str,
        default='iambic_pentameter',
        help='Target meter'
    )
    parser.add_argument(
        '--rhyme-pattern',
        type=str,
        help='Rhyme pattern (e.g., "ABAB CDCD")'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.file:
        with open(args.file, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]

        form_spec = {'meter': args.meter}
        if args.rhyme_pattern:
            form_spec['rhyme_pattern'] = args.rhyme_pattern

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_poem(lines, form_spec)

        print("\nPoem Metrics Analysis")
        print("=" * 60)
        print(f"\nMeter Score: {metrics.meter.score:.2f}")
        print(f"  Foot Accuracy: {metrics.meter.foot_accuracy:.2f}")
        print(f"  Syllable Deviation: {metrics.meter.syllable_deviation:.2f}")
        print(f"  Stress Deviation: {metrics.meter.stress_deviation:.2f}")
        print(f"  Stability: {metrics.meter.stability:.2f}")

        print(f"\nRhyme Score: {metrics.rhyme.score:.2f}")
        print(f"  Density: {metrics.rhyme.density:.2f}")
        print(f"  Strictness: {metrics.rhyme.strictness:.2f}")
        print(f"  Economy: {metrics.rhyme.economy:.2f}")

        print(f"\nSemantic Score: {metrics.semantic.score:.2f}")
        print(f"  Motif Coherence: {metrics.semantic.motif_coherence:.2f}")
        print(f"  Theme Coherence: {metrics.semantic.theme_coherence:.2f}")
        print(f"  Depth: {metrics.semantic.depth:.2f}")

        print(f"\nTechniques:")
        for name, technique in metrics.techniques.items():
            print(f"  {name}: {technique.score:.2f} (intensity={technique.intensity:.2f})")

        print(f"\nLayering Score: {metrics.layering.score:.2f}")
        print(f"  Active Layers: {metrics.layering.layers:.2f}")
        print(f"  Divergence: {metrics.layering.divergence:.2f}")

        print(f"\n{'=' * 60}")
        print(f"TOTAL SCORE: {metrics.total_score:.2f}")
        print("=" * 60)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
