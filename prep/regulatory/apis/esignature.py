"""DocuSign e-signature API client helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from .health_departments import BaseAPIClient, RegulatoryAPIError


class DocuSignAPIError(RegulatoryAPIError):
    """Raised when a DocuSign envelope request fails."""


@dataclass(slots=True)
class EnvelopeSummary:
    """Lightweight representation of a DocuSign envelope."""

    envelope_id: str
    status: str
    raw: dict[str, Any]


class DocuSignClient(BaseAPIClient):
    """Minimal async client for polling DocuSign envelope status."""

    DEFAULT_BASE_URL = "https://demo.docusign.net/restapi/v2.1/accounts"

    def __init__(
        self,
        account_id: str,
        *,
        base_url: str | None = None,
        access_token: str | None = None,
        timeout: int = 30,
    ) -> None:
        super().__init__(timeout=timeout)
        if not account_id:
            raise ValueError("account_id is required")
        self.account_id = account_id
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.access_token = access_token

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def get_envelope(self, envelope_id: str) -> dict[str, Any]:
        """Fetch the latest details for ``envelope_id``."""

        if not envelope_id:
            raise ValueError("envelope_id must be provided")
        url = f"{self.base_url}/{self.account_id}/envelopes/{envelope_id}"
        return await self._fetch_json(url, headers=self._headers())

    async def poll_envelope(self, envelope_id: str, interval: int = 30) -> EnvelopeSummary:
        """Poll ``envelope_id`` until the envelope is completed.

        Args:
            envelope_id: The DocuSign envelope identifier.
            interval: Number of seconds to wait between polls. Must be positive.

        Returns:
            An :class:`EnvelopeSummary` describing the completed envelope.

        Raises:
            ValueError: If ``interval`` is not positive or the envelope id is empty.
            DocuSignAPIError: If the envelope enters a terminal failure state or the
                response payload is invalid.
        """

        if interval <= 0:
            raise ValueError("interval must be greater than zero")
        if not envelope_id:
            raise ValueError("envelope_id must be provided")

        terminal_failures = {"declined", "voided", "deleted", "error", "expired"}

        while True:
            payload = await self.get_envelope(envelope_id)
            status_raw = payload.get("status")
            if status_raw is None:
                raise DocuSignAPIError(f"Envelope {envelope_id} response missing status")
            status = str(status_raw).strip().lower()

            if status == "completed":
                return EnvelopeSummary(
                    envelope_id=envelope_id,
                    status=status,
                    raw=payload,
                )
            if status in terminal_failures:
                raise DocuSignAPIError(f"Envelope {envelope_id} entered terminal state: {status}")

            await asyncio.sleep(interval)


__all__ = ["DocuSignClient", "DocuSignAPIError", "EnvelopeSummary"]
