"""Engine, session factory and the `Base` declarative class.

`get_db` is the FastAPI dependency every router/repository uses to obtain a
session; tests override it to point at a temporary SQLite file per test.
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine(database_url: str) -> Engine:
    connect_args = {}
    if database_url.startswith("sqlite"):
        # Needed because a single SQLite connection is otherwise pinned to the
        # thread that created it; FastAPI may serve a request on a different
        # thread than the one that opened the session.
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args)


engine: Engine = _make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# The one FastAPI dependency annotation every router uses for a DB session —
# `Annotated[Session, Depends(get_db)]` rather than a `Depends(...)` default
# value, which ruff's bugbear check (B008) correctly flags as a mutable/
# call-in-default-argument smell in the general case.
DbSession = Annotated[Session, Depends(get_db)]
