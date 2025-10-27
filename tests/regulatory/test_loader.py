"""Tests for regulatory loader normalization helpers."""

from prep.regulatory.loader import _normalize_regdoc


def test_normalize_regdoc_sets_defaults() -> None:
    payload = {
        "sha256_hash": "abc123",
        "title": "Sample",
        "state": "CA",
    }

    normalized = _normalize_regdoc(payload)

    assert normalized["country_code"] == "US"
    assert normalized["state_province"] == "CA"
    assert normalized["raw_payload"]["sha256_hash"] == "abc123"


def test_normalize_regdoc_respects_explicit_fields() -> None:
    payload = {
        "sha256_hash": "def456",
        "country_code": "CA",
        "state_province": "ON",
        "state": "CA",
    }

    normalized = _normalize_regdoc(payload)

    assert normalized["country_code"] == "CA"
    assert normalized["state_province"] == "ON"
from __future__ import annotations

import logging
from fnmatch import fnmatch
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from prep.cache import RedisProtocol
from prep.models.orm import Base
from prep.regulatory.loader import load_regdoc
from prep.regulatory.models import RegDoc


class RecordingRedis(RedisProtocol):
    """In-memory Redis spy that records invalidated keys."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.deleted_keys: list[str] = []

    async def get(self, key: str) -> Any:
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: Any) -> None:
        self.store[key] = value

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self.store:
                self.store.pop(key, None)
                self.deleted_keys.append(key)
                removed += 1
        return removed

    async def keys(self, pattern: str) -> list[str]:
        return [key for key in self.store if fnmatch(key, pattern)]


@pytest.fixture()
def session() -> Session:
    engine: Engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    try:
        with factory() as db_session:
            yield db_session
            db_session.rollback()
    finally:
        engine.dispose()


def _sample_payload(summary: str = "New regulation summary") -> dict[str, Any]:
    return {
        "sha256_hash": "abc123",
        "jurisdiction": "US",
        "state": "CA",
        "city": "San Francisco",
        "doc_type": "health",
        "title": "Health inspection guidance",
        "summary": summary,
        "source_url": "https://example.com/regulation",
        "raw_payload": {"source": "fixture"},
    }


def test_load_regdoc_inserts_and_invalidates_rules_cache(session: Session, caplog: pytest.LogCaptureFixture) -> None:
    redis = RecordingRedis()
    redis.store.update({"rules:alpha": "1", "rules:beta": "2", "other:key": "noop"})

    with caplog.at_level(logging.INFO):
        inserted = load_regdoc(session, [_sample_payload()], redis_client=redis)

    assert inserted == 1
    assert sorted(redis.deleted_keys) == ["rules:alpha", "rules:beta"]
    doc = session.execute(select(RegDoc).where(RegDoc.sha256_hash == "abc123")).scalar_one()
    assert doc.title == "Health inspection guidance"
    assert "Invalidated" in caplog.text


def test_load_regdoc_updates_and_invalidates_on_changes(session: Session, caplog: pytest.LogCaptureFixture) -> None:
    original_payload = _sample_payload()
    load_regdoc(session, [original_payload], redis_client=RecordingRedis())

    redis = RecordingRedis()
    redis.store.update({"rules:fresh": "cached"})

    updated_payload = _sample_payload(summary="Updated regulation summary")

    with caplog.at_level(logging.INFO):
        inserted = load_regdoc(session, [updated_payload], redis_client=redis)

    assert inserted == 0
    assert redis.deleted_keys == ["rules:fresh"]
    updated = session.execute(select(RegDoc).where(RegDoc.sha256_hash == "abc123")).scalar_one()
    assert updated.summary == "Updated regulation summary"
    assert "Invalidated" in caplog.text
