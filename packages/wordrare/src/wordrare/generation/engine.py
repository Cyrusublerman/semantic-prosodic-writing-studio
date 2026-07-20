"""
Main poem generation engine - ties all components together.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import asdict

from ..database import GenerationRun, get_session
from .generation_spec import GenerationSpec
from .theme_selector import ThemeSelector
from .scaffolding import Scaffolder
from .line_realizer import LineRealizer

logger = logging.getLogger(__name__)


class GeneratedPoem:
    """Represents a generated poem with metadata."""

    def __init__(self, lines: List[str], spec: GenerationSpec,
                 run_id: str, metrics: Dict = None, annotations: Dict = None):
        self.lines = lines
        self.spec = spec
        self.run_id = run_id
        self.metrics = metrics or {}
        self.annotations = annotations or {}

    @property
    def text(self) -> str:
        """Get poem as formatted text."""
        return '\n'.join(self.lines)

    def __str__(self):
        return self.text

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'run_id': self.run_id,
            'text': self.text,
            'lines': self.lines,
            'spec': self.spec.to_dict(),
            'metrics': self.metrics,
            'annotations': self.annotations
        }


class PoemGenerator:
    """Main poem generation engine."""

    def __init__(self):
        self.theme_selector = ThemeSelector()
        self.scaffolder = Scaffolder()

    def generate(self, spec: GenerationSpec = None, **kwargs) -> GeneratedPoem:
        """
        Generate a poem.

        Args:
            spec: Generation specification (optional)
            **kwargs: Override spec parameters

        Returns:
            GeneratedPoem
        """
        # Create or update spec
        if spec is None:
            spec = GenerationSpec()

        # Apply kwargs overrides
        for key, value in kwargs.items():
            if hasattr(spec, key):
                setattr(spec, key, value)

        # Validate spec
        errors = spec.validate()
        if errors:
            raise ValueError(f"Invalid generation spec: {errors}")

        # Generate run ID
        run_id = str(uuid.uuid4())[:8]

        logger.info(f"Starting generation run {run_id}")
        logger.info(f"Form: {spec.form}, Theme: {spec.theme}, Rarity: {spec.rarity_bias}")

        # Build semantic palette
        logger.info("Building semantic palette...")
        semantic_palette = self.theme_selector.build_semantic_palette(spec)

        # Build scaffold
        logger.info("Building poem scaffold...")
        scaffold = self.scaffolder.build_scaffold(spec)

        # Realize lines
        logger.info("Realizing lines...")
        realizer = LineRealizer(spec, semantic_palette)
        lines = realizer.realize_poem(scaffold)

        # Apply devices (if enabled)
        if spec.device_profile:
            logger.info("Applying poetic devices...")
            lines = self._apply_devices(lines, spec, semantic_palette)

        # Global pass (thematic smoothing)
        logger.info("Applying global pass...")
        lines = self._global_pass(lines, spec)

        # Create poem object
        poem = GeneratedPoem(
            lines=lines,
            spec=spec,
            run_id=run_id,
            metrics={},
            annotations={'semantic_palette': {
                'theme_concepts': semantic_palette.get('theme_concepts', []),
                'motifs': semantic_palette.get('motifs', []),
                'bridges': semantic_palette.get('metaphor_bridges', [])
            }}
        )

        # Save to database
        if not spec.debug_mode:
            self._save_generation_run(poem)

        logger.info(f"Generation complete: {run_id}")

        return poem

    def _apply_devices(self, lines: List[str], spec: GenerationSpec,
                      semantic_palette: Dict) -> List[str]:
        """
        Apply poetic devices to lines.

        Args:
            lines: Original lines
            spec: Generation spec
            semantic_palette: Semantic palette

        Returns:
            Modified lines
        """
        # Placeholder for device application
        # In full implementation, would add:
        # - Enjambment (break syntax across lines)
        # - Caesura (mid-line pauses)
        # - Internal rhyme
        # - Metaphor bridges (cross-domain connections)
        # - Motif recurrence

        logger.debug("Device application not yet implemented")
        return lines

    def _global_pass(self, lines: List[str], spec: GenerationSpec) -> List[str]:
        """
        Perform global thematic smoothing.

        Args:
            lines: Original lines
            spec: Generation spec

        Returns:
            Modified lines
        """
        # Placeholder for global pass
        # In full implementation, would:
        # - Analyze thematic progression
        # - Identify weak transitions
        # - Adjust word choices for coherence
        # - Balance emotional intensity
        # - Ensure contrasts are deliberate

        logger.debug("Global pass not yet implemented")
        return lines

    def _save_generation_run(self, poem: GeneratedPoem):
        """Save generation run to database."""
        try:
            with get_session() as session:
                run = GenerationRun(
                    run_id=poem.run_id,
                    input_spec=poem.spec.to_dict(),
                    form_id=poem.spec.form,
                    theme=poem.spec.theme,
                    parameter_snapshot=poem.spec.to_dict(),
                    poem_text=poem.text,
                    debug_annotations=poem.annotations,
                    metrics=poem.metrics
                )
                session.add(run)

            logger.info(f"Saved generation run {poem.run_id} to database")

        except Exception as e:
            logger.error(f"Failed to save generation run: {e}")

    def generate_batch(self, spec: GenerationSpec, count: int = 5) -> List[GeneratedPoem]:
        """
        Generate multiple poems with the same spec.

        Args:
            spec: Generation specification
            count: Number of poems to generate

        Returns:
            List of GeneratedPoem objects
        """
        poems = []

        for i in range(count):
            logger.info(f"Generating poem {i+1}/{count}")
            try:
                poem = self.generate(spec)
                poems.append(poem)
            except Exception as e:
                logger.error(f"Failed to generate poem {i+1}: {e}")

        return poems

    def list_forms(self) -> List[str]:
        """List available poetic forms."""
        return self.scaffolder.form_library.list_forms()

    def get_form_info(self, form_id: str) -> Dict:
        """Get information about a form."""
        form = self.scaffolder.form_library.get_form(form_id)

        if not form:
            return {}

        return {
            'form_id': form.form_id,
            'name': form.name,
            'description': form.description,
            'total_lines': form.total_lines,
            'rhyme_pattern': form.rhyme_pattern,
            'meter_pattern': form.meter_pattern
        }


def main():
    """CLI for poem generation."""
    import argparse

    parser = argparse.ArgumentParser(description="WordRare Poem Generator")

    parser.add_argument(
        '--form',
        type=str,
        default='haiku',
        help='Poetic form'
    )
    parser.add_argument(
        '--theme',
        type=str,
        help='Poem theme'
    )
    parser.add_argument(
        '--rarity',
        type=float,
        default=0.5,
        help='Rarity bias (0.0-1.0)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=1,
        help='Number of poems to generate'
    )
    parser.add_argument(
        '--list-forms',
        action='store_true',
        help='List available forms'
    )
    parser.add_argument(
        '--preset',
        choices=['melancholic_nature', 'joyful_simple', 'mysterious_archaic'],
        help='Use a preset configuration'
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    generator = PoemGenerator()

    if args.list_forms:
        print("\nAvailable Poetic Forms:")
        for form_id in generator.list_forms():
            info = generator.get_form_info(form_id)
            print(f"  {form_id}: {info.get('name', 'Unknown')}")
        return

    # Create spec
    if args.preset:
        if args.preset == 'melancholic_nature':
            spec = GenerationSpec.preset_melancholic_nature()
        elif args.preset == 'joyful_simple':
            spec = GenerationSpec.preset_joyful_simple()
        else:
            spec = GenerationSpec.preset_mysterious_archaic()
    else:
        spec = GenerationSpec(
            form=args.form,
            theme=args.theme,
            rarity_bias=args.rarity
        )

    # Generate
    if args.count == 1:
        poem = generator.generate(spec)
        print("\n" + "=" * 60)
        print(poem.text)
        print("=" * 60)
        print(f"\nRun ID: {poem.run_id}")
        print(f"Form: {spec.form}")
        print(f"Theme: {spec.theme}")
        print(f"Rarity: {spec.rarity_bias}")
    else:
        poems = generator.generate_batch(spec, count=args.count)
        for i, poem in enumerate(poems, 1):
            print(f"\n{'=' * 60}")
            print(f"Poem {i}/{args.count} (ID: {poem.run_id})")
            print("=" * 60)
            print(poem.text)


if __name__ == "__main__":
    main()
