from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime

import pytest

from etl import crawler


class StubResponse:
    def __init__(self, status: int, body: bytes = b"", raise_for_status: Exception | None = None):
        self.status = status
        self._body = body
        self._raise_for_status = raise_for_status

    async def read(self) -> bytes:
        return self._body

    def raise_for_status(self) -> None:
        if self._raise_for_status:
            raise self._raise_for_status
        if 400 <= self.status < 600:
            raise RuntimeError(f"HTTP {self.status}")

    async def __aenter__(self) -> StubResponse:
        return self

    async def __aexit__(self, *exc_info) -> None:
        return None


class StubSession:
    def __init__(self, responses: list[StubResponse]):
        self._responses = responses
        self.requests: list[str] = []

    def get(self, url: str):
        self.requests.append(url)
        response = self._responses.pop(0)

        class _Ctx:
            async def __aenter__(self_inner):
                return response

            async def __aexit__(self_inner, exc_type, exc, tb):
                return False

        return _Ctx()

    async def close(self) -> None:
        return None


class StubS3:
    def __init__(self):
        self.calls: list[dict] = []

    def put_object(self, **kwargs):
        self.calls.append(kwargs)


@pytest.mark.asyncio
async def test_process_urls_success(monkeypatch):
    session = StubSession([StubResponse(200, b"hello")])
    s3 = StubS3()

    summary = await crawler.process_urls(
        ["https://example.com/ca/doc.pdf"],
        session=session,
        s3_client=s3,
        run_date=datetime(2024, 1, 2, tzinfo=UTC),
    )

    assert summary == {"success": 1, "failed": 0}
    assert len(s3.calls) == 1
    call = s3.calls[0]
    assert call["Bucket"] == crawler.DEFAULT_BUCKET
    assert call["Key"] == "2024-01-02/ca/doc.pdf"
    expected_hash = hashlib.sha256(b"hello").hexdigest()
    assert call["Metadata"] == {"sha256": expected_hash}


@pytest.mark.asyncio
async def test_fetch_retries_with_backoff(monkeypatch):
    responses = [StubResponse(500), StubResponse(502), StubResponse(200, b"ok")]
    session = StubSession(responses)
    s3 = StubS3()

    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    summary = await crawler.process_urls(
        ["https://example.com/nv/rule.txt"],
        session=session,
        s3_client=s3,
        run_date=datetime(2024, 3, 1, tzinfo=UTC),
        sleep=fake_sleep,
    )

    assert summary == {"success": 1, "failed": 0}
    assert sleeps == [1, 2]
    assert len(s3.calls) == 1
    assert s3.calls[0]["Key"] == "2024-03-01/nv/rule.txt"


@pytest.mark.asyncio
async def test_failure_after_max_attempts():
    responses = [
        StubResponse(500),
        StubResponse(503),
        StubResponse(502),
        StubResponse(501),
        StubResponse(500),
    ]
    session = StubSession(responses)
    s3 = StubS3()

    summary = await crawler.process_urls(
        ["https://example.com/wa/doc.pdf"],
        session=session,
        s3_client=s3,
        run_date=datetime(2024, 4, 4, tzinfo=UTC),
        sleep=lambda *_: asyncio.sleep(0),
    )

    assert summary == {"success": 0, "failed": 1}
    assert s3.calls == []
