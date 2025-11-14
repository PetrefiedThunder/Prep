"""Insurance certificate issuance helpers."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from prep.database.connection import AsyncSessionLocal
from prep.models import Booking, COIDocument, Kitchen
from prep.observability.metrics import (
    INTEGRATION_SYNC_FAILURES,
    INTEGRATION_SYNC_SUCCESS,
)
from prep.regulatory.apis.insurance import (
    CertificateIssueResult,
    InsuranceAPIError,
    InsuranceVerificationAPI,
)

logger = logging.getLogger(__name__)


async def issue_certificate_for_booking(booking_id: str) -> None:
    """Issue a certificate of insurance for the given booking if configured."""

    try:
        booking_uuid = uuid.UUID(booking_id)
    except ValueError:
        logger.error("Invalid booking id %s for certificate issuance", booking_id)
        return

    async with AsyncSessionLocal() as session:
        booking = await session.get(Booking, booking_uuid)
        if booking is None:
            logger.warning("Booking %s not found for certificate issuance", booking_id)
            return

        kitchen = await session.get(Kitchen, booking.kitchen_id)
        if kitchen is None:
            logger.warning("Kitchen %s not found for certificate issuance", booking.kitchen_id)
            return

        insurance_metadata = kitchen.insurance_info or {}
        provider = str(insurance_metadata.get("provider") or "").lower()
        policy_number = insurance_metadata.get("policy_number")
        insured_name = insurance_metadata.get("insured_name") or kitchen.name

        if not provider or not policy_number:
            logger.info(
                "Kitchen %s does not have insurance metadata to auto-issue certificate", kitchen.id
            )
            return

        api = InsuranceVerificationAPI()
        try:
            certificate = await api.issue_certificate(
                provider,
                policy_number,
                insured_name=insured_name,
                reference_id=str(booking.id),
            )
        except InsuranceAPIError as exc:
            INTEGRATION_SYNC_FAILURES.labels(integration="insurance").inc()
            logger.exception("Failed to issue certificate via %s: %s", provider, exc)
            return

        await _persist_certificate(session, certificate, booking, kitchen)
        INTEGRATION_SYNC_SUCCESS.labels(integration="insurance").inc()
        logger.info("Issued %s certificate for booking %s", certificate.provider, booking.id)


async def _persist_certificate(
    session: AsyncSession,
    certificate: CertificateIssueResult,
    booking: Booking,
    kitchen: Kitchen,
) -> None:
    """Persist certificate metadata and update kitchen insurance info."""

    checksum_source = certificate.certificate_url or f"{certificate.provider}-{booking.id}"
    checksum = hashlib.sha256(checksum_source.encode("utf-8")).hexdigest()

    document = COIDocument(
        filename=f"{certificate.provider}-{booking.id}.pdf",
        content_type="application/pdf",
        file_size=int(certificate.raw.get("file_size") or 0),
        checksum=checksum,
        valid=True,
        expiry_date=certificate.expires_at,
        policy_number=certificate.policy_number,
        insured_name=certificate.insured_name or kitchen.name,
        validation_errors=None,
    )
    session.add(document)

    updated_metadata = dict(kitchen.insurance_info or {})
    updated_metadata["latest_certificate"] = {
        "provider": certificate.provider,
        "issued_at": certificate.issued_at.isoformat(),
        "url": certificate.certificate_url,
        "booking_id": str(booking.id),
        "reference_id": certificate.reference_id,
    }
    kitchen.insurance_info = updated_metadata

    await session.commit()


def issue_certificate_for_booking_sync(booking_id: str) -> None:
    """Synchronous entrypoint compatible with FastAPI background tasks."""

    try:
        asyncio.run(issue_certificate_for_booking(booking_id))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.create_task(issue_certificate_for_booking(booking_id))


__all__ = [
    "issue_certificate_for_booking",
    "issue_certificate_for_booking_sync",
]
