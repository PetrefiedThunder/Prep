"""Tests for the high-level DocuSign integration helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import pytest

from integrations.docusign_client import (
    DocuSignError,
    DocuSignTimeoutError,
    poll_envelope,
    send_sublease,
)


@dataclass
class _FakeClock:
    """Utility used to simulate ``time.monotonic`` and ``time.sleep``."""

    value: float = 0.0
    sleeps: list[float] | None = None

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        if self.sleeps is not None:
            self.sleeps.append(seconds)
        self.value += seconds


class _StubDocuSignClient:
    """Test double for :class:`DocuSignClient` requests."""

    def __init__(self, responses: Iterable[dict[str, Any]]) -> None:
        self.base_url = "https://demo.docusign.net/restapi"
        self.account_id = "123456"
        self._responses = list(responses)
        self._call_count = 0
        self.calls: list[str] = []
        self.sent_payloads: list[dict[str, Any]] = []

    def send_template(self, **kwargs: Any) -> tuple[str, str]:
        self.calls.append("send_template")
        self.sent_payloads.append(kwargs)
        return ("env-123", "https://sign.docusign.com/embedded")

    def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(method.lower())
        index = min(self._call_count, len(self._responses) - 1)
        self._call_count += 1
        return self._responses[index]


def _install_stub_client(monkeypatch: pytest.MonkeyPatch, stub: _StubDocuSignClient) -> None:
    monkeypatch.setenv("DOCUSIGN_SANDBOX_ACCOUNT_ID", "acct-123")
    monkeypatch.setenv("DOCUSIGN_SANDBOX_ACCESS_TOKEN", "token-abc")
    monkeypatch.setenv("DOCUSIGN_SUBLEASE_TEMPLATE_ID", "tmpl-xyz")
    monkeypatch.setattr(
        "integrations.docusign_client._create_client",
        lambda session=None: stub,
    )


def test_send_sublease_uses_template_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _StubDocuSignClient(responses=[{"status": "completed"}])
    _install_stub_client(monkeypatch, stub)

    envelope_id, signing_url = send_sublease(
        signer_email="tenant@example.com",
        signer_name="Tenant Example",
        return_url="https://prep.example.com/done",
        client_user_id="sublease-1",
        ping_url="https://prep.example.com/ping",
        role_name="Subtenant",
    )

    assert envelope_id == "env-123"
    assert signing_url == "https://sign.docusign.com/embedded"
    assert stub.calls.count("send_template") == 1
    assert stub.sent_payloads[0]["template_id"] == "tmpl-xyz"
    assert stub.sent_payloads[0]["role_name"] == "Subtenant"


def test_send_sublease_allows_template_override(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _StubDocuSignClient(responses=[{"status": "completed"}])
    _install_stub_client(monkeypatch, stub)

    send_sublease(
        signer_email="tenant@example.com",
        signer_name="Tenant Example",
        return_url="https://prep.example.com/done",
        template_id="tmpl-custom",
    )

    # The helper should still delegate to ``send_template`` once.
    assert stub.calls.count("send_template") == 1
    assert stub.sent_payloads[0]["template_id"] == "tmpl-custom"


def test_send_sublease_requires_template_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _StubDocuSignClient(responses=[{"status": "completed"}])
    monkeypatch.setenv("DOCUSIGN_SANDBOX_ACCOUNT_ID", "acct-123")
    monkeypatch.setenv("DOCUSIGN_SANDBOX_ACCESS_TOKEN", "token-abc")
    monkeypatch.delenv("DOCUSIGN_SUBLEASE_TEMPLATE_ID", raising=False)

    monkeypatch.setattr(
        "integrations.docusign_client._create_client",
        lambda session=None: stub,
    )

    with pytest.raises(RuntimeError):
        send_sublease(
            signer_email="tenant@example.com",
            signer_name="Tenant Example",
            return_url="https://prep.example.com/done",
        )


def test_poll_envelope_until_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        {"status": "Sent"},
        {"status": "Completed", "completedDateTime": "2024-01-01T12:00:00Z"},
    ]
    stub = _StubDocuSignClient(responses=responses)
    _install_stub_client(monkeypatch, stub)

    clock = _FakeClock(sleeps=[])
    monkeypatch.setattr("integrations.docusign_client.time.monotonic", clock.monotonic)
    monkeypatch.setattr("integrations.docusign_client.time.sleep", clock.sleep)

    payload = poll_envelope("env-123", interval=5, timeout=20)

    assert payload["status"].lower() == "completed"
    assert clock.sleeps == [5.0]


def test_poll_envelope_raises_on_terminal_state(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [{"status": "sent"}, {"status": "declined"}]
    stub = _StubDocuSignClient(responses=responses)
    _install_stub_client(monkeypatch, stub)

    clock = _FakeClock(sleeps=[])
    monkeypatch.setattr("integrations.docusign_client.time.monotonic", clock.monotonic)
    monkeypatch.setattr("integrations.docusign_client.time.sleep", clock.sleep)

    with pytest.raises(DocuSignError):
        poll_envelope("env-123", interval=3, timeout=30)


def test_poll_envelope_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [{"status": "sent"}]
    stub = _StubDocuSignClient(responses=responses)
    _install_stub_client(monkeypatch, stub)

    clock = _FakeClock(sleeps=[])
    monkeypatch.setattr("integrations.docusign_client.time.monotonic", clock.monotonic)
    monkeypatch.setattr("integrations.docusign_client.time.sleep", clock.sleep)

    with pytest.raises(DocuSignTimeoutError):
        poll_envelope("env-123", interval=5, timeout=10)


def test_poll_envelope_errors_when_status_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [{}, {"status": "completed"}]
    stub = _StubDocuSignClient(responses=responses)
    _install_stub_client(monkeypatch, stub)

    clock = _FakeClock(sleeps=[])
    monkeypatch.setattr("integrations.docusign_client.time.monotonic", clock.monotonic)
    monkeypatch.setattr("integrations.docusign_client.time.sleep", clock.sleep)

    with pytest.raises(DocuSignError):
        poll_envelope("env-123", interval=2, timeout=10)
