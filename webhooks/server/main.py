"""FastAPI webhook server for Prep integrations."""

from __future__ import annotations

"""FastAPI application that verifies and routes Prep webhook events."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

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

    message = f"{timestamp}.".encode() + body
    digest = hmac.new(secret.encode("utf-8"), msg=message, digestmod="sha256")
    return digest.hexdigest()


def parse_signature_header(signature_header: str) -> dict[str, str]:
    """Parse the Prep signature header into its components."""

    parts: dict[str, str] = {}
    for part in signature_header.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        parts[key.strip()] = value.strip()
    return parts


async def verify_webhook_request(request: Request, *, expected_event: str) -> dict[str, Any]:
    """Validate the incoming webhook request and return its JSON payload."""

    try:
        settings = get_settings()
    except RuntimeError as exc:
        logger.error("Webhook settings are not configured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Webhook server misconfigured"
        ) from exc

    signature_header = request.headers.get(SIGNATURE_HEADER)
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signature header"
        )

    parts = parse_signature_header(signature_header)
    timestamp = parts.get(HEADER_TIMESTAMP_KEY)
    signature = parts.get(HEADER_SIGNATURE_KEY)
    if not timestamp or not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature header"
        )

    try:
        timestamp_int = int(timestamp)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature timestamp"
        ) from exc

    now = int(time.time())
    skew = abs(now - timestamp_int)
    if skew > settings.max_timestamp_skew_seconds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signature timestamp is outside the accepted window",
        )

    raw_body = await request.body()

    expected_signature = compute_signature(settings.webhook_secret, timestamp, raw_body)
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        ) from exc

    event_type = payload.get("type")
    if event_type != expected_event:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unexpected event type")

    return payload


app = FastAPI(title="Prep Webhook Receiver", version="1.0.0")


async def _handle_event(request: Request, event_type: str) -> dict[str, Any]:
    payload = await verify_webhook_request(request, expected_event=event_type)
    event_id = payload.get("id", "unknown")
    logger.info("Received webhook %s (id=%s)", event_type, event_id)
    return {"status": "accepted", "event": event_type, "id": event_id}


@app.post("/webhooks/fees.updated")
async def fees_updated(request: Request) -> dict[str, Any]:
    """Handle the fees.updated webhook."""

    return await _handle_event(request, "fees.updated")


@app.post("/webhooks/requirements.updated")
async def requirements_updated(request: Request) -> dict[str, Any]:
    """Handle the requirements.updated webhook."""

    return await _handle_event(request, "requirements.updated")


@app.post("/webhooks/policy.decision")
async def policy_decision(request: Request) -> dict[str, Any]:
    """Handle the policy.decision webhook."""

    return await _handle_event(request, "policy.decision")


__all__ = [
    "app",
    "compute_signature",
    "get_settings",
    "parse_signature_header",
    "verify_webhook_request",
]
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from fastapi import Depends, FastAPI, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError


def _configure_logging() -> None:
    """Configure structured logging for the webhook receiver."""

    level_name = os.getenv("PREP_WEBHOOK_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # The app may run under uvicorn which configures logging itself. Avoid
    # duplicating handlers if they already exist.
    if logging.getLogger().handlers:
        logging.getLogger().setLevel(level)
    else:  # pragma: no cover - depends on runtime environment
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )


_configure_logging()


logger = logging.getLogger("prep.webhooks")


@dataclass(slots=True)
class Settings:
    """Runtime configuration for the webhook receiver."""

    secret: str
    max_skew: timedelta = timedelta(minutes=5)


@lru_cache(maxsize=1)
def _load_settings() -> Settings:
    """Return cached application settings derived from environment variables."""

    secret = os.getenv("PREP_WEBHOOK_SECRET")
    if not secret:
        raise RuntimeError("PREP_WEBHOOK_SECRET environment variable is required")

    skew_override = os.getenv("PREP_WEBHOOK_MAX_SKEW_SECONDS")
    if skew_override:
        try:
            max_skew = timedelta(seconds=int(skew_override))
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise RuntimeError("PREP_WEBHOOK_MAX_SKEW_SECONDS must be an integer") from exc
    else:
        max_skew = timedelta(minutes=5)

    return Settings(secret=secret, max_skew=max_skew)


def get_settings() -> Settings:
    """Dependency wrapper that exposes cached settings to request handlers."""

    return _load_settings()


class WebhookEnvelope(BaseModel):
    """Pydantic model describing the Prep webhook payload schema."""

    type: str = Field(description="Event type identifier")
    data: Mapping[str, Any] | None = Field(default=None, description="Event body")
    context: Mapping[str, Any] | None = Field(
        default=None, description="Optional metadata included with the event"
    )
    emitted_at: datetime | None = Field(
        default=None,
        description="Timestamp supplied by Prep when the event was emitted",
    )


EventHandler = Callable[[WebhookEnvelope, str], Awaitable[Mapping[str, Any] | None]]


def _validate_timestamp(timestamp_header: str, *, max_skew: timedelta) -> datetime:
    """Parse and validate the Prep-Timestamp header."""

    try:
        timestamp = datetime.fromtimestamp(int(timestamp_header), tz=UTC)
    except (ValueError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Prep-Timestamp header",
        ) from exc

    now = datetime.now(tz=UTC)
    if timestamp < now - max_skew or timestamp > now + max_skew:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prep-Timestamp outside of allowed skew",
        )

    return timestamp


def _verify_signature(
    *,
    body: bytes,
    timestamp: str,
    signature: str,
    settings: Settings,
) -> None:
    """Validate the HMAC signature supplied with the webhook."""

    message = f"{timestamp}.".encode() + body
    expected = hmac.new(
        settings.secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Prep-Signature header",
        )


async def _handle_fees_updated(event: WebhookEnvelope, event_id: str) -> Mapping[str, Any] | None:
    logger.info("Processed fees update", extra={"event_id": event_id, "type": event.type})
    return {"fee_items": len(event.data or {})}


async def _handle_requirements_updated(
    event: WebhookEnvelope, event_id: str
) -> Mapping[str, Any] | None:
    logger.info("Processed requirements update", extra={"event_id": event_id, "type": event.type})
    return {"requirements": list((event.data or {}).keys())}


async def _handle_policy_decision(
    event: WebhookEnvelope, event_id: str
) -> Mapping[str, Any] | None:
    logger.info("Processed policy decision", extra={"event_id": event_id, "type": event.type})
    return {"decision": (event.data or {}).get("decision")}


HANDLERS: dict[str, EventHandler] = {
    "fees.updated": _handle_fees_updated,
    "requirements.updated": _handle_requirements_updated,
    "policy.decision": _handle_policy_decision,
}


app = FastAPI(title="Prep Webhook Receiver", version="0.1.0")


@app.get("/healthz", include_in_schema=False)
async def healthcheck() -> Mapping[str, str]:
    """Lightweight health probe for runtime monitoring."""

    return {"status": "ok"}


@app.post("/webhooks/prep")
async def receive_webhook(
    request: Request,
    prep_signature: str = Header(..., alias="Prep-Signature"),
    prep_timestamp: str = Header(..., alias="Prep-Timestamp"),
    prep_event_id: str = Header(..., alias="Prep-Event-Id"),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Validate signature headers and dispatch Prep webhook events."""

    body = await request.body()
    _validate_timestamp(prep_timestamp, max_skew=settings.max_skew)
    _verify_signature(
        body=body,
        timestamp=prep_timestamp,
        signature=prep_signature,
        settings=settings,
    )

    try:
        envelope = WebhookEnvelope.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=json.loads(exc.json()),
        ) from exc

    handler = HANDLERS.get(envelope.type)
    if handler is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unhandled event type: {envelope.type}",
        )

    result = await handler(envelope, prep_event_id)
    return JSONResponse(
        {
            "status": "accepted",
            "eventId": prep_event_id,
            "processedAt": datetime.now(tz=UTC).isoformat(),
            "details": result or {},
        }
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(_: Request, exc: RuntimeError) -> JSONResponse:
    """Return a JSON response when the receiver is misconfigured."""

    logger.error("Webhook receiver misconfiguration: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "webhook receiver misconfigured", "detail": str(exc)},
    )
