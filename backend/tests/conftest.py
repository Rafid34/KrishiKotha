"""Shared fixtures: in-memory DB seeded with fixtures, and a TestClient bound to it."""
from __future__ import annotations

import os

# Tests never read the real `.env` data mode: the NASA clients must stay mockable.
os.environ["DATA_MODE"] = "live"

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.app.config import get_settings  # noqa: E402

get_settings.cache_clear()


@pytest.fixture()
def session_factory() -> Iterator[sessionmaker[Session]]:
    """Empty in-memory SQLite database with every table created and static data seeded."""
    from backend.app import models  # noqa: F401
    from backend.app.db import Base
    from backend.app.seed import seed

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        seed(session)
    yield factory
    engine.dispose()


@pytest.fixture()
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    """TestClient whose `get_db` dependency uses the in-memory database."""
    from backend.app.db import get_db
    from backend.app.main import create_app

    app = create_app()

    def override() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
