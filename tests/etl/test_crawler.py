import asyncio
from unittest import mock

import aiohttp
import pytest

from etl import crawler


class MockResponse:
    def __init__(self, status: int, body: bytes = b"payload") -> None:
        self.status = status
        self._body = body

    async def read(self) -> bytes:
        return self._body

    def raise_for_status(self) -> None:
        if self.status >= 400 and not (500 <= self.status < 600):
            raise aiohttp.ClientError(f"status {self.status}")

    async def __aenter__(self) -> "MockResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return False


class MockContextManager:
    def __init__(self, response: MockResponse) -> None:
        self.response = response

    async def __aenter__(self) -> MockResponse:
        return self.response

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return False


@pytest.mark.parametrize(
    "line, expected",
    [
        (
            "ca,https://example.com/file.pdf",
            crawler.CrawlTarget("ca", "https://example.com/file.pdf"),
        ),
        ("ny\thttps://example.com", crawler.CrawlTarget("ny", "https://example.com")),
        ("wa https://example.com/path", crawler.CrawlTarget("wa", "https://example.com/path")),
    ],
)
def test_parse_targets_variants(line, expected):
    targets = crawler.parse_targets([line])
    assert targets == [expected]


def test_parse_targets_invalid():
    with pytest.raises(ValueError):
        crawler.parse_targets(["invalid-line"])


def test_fetch_with_backoff_retries_on_5xx(monkeypatch):
    responses = [MockResponse(500), MockResponse(502), MockResponse(200, b"ok")]

    def fake_get(url):
        return MockContextManager(responses.pop(0))

    session = mock.Mock()
    session.get = mock.Mock(side_effect=fake_get)

    sleep_calls = []

    async def fake_sleep(delay):
        sleep_calls.append(delay)

    result = asyncio.run(
        crawler.fetch_with_backoff(
            session,
            "https://example.com",
            max_attempts=5,
            base_delay=0.1,
            sleep=fake_sleep,
        )
    )

    assert result == b"ok"
    assert sleep_calls == [0.1, 0.2]


def test_fetch_and_upload_puts_object(monkeypatch):
    session = mock.Mock()
    session.get = mock.Mock(return_value=MockContextManager(MockResponse(200, b"body")))

    s3_client = mock.Mock()

    async def fake_sleep(delay):
        raise AssertionError("sleep should not be called")

    async def fake_to_thread(func, *args, **kwargs):
        func(*args, **kwargs)

    key, digest = asyncio.run(
        crawler.fetch_and_upload(
            session,
            s3_client,
            crawler.CrawlTarget("ca", "https://example.com/file.pdf"),
            bucket="prep-etl-raw",
            date_prefix="2024-05-01",
            sleep=fake_sleep,
            to_thread=fake_to_thread,
        )
    )

    assert key == "2024-05-01/ca/file.pdf"
    assert digest == "230d8358dc8e8890b4c58deeb62912ee2f20357ae92a5cc861b98e68fe31acb5"
    s3_client.put_object.assert_called_once()
    call = s3_client.put_object.call_args
    assert call.kwargs["Bucket"] == "prep-etl-raw"
    assert call.kwargs["Key"] == key
    assert call.kwargs["Body"] == b"body"
    assert call.kwargs["Metadata"] == {"sha256": digest}
