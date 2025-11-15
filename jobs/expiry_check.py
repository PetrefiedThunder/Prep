"""Daily job for identifying soon-to-expire Certificates of Insurance."""

from __future__ import annotations

import asyncio
import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

try:  # pragma: no cover - exercised via integration tests
    from sqlalchemy import select  # type: ignore
    from sqlalchemy.orm import Session  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - allow running without SQLAlchemy installed
    select = None  # type: ignore
    Session = Any  # type: ignore

try:  # pragma: no cover - optional dependency during testing
    from prep.models.db import SessionLocal  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fall back when SQLAlchemy isn't available
    SessionLocal = None  # type: ignore

try:  # pragma: no cover - optional during unit tests
    from prep.models.orm import COIDocument  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - tests may stub this dependency
    COIDocument = Any  # type: ignore
from prep.settings import get_settings

logger = logging.getLogger(__name__)


class SMSClient(Protocol):
    """Protocol describing the interface for SMS delivery."""

    def send_sms(self, *, to: str, body: str) -> None:  # pragma: no cover - interface
        """Send an SMS message."""


class EmailClient(Protocol):
    """Protocol describing the interface for email delivery."""

    def send_email(
        self, *, to: str, subject: str, body: str
    ) -> None:  # pragma: no cover - interface
        """Send an email message."""


@dataclass(slots=True)
class ExpirySummary:
    """Summary of a COI expiry scan."""

    total_documents: int
    sms_sent: int
    emails_sent: int
    skipped: int

    def as_dict(self) -> dict[str, int]:
        """Return a dictionary representation for structured logging."""

        return {
            "total_documents": self.total_documents,
            "sms_sent": self.sms_sent,
            "emails_sent": self.emails_sent,
            "skipped": self.skipped,
        }


class TwilioSMSClient:
    """Lightweight Twilio SMS client that logs dispatched messages."""

    def __init__(self, *, from_number: str | None) -> None:
        self.from_number = from_number
        self._logger = logging.getLogger(f"{__name__}.TwilioSMSClient")

    def send_sms(self, *, to: str, body: str) -> None:
        if not self.from_number:
            self._logger.warning(
                "Skipping SMS dispatch; Twilio sender number is not configured", to_number=to
            )
            return
        if not to:
            self._logger.warning("Skipping SMS dispatch; destination phone number missing")
            return

        self._logger.info(
            "Twilio SMS dispatched",
            extra={
                "from_number": self.from_number,
                "to_number": to,
                "body": body,
            },
        )


class EmailAlertClient:
    """Simple email client that logs outbound compliance alerts."""

    def __init__(self, *, sender: str | None) -> None:
        self.sender = sender
        self._logger = logging.getLogger(f"{__name__}.EmailAlertClient")

    def send_email(self, *, to: str, subject: str, body: str) -> None:
        if not self.sender:
            self._logger.warning(
                "Skipping email dispatch; alert sender address is not configured", to_email=to
            )
            return
        if not to:
            self._logger.warning(
                "Skipping email dispatch; destination address missing", subject=subject
            )
            return

        self._logger.info(
            "Compliance email dispatched",
            extra={
                "from_email": self.sender,
                "to_email": to,
                "subject": subject,
                "body": body,
            },
        )


SessionFactory = Callable[[], Any]


def _query_expiring_documents(
    session: Session, start: datetime, cutoff: datetime
) -> list[COIDocument]:
    """Return COI documents expiring between ``start`` and ``cutoff`` inclusive."""

    if select is None or SessionLocal is None or COIDocument is Any:  # pragma: no cover - env guard
        raise RuntimeError("SQLAlchemy is required to query COI documents")

    stmt = (
        select(COIDocument)
        .where(COIDocument.expiry_date.is_not(None))
        .where(COIDocument.expiry_date >= start)
        .where(COIDocument.expiry_date <= cutoff)
    )
    return list(session.execute(stmt).scalars())


def _normalize_expiry(expiry: datetime) -> datetime:
    if expiry.tzinfo is None:
        return expiry.replace(tzinfo=UTC)
    return expiry.astimezone(UTC)


def _days_until(expiry: datetime, reference: datetime) -> int:
    delta = expiry - reference
    return max(0, math.ceil(delta.total_seconds() / 86400))


def run_expiry_check(
    *,
    now: datetime | None = None,
    session_factory: SessionFactory | None = SessionLocal,
    sms_client: SMSClient | None = None,
    email_client: EmailClient | None = None,
) -> ExpirySummary:
    """Scan for COIs expiring within 30 days and dispatch notifications."""

    settings = get_settings()
    sms_client = sms_client or TwilioSMSClient(from_number=settings.twilio_from_number)
    email_client = email_client or EmailAlertClient(sender=settings.alert_email_sender)

    sms_recipient = settings.compliance_ops_phone
    email_recipient = settings.compliance_ops_email

    if now is None:
        now = datetime.now(UTC)
    now = now.replace(tzinfo=UTC) if now.tzinfo is None else now.astimezone(UTC)

    cutoff = now + timedelta(days=30)

    if session_factory is None:
        raise RuntimeError("A session_factory must be provided when SQLAlchemy is unavailable")

    session = session_factory()
    try:
        documents = _query_expiring_documents(session, now, cutoff)
    finally:
        session.close()

    sms_sent = 0
    emails_sent = 0
    skipped = 0

    for document in documents:
        expiry = document.expiry_date
        if expiry is None:
            skipped += 1
            continue

        normalized_expiry = _normalize_expiry(expiry)
        days_until = _days_until(normalized_expiry, now)

        message = "Certificate of Insurance '%s' expires on %s (%d days remaining)." % (
            document.filename,
            normalized_expiry.date().isoformat(),
            days_until,
        )
        subject = f"COI expiring in {days_until} day{'s' if days_until != 1 else ''}"

        dispatched = False

        if sms_recipient:
            sms_client.send_sms(to=sms_recipient, body=message)
            sms_sent += 1
            dispatched = True
        else:
            logger.debug(
                "No compliance operations phone configured; skipping SMS alert",
                extra={"document_id": str(document.id)},
            )

        email_body = f"{message}\n\nDocument ID: {document.id}\nChecksum: {document.checksum}"
        if email_recipient:
            email_client.send_email(to=email_recipient, subject=subject, body=email_body)
            emails_sent += 1
            dispatched = True
        else:
            logger.debug(
                "No compliance operations email configured; skipping email alert",
                extra={"document_id": str(document.id)},
            )

        if not dispatched:
            skipped += 1

    summary = ExpirySummary(
        total_documents=len(documents),
        sms_sent=sms_sent,
        emails_sent=emails_sent,
        skipped=skipped,
    )

    logger.info("COI expiry check completed", extra=summary.as_dict())
    return summary


async def run_expiry_check_async(
    *,
    now: datetime | None = None,
    session_factory: SessionFactory = SessionLocal,
    sms_client: SMSClient | None = None,
    email_client: EmailClient | None = None,
) -> ExpirySummary:
    """Async wrapper around :func:`run_expiry_check` for scheduler integration."""

    return await asyncio.to_thread(
        run_expiry_check,
        now=now,
        session_factory=session_factory,
        sms_client=sms_client,
        email_client=email_client,
    )


__all__ = [
    "EmailAlertClient",
    "ExpirySummary",
    "TwilioSMSClient",
    "run_expiry_check",
    "run_expiry_check_async",
]
