"""Build the database: create every table from the models, then load the fixtures.

The database is a disposable copy of the fixtures: `build_database` deletes and rebuilds it on
every start, so every run (and every test) begins from the same known state.
"""
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.dialects import sqlite
from sqlalchemy.schema import CreateIndex, CreateTable

from app.db.engine import MEMORY, create_db_engine
from app.db.seed import SeedError, load_history, seed_database
from app.db.session import make_session_factory
from app.models import Base

__all__ = ["MEMORY", "SCHEMA_PATH", "SeedError", "build_database", "render_schema_sql"]

# Generated reference copy of the schema (see render_schema_sql); the models are the source of truth.
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def build_database(path: str, seed_path: str, history_path: str | None = None) -> Engine:
    """Delete any existing database file, create all tables from the models, and load the fixtures.

    `history_path` is optional: when it is None or the file doesn't exist, no performance
    history is loaded (history endpoints return []).
    """
    if path != MEMORY:
        for suffix in ("", "-journal", "-wal", "-shm"):
            Path(path + suffix).unlink(missing_ok=True)
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    engine = create_db_engine(path)
    Base.metadata.create_all(engine)
    with make_session_factory(engine).begin() as session:  # one transaction: all or nothing
        seed_database(session, seed_path)
        if history_path is not None and Path(history_path).exists():
            load_history(session, history_path)
    return engine


def render_schema_sql() -> str:
    """The CREATE statements SQLite runs for our models, as documentation (schema.sql)."""
    dialect = sqlite.dialect()
    statements = []
    for table in Base.metadata.sorted_tables:
        statements.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
        statements.extend(
            str(CreateIndex(index).compile(dialect=dialect)).strip() + ";"
            for index in sorted(table.indexes, key=lambda i: i.name or "")
        )
    header = (
        "-- GENERATED from app/models by `python -m app.db.schema_dump`. Do not edit by hand:\n"
        "-- change the models, then regenerate. tests/unit/test_models.py fails if this file is stale.\n"
    )
    return header + "\n" + "\n\n".join(statements) + "\n"
