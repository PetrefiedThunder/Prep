"""High-level DocuSign helpers used by Prep integrations."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional, Tuple

import requests

from Prep.docusign_client import DocuSignClient, DocuSignError

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


def _create_client(*, session: Optional[requests.Session] = None) -> DocuSignClient:
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
    client_user_id: Optional[str] = None,
    ping_url: Optional[str] = None,
    template_id: Optional[str] = None,
    role_name: str = "signer",
    session: Optional[requests.Session] = None,
) -> Tuple[str, str]:
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


def poll_envelope(
    envelope_id: str,
    *,
    interval: int = 10,
    backoff: float = 1.5,
    timeout: int = 300,
    max_interval: int = 60,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """Poll ``envelope_id`` until it completes or fails."""

    if interval <= 0:
        raise ValueError("interval must be greater than zero")
    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")
    if backoff <= 1:
        raise ValueError("backoff must be greater than 1")
    if max_interval <= 0:
        raise ValueError("max_interval must be greater than zero")

    client = _create_client(session=session)
    url = f"{client.base_url}/v2.1/accounts/{client.account_id}/envelopes/{envelope_id}"

    deadline = time.monotonic() + timeout
    current_interval = interval

    while True:
        payload = client._request("get", url)  # pylint: disable=protected-access
        status_raw = payload.get("status")
        if status_raw is None:
            raise DocuSignError("DocuSign response missing status field")

        status = str(status_raw).strip().lower()
        if status == "completed":
            return payload
        if status in TERMINAL_FAILURE_STATES:
            raise DocuSignError(
                f"Envelope {envelope_id} entered terminal state: {status}"
            )

        if time.monotonic() >= deadline:
            raise DocuSignTimeoutError(
                f"Envelope {envelope_id} did not complete within {timeout} seconds"
            )

        time.sleep(current_interval)
        current_interval = min(current_interval * backoff, max_interval)


__all__ = [
    "DocuSignError",
    "DocuSignTimeoutError",
    "poll_envelope",
    "send_sublease",
]
