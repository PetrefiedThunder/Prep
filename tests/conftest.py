import os
import asyncio
import pytest

from sqlalchemy.orm import Session

# Ensure SQLite is used in tests unless explicitly overridden
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from prep.models.db import engine, SessionLocal, init_db  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    # pytest-asyncio compat on some CI images
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    # create all tables once for the in-memory SQLite; each test gets fresh session
    init_db()
    yield


@pytest.fixture
def db_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
