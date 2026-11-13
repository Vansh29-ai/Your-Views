"""Test fixtures. A temporary SQLite database and the deterministic lexical embedder are used so
the suite never depends on network access or on the sentence-transformer model."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEMP_DIR = Path(tempfile.mkdtemp(prefix="yourviews-tests-"))
os.environ["YV_DATABASE_URL"] = f"sqlite:///{(TEMP_DIR / 'test.db').as_posix()}"
os.environ["YV_ENVIRONMENT"] = "test"
os.environ["YV_ENABLE_SCHEDULER"] = "false"
os.environ["YV_INGEST_ON_STARTUP"] = "false"
os.environ["YV_LOG_LEVEL"] = "WARNING"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database.connection import Base, SessionLocal, engine  # noqa: E402
from app.database.init_db import init_db  # noqa: E402
from app.ml.embeddings import HashingEmbedder, embedding_service  # noqa: E402

embedding_service._embedder = HashingEmbedder()


def _wipe_database() -> None:
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
        try:
            connection.execute(text("DELETE FROM event_fts"))
        except Exception:
            pass


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    init_db()
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_database(prepare_database):
    _wipe_database()
    yield
    _wipe_database()


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(clean_database):
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
