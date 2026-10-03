"""Sessions: a Session is one unit of work against the database (load objects, change them, commit).

The app creates one session factory at startup; each piece of work (seeding, and each service
call during a request) opens its own short-lived session from it and closes it when finished.
"""
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    # expire_on_commit=False: objects stay readable after commit (e.g. while building a response),
    # instead of triggering a reload from the database on the next attribute access.
    return sessionmaker(engine, expire_on_commit=False)
