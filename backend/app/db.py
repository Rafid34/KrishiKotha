"""SQLAlchemy engine, session dependency and table creation."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def make_engine(url: str | None = None) -> Engine:
    """Create an engine; ensures the parent folder of a SQLite file exists."""
    url = url or get_settings().database_url
    if url.startswith("sqlite:///") and ":memory:" not in url:
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_all(bind: Engine | None = None) -> None:
    """Create every table that does not exist yet."""
    from . import models  # noqa: F401  (register models)

    Base.metadata.create_all(bind or engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session."""
    with SessionLocal() as session:
        yield session
