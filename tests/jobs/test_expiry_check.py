from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

import jobs.expiry_check as expiry_check
from jobs.expiry_check import run_expiry_check, run_expiry_check_async
from prep.settings import get_settings


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class CaptureSMS:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def send_sms(self, *, to: str, body: str) -> None:
        self.messages.append({"to": to, "body": body})


class CaptureEmail:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def send_email(self, *, to: str, subject: str, body: str) -> None:
        self.messages.append({"to": to, "subject": subject, "body": body})


@dataclass
class _FakeDocument:
    filename: str
    checksum: str
    expiry_date: datetime | None
    id: str = field(default_factory=lambda: str(uuid4()))


class _StubSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _configure_notification_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCE_OPS_EMAIL", "ops@example.com")
    monkeypatch.setenv("COMPLIANCE_OPS_PHONE", "+15555550100")
    monkeypatch.setenv("ALERT_EMAIL_SENDER", "alerts@example.com")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15555550999")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://prep:prep@localhost:5432/prep")
    get_settings.cache_clear()


def test_expiry_check_sends_notifications(monkeypatch: pytest.MonkeyPatch, caplog):
    _configure_notification_settings(monkeypatch)

    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    expiring_soon = _FakeDocument("soon.pdf", "soon", now + timedelta(days=10))
    expiring_later = _FakeDocument("later.pdf", "later", now + timedelta(days=40))
    expiring_very_soon = _FakeDocument("very-soon.pdf", "verysoon", now + timedelta(days=3))

    documents = [expiring_soon, expiring_later, expiring_very_soon]

    def _fake_query(session, start, cutoff):
        return [doc for doc in documents if doc.expiry_date and start <= doc.expiry_date <= cutoff]

    monkeypatch.setattr(expiry_check, "_query_expiring_documents", _fake_query)

    sms = CaptureSMS()
    email = CaptureEmail()

    caplog.set_level(logging.INFO, logger="jobs.expiry_check")

    summary = run_expiry_check(
        now=now,
        session_factory=_StubSession,
        sms_client=sms,
        email_client=email,
    )

    assert summary.total_documents == 2
    assert summary.sms_sent == 2
    assert summary.emails_sent == 2
    assert summary.skipped == 0
    assert len(sms.messages) == 2
    assert all("Certificate of Insurance" in message["body"] for message in sms.messages)
    assert len(email.messages) == 2
    assert any("COI expiry check completed" in record.message for record in caplog.records)

@pytest.mark.anyio
async def test_run_expiry_check_async(monkeypatch: pytest.MonkeyPatch):
    _configure_notification_settings(monkeypatch)

    now = datetime(2024, 5, 1, tzinfo=timezone.utc)
    document = _FakeDocument("async.pdf", "async", now + timedelta(days=2))

    monkeypatch.setattr(
        expiry_check,
        "_query_expiring_documents",
        lambda session, start, cutoff: [doc for doc in [document] if doc.expiry_date and start <= doc.expiry_date <= cutoff],
    )

    sms = CaptureSMS()
    email = CaptureEmail()

    summary = await run_expiry_check_async(
        now=now,
        session_factory=_StubSession,
        sms_client=sms,
        email_client=email,
    )

    assert summary.total_documents == 1
    assert summary.sms_sent == 1
    assert summary.emails_sent == 1
    assert summary.skipped == 0
    assert sms.messages[0]["to"] == "+15555550100"
    assert "async.pdf" in email.messages[0]["body"]
