"""The SQLAlchemy engine: the application's single entry point to the database.

An engine owns a pool of connections. Code never opens connections itself; it asks for a
Session (see session.py), which borrows a connection from the engine and returns it when done.
"""
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.pool import StaticPool

MEMORY = ":memory:"


def create_db_engine(path: str) -> Engine:
    """Engine for a SQLite file, or for an in-memory database when path is ":memory:"."""
    # FastAPI runs plain `def` routes on a thread pool, so connections may be used from
    # threads other than the one that created them; each is still used by one request at a time.
    connect_args = {"check_same_thread": False}
    if path == MEMORY:
        # An in-memory database exists only inside its connection, so every user must share
        # one connection (StaticPool) or each would see a different, empty database.
        engine = create_engine("sqlite://", connect_args=connect_args, poolclass=StaticPool)
    else:
        engine = create_engine(f"sqlite:///{Path(path).as_posix()}", connect_args=connect_args)
    event.listen(engine, "connect", _enable_foreign_keys)
    return engine


def _enable_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
    # SQLite ignores foreign keys unless this is switched on for every new connection.
    dbapi_connection.execute("PRAGMA foreign_keys = ON")
