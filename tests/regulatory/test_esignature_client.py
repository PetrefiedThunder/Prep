from __future__ import annotations

from typing import Any

import pytest

from prep.regulatory.apis.esignature import DocuSignAPIError, DocuSignClient

pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture()
def anyio_backend() -> str:
    """Limit anyio to the asyncio backend for these tests."""

    return "asyncio"


def _build_client() -> DocuSignClient:
    return DocuSignClient(account_id="12345", base_url="https://example.com/api")


async def test_poll_envelope_until_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client()
    responses: list[dict[str, Any]] = [
        {"status": "sent"},
        {"status": "delivered"},
        {"status": "completed", "envelopeId": "env-1"},
    ]

    async def fake_get_envelope(envelope_id: str) -> dict[str, Any]:
        return responses.pop(0)

    sleep_calls: list[int] = []

    async def fake_sleep(seconds: int) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(client, "get_envelope", fake_get_envelope)
    monkeypatch.setattr("prep.regulatory.apis.esignature.asyncio.sleep", fake_sleep)

    summary = await client.poll_envelope("env-1", interval=5)

    assert summary.status == "completed"
    assert summary.envelope_id == "env-1"
    assert sleep_calls == [5, 5]


async def test_poll_envelope_raises_for_terminal_state(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client()
    responses: list[dict[str, Any]] = [
        {"status": "sent"},
        {"status": "voided"},
    ]

    async def fake_get_envelope(envelope_id: str) -> dict[str, Any]:
        return responses.pop(0)

    async def fake_sleep(seconds: int) -> None:
        pass

    monkeypatch.setattr(client, "get_envelope", fake_get_envelope)
    monkeypatch.setattr("prep.regulatory.apis.esignature.asyncio.sleep", fake_sleep)

    with pytest.raises(DocuSignAPIError):
        await client.poll_envelope("env-2", interval=2)


async def test_poll_envelope_requires_positive_interval() -> None:
    client = _build_client()
    with pytest.raises(ValueError):
        await client.poll_envelope("env-3", interval=0)


async def test_poll_envelope_errors_when_status_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_client()

    async def fake_get_envelope(envelope_id: str) -> dict[str, Any]:
        return {"envelopeId": envelope_id}

    async def fake_sleep(seconds: int) -> None:
        pass

    monkeypatch.setattr(client, "get_envelope", fake_get_envelope)
    monkeypatch.setattr("prep.regulatory.apis.esignature.asyncio.sleep", fake_sleep)

    with pytest.raises(DocuSignAPIError):
        await client.poll_envelope("env-4", interval=1)
