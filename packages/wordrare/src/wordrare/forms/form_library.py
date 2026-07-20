"""
Poetic form library - loads and manages form specifications.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from ..config import FORMS_DIR
from ..database import PoeticForm, get_session

logger = logging.getLogger(__name__)


@dataclass
class StanzaSpec:
    """Specification for a stanza."""
    stanza_id: int
    lines: int
    rhyme_pattern: List[Optional[str]]
    meter_pattern: str


@dataclass
class FormSpec:
    """Complete form specification."""
    form_id: str
    name: str
    description: str
    total_lines: int
    stanza_specs: List[StanzaSpec]
    rhyme_pattern: str
    meter_pattern: str
    special_rules: Dict
    device_profile_defaults: Dict

    def get_line_rhyme_symbol(self, line_number: int) -> Optional[str]:
        """
        Get rhyme symbol for a specific line (1-indexed).

        Args:
            line_number: Line number (1-indexed)

        Returns:
            Rhyme symbol or None
        """
        if line_number < 1 or line_number > self.total_lines:
            return None

        current_line = 0
        for stanza in self.stanza_specs:
            if current_line + stanza.lines >= line_number:
                # Line is in this stanza
                local_line = line_number - current_line - 1
                return stanza.rhyme_pattern[local_line]
            current_line += stanza.lines

        return None

    def get_lines_with_rhyme_symbol(self, symbol: str) -> List[int]:
        """
        Get all line numbers that use a specific rhyme symbol.

        Args:
            symbol: Rhyme symbol (e.g., "A", "B1")

        Returns:
            List of line numbers (1-indexed)
        """
        lines = []
        current_line = 0

        for stanza in self.stanza_specs:
            for i, rhyme in enumerate(stanza.rhyme_pattern):
                if rhyme == symbol:
                    lines.append(current_line + i + 1)
            current_line += stanza.lines

        return lines


class FormLibrary:
    """Manages poetic form specifications."""

    def __init__(self, forms_dir: Path = None):
        self.forms_dir = forms_dir or FORMS_DIR
        self.forms_cache: Dict[str, FormSpec] = {}
        self.load_all_forms()

    def load_form_from_json(self, json_path: Path) -> Optional[FormSpec]:
        """
        Load a form specification from JSON file.

        Args:
            json_path: Path to JSON file

        Returns:
            FormSpec object or None
        """
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            # Parse stanza specs
            stanza_specs = []
            for stanza_data in data['stanza_specs']:
                stanza = StanzaSpec(
                    stanza_id=stanza_data['stanza_id'],
                    lines=stanza_data['lines'],
                    rhyme_pattern=stanza_data['rhyme_pattern'],
                    meter_pattern=stanza_data['meter_pattern']
                )
                stanza_specs.append(stanza)

            # Create form spec
            form_spec = FormSpec(
                form_id=data['form_id'],
                name=data['name'],
                description=data['description'],
                total_lines=data['total_lines'],
                stanza_specs=stanza_specs,
                rhyme_pattern=data['rhyme_pattern'],
                meter_pattern=data['meter_pattern'],
                special_rules=data.get('special_rules', {}),
                device_profile_defaults=data.get('device_profile_defaults', {})
            )

            return form_spec

        except Exception as e:
            logger.error(f"Error loading form from {json_path}: {e}")
            return None

    def load_all_forms(self):
        """Load all form specifications from forms directory."""
        if not self.forms_dir.exists():
            logger.warning(f"Forms directory not found: {self.forms_dir}")
            return

        json_files = list(self.forms_dir.glob("*.json"))

        logger.info(f"Loading {len(json_files)} form specifications...")

        for json_file in json_files:
            form_spec = self.load_form_from_json(json_file)

            if form_spec:
                self.forms_cache[form_spec.form_id] = form_spec
                logger.debug(f"Loaded form: {form_spec.name}")

        logger.info(f"Loaded {len(self.forms_cache)} forms")

    def get_form(self, form_id: str) -> Optional[FormSpec]:
        """
        Get a form specification by ID.

        Args:
            form_id: Form identifier

        Returns:
            FormSpec or None
        """
        return self.forms_cache.get(form_id)

    def list_forms(self) -> List[str]:
        """
        List all available form IDs.

        Returns:
            List of form IDs
        """
        return list(self.forms_cache.keys())

    def save_to_database(self):
        """Save all loaded forms to database."""
        with get_session() as session:
            for form_id, form_spec in self.forms_cache.items():
                # Check if exists
                existing = session.query(PoeticForm).filter_by(form_id=form_id).first()

                # Convert stanza specs to serializable format
                stanza_specs_data = [
                    {
                        'stanza_id': s.stanza_id,
                        'lines': s.lines,
                        'rhyme_pattern': s.rhyme_pattern,
                        'meter_pattern': s.meter_pattern
                    }
                    for s in form_spec.stanza_specs
                ]

                if existing:
                    # Update
                    existing.name = form_spec.name
                    existing.stanza_specs = stanza_specs_data
                    existing.rhyme_pattern = form_spec.rhyme_pattern
                    existing.meter_pattern = form_spec.meter_pattern
                    existing.special_rules = form_spec.special_rules
                    existing.device_profile_defaults = form_spec.device_profile_defaults
                    existing.description = form_spec.description
                else:
                    # Create
                    poetic_form = PoeticForm(
                        form_id=form_id,
                        name=form_spec.name,
                        stanza_specs=stanza_specs_data,
                        rhyme_pattern=form_spec.rhyme_pattern,
                        meter_pattern=form_spec.meter_pattern,
                        special_rules=form_spec.special_rules,
                        device_profile_defaults=form_spec.device_profile_defaults,
                        description=form_spec.description
                    )
                    session.add(poetic_form)

        logger.info(f"Saved {len(self.forms_cache)} forms to database")

    def create_form_spec(self, form_id: str, name: str, description: str,
                        stanza_specs: List[Dict], meter_pattern: str,
                        special_rules: Dict = None,
                        device_profile_defaults: Dict = None) -> FormSpec:
        """
        Programmatically create a form specification.

        Args:
            form_id: Unique form identifier
            name: Human-readable name
            description: Form description
            stanza_specs: List of stanza specification dicts
            meter_pattern: Meter pattern name
            special_rules: Optional special rules dict
            device_profile_defaults: Optional device defaults dict

        Returns:
            FormSpec object
        """
        # Parse stanza specs
        stanzas = []
        total_lines = 0

        for spec in stanza_specs:
            stanza = StanzaSpec(
                stanza_id=spec['stanza_id'],
                lines=spec['lines'],
                rhyme_pattern=spec['rhyme_pattern'],
                meter_pattern=spec.get('meter_pattern', meter_pattern)
            )
            stanzas.append(stanza)
            total_lines += stanza.lines

        # Build rhyme pattern string
        rhyme_symbols = []
        for stanza in stanzas:
            rhyme_symbols.extend([s if s else '_' for s in stanza.rhyme_pattern])
        rhyme_pattern = ' '.join(rhyme_symbols)

        form_spec = FormSpec(
            form_id=form_id,
            name=name,
            description=description,
            total_lines=total_lines,
            stanza_specs=stanzas,
            rhyme_pattern=rhyme_pattern,
            meter_pattern=meter_pattern,
            special_rules=special_rules or {},
            device_profile_defaults=device_profile_defaults or {}
        )

        # Add to cache
        self.forms_cache[form_id] = form_spec

        return form_spec


def main():
    """Command-line interface for form library."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage poetic forms")
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available forms'
    )
    parser.add_argument(
        '--show',
        type=str,
        help='Show details for specific form'
    )
    parser.add_argument(
        '--save-db',
        action='store_true',
        help='Save forms to database'
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    library = FormLibrary()

    if args.list:
        print("\nAvailable Poetic Forms:")
        for form_id in library.list_forms():
            form = library.get_form(form_id)
            print(f"  {form_id}: {form.name} ({form.total_lines} lines)")

    elif args.show:
        form = library.get_form(args.show)
        if form:
            print(f"\nForm: {form.name}")
            print(f"ID: {form.form_id}")
            print(f"Description: {form.description}")
            print(f"Total Lines: {form.total_lines}")
            print(f"Rhyme Pattern: {form.rhyme_pattern}")
            print(f"Meter: {form.meter_pattern}")
            print(f"\nStanzas:")
            for stanza in form.stanza_specs:
                print(f"  Stanza {stanza.stanza_id}: {stanza.lines} lines, {stanza.rhyme_pattern}")
            print(f"\nSpecial Rules: {json.dumps(form.special_rules, indent=2)}")
        else:
            print(f"Form '{args.show}' not found")

    elif args.save_db:
        library.save_to_database()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
