"""Service layer for managing DocuSign-backed sublease contracts."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from docusign_client import DocuSignClient, DocuSignError
from prep.models.orm import Booking, SubleaseContract, SubleaseContractStatus
from prep.platform.service import PlatformError
from prep.settings import Settings


@dataclass(slots=True)
class SubleaseContractSendResult:
    """Return payload for sending a sublease contract."""

    contract: SubleaseContract
    signing_url: str


class SubleaseContractService:
    """Coordinate DocuSign envelope workflows for booking subleases."""

    def __init__(
        self,
        session: AsyncSession,
        docusign_client: DocuSignClient,
        s3_client: BaseClient,
        settings: Settings,
    ) -> None:
        self._session = session
        self._docusign = docusign_client
        self._s3 = s3_client
        self._settings = settings

    async def send_contract(
        self,
        *,
        booking_id: UUID,
        signer_email: str,
        signer_name: Optional[str],
        return_url: Optional[str],
    ) -> SubleaseContractSendResult:
        booking = await self._session.get(Booking, booking_id)
        if booking is None:
            raise PlatformError("Booking not found", status_code=404)

        template_id = self._settings.docusign_sublease_template_id
        if not template_id:
            raise PlatformError("DocuSign template not configured", status_code=500)

        destination_url = return_url or str(self._settings.docusign_return_url)
        ping_url = str(self._settings.docusign_ping_url) if self._settings.docusign_ping_url else None

        try:
            envelope_id, sign_url = await asyncio.to_thread(
                self._docusign.send_template,
                template_id=template_id,
                signer_email=signer_email,
                signer_name=signer_name or signer_email,
                return_url=destination_url,
                client_user_id=str(booking.id),
                ping_url=ping_url,
            )
        except DocuSignError as exc:  # pragma: no cover - network failure path
            raise PlatformError("Failed to send DocuSign envelope", status_code=502) from exc

        contract = await self._get_contract_by_booking(booking_id)
        if contract is None:
            contract = SubleaseContract(
                booking_id=booking_id,
                envelope_id=envelope_id,
                status=SubleaseContractStatus.SENT,
                signer_email=signer_email,
                signer_name=signer_name or signer_email,
                sign_url=sign_url,
                last_checked_at=datetime.now(UTC),
            )
            self._session.add(contract)
        else:
            contract.envelope_id = envelope_id
            contract.status = SubleaseContractStatus.SENT
            contract.signer_email = signer_email
            contract.signer_name = signer_name or signer_email
            contract.sign_url = sign_url
            contract.completed_at = None
            contract.document_s3_bucket = None
            contract.document_s3_key = None
            contract.last_checked_at = datetime.now(UTC)

        await self._session.commit()
        await self._session.refresh(contract)
        return SubleaseContractSendResult(contract=contract, signing_url=sign_url)

    async def get_contract_status(self, booking_id: UUID) -> SubleaseContract:
        contract = await self._get_contract_by_booking(booking_id)
        if contract is None:
            raise PlatformError("No sublease contract found", status_code=404)

        try:
            status_value = await asyncio.to_thread(
                self._docusign.get_envelope_status, contract.envelope_id
            )
        except DocuSignError as exc:  # pragma: no cover - network failure path
            raise PlatformError("Failed to fetch DocuSign envelope status", status_code=502) from exc

        contract.status = self._map_status(status_value)
        contract.last_checked_at = datetime.now(UTC)

        if contract.status is SubleaseContractStatus.COMPLETED and contract.document_s3_key is None:
            await self._persist_signed_document(contract)

        await self._session.commit()
        await self._session.refresh(contract)
        return contract

    async def _get_contract_by_booking(self, booking_id: UUID) -> SubleaseContract | None:
        stmt: Select[tuple[SubleaseContract]] = select(SubleaseContract).where(
            SubleaseContract.booking_id == booking_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _persist_signed_document(self, contract: SubleaseContract) -> None:
        bucket = self._settings.contracts_s3_bucket
        if not bucket:
            raise PlatformError("Contracts S3 bucket not configured", status_code=500)

        try:
            document_bytes = await asyncio.to_thread(
                self._docusign.download_document, contract.envelope_id
            )
        except DocuSignError as exc:  # pragma: no cover - network failure path
            raise PlatformError("Failed to download signed contract", status_code=502) from exc

        key = f"sublease-contracts/{contract.booking_id}.pdf"
        try:
            await asyncio.to_thread(
                self._s3.put_object,
                Bucket=bucket,
                Key=key,
                Body=document_bytes,
                ContentType="application/pdf",
            )
        except (BotoCoreError, ClientError) as exc:  # pragma: no cover - network failure path
            raise PlatformError("Failed to store signed contract", status_code=502) from exc

        now = datetime.now(UTC)
        contract.document_s3_bucket = bucket
        contract.document_s3_key = key
        contract.completed_at = now

    @staticmethod
    def _map_status(status: str) -> SubleaseContractStatus:
        normalized = status.lower()
        if normalized == "completed":
            return SubleaseContractStatus.COMPLETED
        if normalized == "created":
            return SubleaseContractStatus.CREATED
        if normalized in {"sent", "delivered", "inprocess"}:
            return SubleaseContractStatus.SENT
        if normalized == "declined":
            return SubleaseContractStatus.DECLINED
        if normalized == "voided":
            return SubleaseContractStatus.VOIDED
        return SubleaseContractStatus.ERROR
