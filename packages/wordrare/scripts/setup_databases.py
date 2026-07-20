#!/usr/bin/env python3
"""
Script to set up all WordRare databases.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.session import get_session_manager
from config import DATABASE_DIR, DATABASE_URL


def main():
    """Create all database tables."""
    print("Setting up WordRare databases...")
    print(f"Database URL: {DATABASE_URL}")

    # Ensure database directory exists
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    # Create session manager and tables
    manager = get_session_manager()
    print("Creating tables...")
    manager.create_tables()

    print("✓ Database setup complete!")
    print("\nCreated tables:")
    print("  - rare_lexicon")
    print("  - lexico")
    print("  - phonetics")
    print("  - freq_profile")
    print("  - semantics")
    print("  - concept_node")
    print("  - concept_edge")
    print("  - poetic_forms")
    print("  - word_record")
    print("  - generation_runs")


if __name__ == "__main__":
    main()
