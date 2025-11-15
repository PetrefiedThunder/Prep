"""High-level DocuSign helpers used by Prep integrations."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import aiohttp
from docusign_client import DocuSignClient, DocuSignError

DEFAULT_BASE_URL = "https://demo.docusign.net/restapi"
ENV_BASE_URL = "DOCUSIGN_SANDBOX_BASE_URL"
ENV_ACCOUNT_ID = "DOCUSIGN_SANDBOX_ACCOUNT_ID"
ENV_ACCESS_TOKEN = "DOCUSIGN_SANDBOX_ACCESS_TOKEN"
ENV_TEMPLATE_ID = "DOCUSIGN_SUBLEASE_TEMPLATE_ID"

TERMINAL_FAILURE_STATES = {"declined", "voided", "deleted", "error", "expired"}


class DocuSignTimeoutError(TimeoutError):
    """Raised when an envelope fails to complete before the timeout."""


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _create_client(*, session: requests.Session | None = None) -> DocuSignClient:
    base_url = os.getenv(ENV_BASE_URL, DEFAULT_BASE_URL)
    account_id = _require_env(ENV_ACCOUNT_ID)
    access_token = _require_env(ENV_ACCESS_TOKEN)
    return DocuSignClient(
        base_url=base_url,
        account_id=account_id,
        access_token=access_token,
        session=session,
    )


def send_sublease(
    *,
    signer_email: str,
    signer_name: str,
    return_url: str,
    client_user_id: str | None = None,
    ping_url: str | None = None,
    template_id: str | None = None,
    role_name: str = "signer",
    session: requests.Session | None = None,
) -> tuple[str, str]:
    """Send a DocuSign envelope for a sublease template."""

    template_to_use = template_id or _require_env(ENV_TEMPLATE_ID)
    client = _create_client(session=session)
    return client.send_template(
        template_id=template_to_use,
        signer_email=signer_email,
        signer_name=signer_name,
        return_url=return_url,
        role_name=role_name,
        client_user_id=client_user_id,
        ping_url=ping_url,
    )


async def poll_envelope(
    envelope_id: str,
    *,
    interval: int = 10,
    backoff: float = 1.5,
    timeout: int = 300,
    max_interval: int = 60,
    session: aiohttp.ClientSession | None = None,
) -> dict[str, Any]:
    """Poll ``envelope_id`` until it completes or fails."""

    if interval <= 0:
        raise ValueError("interval must be greater than zero")
    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")
    if backoff <= 1:
        raise ValueError("backoff must be greater than 1")
    if max_interval <= 0:
        raise ValueError("max_interval must be greater than zero")

    client = _create_client(session=None)  # TODO: Update _create_client for async
    url = f"{client.base_url}/v2.1/accounts/{client.account_id}/envelopes/{envelope_id}"

    start_time = asyncio.get_event_loop().time()
    deadline = start_time + timeout
    current_interval = interval

    owns_session = session is None
    if owns_session:
        session = aiohttp.ClientSession()

    try:
        while asyncio.get_event_loop().time() < deadline:
            async with session.get(
                url,
                headers={"Authorization": f"Bearer {client.access_token}"},
            ) as response:
                response.raise_for_status()
                payload = await response.json()

            status_raw = payload.get("status")
            if status_raw is None:
                raise DocuSignError("DocuSign response missing status field")

            status = str(status_raw).strip().lower()
            if status == "completed":
                return payload
            if status in TERMINAL_FAILURE_STATES:
                raise DocuSignError(f"Envelope {envelope_id} entered terminal state: {status}")

            await asyncio.sleep(current_interval)
            current_interval = min(current_interval * backoff, max_interval)

        raise DocuSignTimeoutError(
            f"Envelope {envelope_id} did not complete within {timeout} seconds"
        )
    finally:
        if owns_session:
            await session.close()


__all__ = [
    "DocuSignError",
    "DocuSignTimeoutError",
    "poll_envelope",
    "send_sublease",
]
