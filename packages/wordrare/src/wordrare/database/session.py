"""
Database session management.
"""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator, List, Tuple

from ..config import DATABASE_URL
from .models import Base

logger = logging.getLogger(__name__)

_PHON_ALTER: List[Tuple[str, str]] = [
    ("syllable_phones", "JSON"),
    ("syllable_keys", "JSON"),
    ("assonance_keys", "JSON"),
    ("end_keys", "JSON"),
]
_WORD_ALTER: List[Tuple[str, str]] = [
    ("syllable_keys", "JSON"),
    ("end_key_2", "VARCHAR(256)"),
    ("end_key_3", "VARCHAR(256)"),
]


class SessionManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        self.engine = create_engine(
            self.database_url,
            echo=False,
            pool_pre_ping=True,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def create_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)
        self.ensure_schema()

    def ensure_schema(self):
        """ALTER existing SQLite tables to add columns create_all cannot migrate."""
        with self.engine.connect() as conn:
            for table, cols in (("phonetics", _PHON_ALTER), ("word_record", _WORD_ALTER)):
                try:
                    existing = {
                        r[1]
                        for r in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                    }
                except Exception:
                    continue
                for name, typ in cols:
                    if name not in existing:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {typ}"))
                        logger.info("ensure_schema: added %s.%s", table, name)
            conn.commit()

    def drop_tables(self):
        """Drop all tables from the database."""
        Base.metadata.drop_all(bind=self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Global session manager instance
_session_manager = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
        _session_manager.create_tables()
    return _session_manager


def get_session() -> Generator[Session, None, None]:
    """Convenience function to get a database session."""
    manager = get_session_manager()
    return manager.get_session()
