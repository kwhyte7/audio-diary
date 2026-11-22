import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import db


@pytest.fixture
def db_session(monkeypatch):
    """Point db.py at an in-memory SQLite database for fast, isolated tests."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.Base.metadata.create_all(engine)

    TestingSession = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    monkeypatch.setattr(db, "SessionLocal", TestingSession)

    yield TestingSession

    db.Base.metadata.drop_all(engine)
    engine.dispose()
