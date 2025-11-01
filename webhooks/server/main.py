"""FastAPI webhook server for Prep integrations."""
from __future__ import annotations

import hmac
import json
import logging
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status

LOG_LEVEL = os.getenv("PREP_WEBHOOK_LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("prep.webhooks.server")

SIGNATURE_HEADER = "x-prep-signature"
HEADER_TIMESTAMP_KEY = "t"
HEADER_SIGNATURE_KEY = "v1"
DEFAULT_MAX_SKEW_SECONDS = 300


@dataclass(frozen=True)
class Settings:
    """Configuration for the webhook server."""

    webhook_secret: str
    max_timestamp_skew_seconds: int = DEFAULT_MAX_SKEW_SECONDS


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache application settings.

    Raises:
        RuntimeError: If the webhook secret or skew setting is invalid.
    """

    secret = os.getenv("PREP_WEBHOOK_SECRET")
    if not secret:
        raise RuntimeError("PREP_WEBHOOK_SECRET must be configured")

    skew_raw = os.getenv("PREP_WEBHOOK_MAX_SKEW", str(DEFAULT_MAX_SKEW_SECONDS))
    try:
        skew = int(skew_raw)
    except ValueError as exc:  # pragma: no cover - defensive programming
        raise RuntimeError("PREP_WEBHOOK_MAX_SKEW must be an integer") from exc

    if skew <= 0:
        raise RuntimeError("PREP_WEBHOOK_MAX_SKEW must be positive")

    return Settings(webhook_secret=secret, max_timestamp_skew_seconds=skew)


def compute_signature(secret: str, timestamp: str, body: bytes) -> str:
    """Compute the webhook signature using the configured secret."""

    message = f"{timestamp}.".encode("utf-8") + body
    digest = hmac.new(secret.encode("utf-8"), msg=message, digestmod="sha256")
    return digest.hexdigest()


def parse_signature_header(signature_header: str) -> Dict[str, str]:
    """Parse the Prep signature header into its components."""

    parts: Dict[str, str] = {}
    for part in signature_header.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        parts[key.strip()] = value.strip()
    return parts


async def verify_webhook_request(request: Request, *, expected_event: str) -> Dict[str, Any]:
    """Validate the incoming webhook request and return its JSON payload."""

    try:
        settings = get_settings()
    except RuntimeError as exc:
        logger.error("Webhook settings are not configured: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Webhook server misconfigured") from exc

    signature_header = request.headers.get(SIGNATURE_HEADER)
    if not signature_header:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signature header")

    parts = parse_signature_header(signature_header)
    timestamp = parts.get(HEADER_TIMESTAMP_KEY)
    signature = parts.get(HEADER_SIGNATURE_KEY)
    if not timestamp or not signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature header")

    try:
        timestamp_int = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature timestamp") from exc

    now = int(time.time())
    skew = abs(now - timestamp_int)
    if skew > settings.max_timestamp_skew_seconds:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Signature timestamp is outside the accepted window")

    raw_body = await request.body()

    expected_signature = compute_signature(settings.webhook_secret, timestamp, raw_body)
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from exc

    event_type = payload.get("type")
    if event_type != expected_event:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unexpected event type")

    return payload


app = FastAPI(title="Prep Webhook Receiver", version="1.0.0")


async def _handle_event(request: Request, event_type: str) -> Dict[str, Any]:
    payload = await verify_webhook_request(request, expected_event=event_type)
    event_id = payload.get("id", "unknown")
    logger.info("Received webhook %s (id=%s)", event_type, event_id)
    return {"status": "accepted", "event": event_type, "id": event_id}


@app.post("/webhooks/fees.updated")
async def fees_updated(request: Request) -> Dict[str, Any]:
    """Handle the fees.updated webhook."""

    return await _handle_event(request, "fees.updated")


@app.post("/webhooks/requirements.updated")
async def requirements_updated(request: Request) -> Dict[str, Any]:
    """Handle the requirements.updated webhook."""

    return await _handle_event(request, "requirements.updated")


@app.post("/webhooks/policy.decision")
async def policy_decision(request: Request) -> Dict[str, Any]:
    """Handle the policy.decision webhook."""

    return await _handle_event(request, "policy.decision")


__all__ = [
    "app",
    "compute_signature",
    "get_settings",
    "parse_signature_header",
    "verify_webhook_request",
]
