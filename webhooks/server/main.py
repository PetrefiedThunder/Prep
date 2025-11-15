"""FastAPI webhook server for Prep integrations."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
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
