"""SQLAlchemy engine/session helpers for SPWS workspace SQLite."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

_ENGINE_CACHE: dict[str, Engine] = {}


def sqlite_url(path: str | Path) -> str:
    resolved = Path(path).expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{resolved.as_posix()}"


def get_engine(path: str | Path, *, echo: bool = False) -> Engine:
    url = sqlite_url(path)
    cached = _ENGINE_CACHE.get(url)
    if cached is not None:
        return cached
    engine = create_engine(url, echo=echo, future=True)
    # SQLite foreign keys
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    _ENGINE_CACHE[url] = engine
    return engine


def get_session(path: str | Path) -> Session:
    engine = get_engine(path)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    return factory()


def _migrate_missing_columns(engine: Engine) -> None:
    """Add columns introduced after initial create_all (SQLite has no ALTER sync)."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {col["name"] for col in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            col_type = column.type.compile(dialect=engine.dialect)
            # Existing rows cannot satisfy NOT NULL without a default; add as nullable.
            ddl = f"ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type}"
            with engine.begin() as conn:
                conn.execute(text(ddl))


def ensure_schema(path: str | Path) -> Engine:
    """Create all SQLAlchemy tables if missing (compat with WorkspaceStore)."""
    engine = get_engine(path)
    Base.metadata.create_all(engine)
    _migrate_missing_columns(engine)
    return engine


__all__ = [
    "Base",
    "ensure_schema",
    "get_engine",
    "get_session",
    "sqlite_url",
]
