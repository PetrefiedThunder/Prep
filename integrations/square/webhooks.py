"""Square webhook verification and payload helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


class SquareWebhookVerificationError(Exception):
    """Raised when webhook validation fails."""


@dataclass(frozen=True)
class PrepTimeUpdate:
    """Represents a prep-time update emitted by Square KDS."""

    location_id: str
    order_id: str
    prep_time_seconds: int
    ready_at: datetime
    updated_at: datetime

    @property
    def prep_time_minutes(self) -> float:
        """Expose the prep time in minutes for convenience."""

        return self.prep_time_seconds / 60


class SquareWebhookVerifier:
    """Utility for verifying Square webhook signatures."""

    def __init__(self, signature_key: str, notification_url: str) -> None:
        if not signature_key:
            raise ValueError("signature_key must be provided")
        if not notification_url:
            raise ValueError("notification_url must be provided")
        self._signature_key = signature_key
        self._notification_url = notification_url

    def compute_signature(self, body: bytes) -> str:
        """Compute the HMAC signature for the provided payload."""

        message = (self._notification_url + body.decode("utf-8")).encode("utf-8")
        digest = hmac.new(
            self._signature_key.encode("utf-8"), message, hashlib.sha1
        ).digest()
        return base64.b64encode(digest).decode("utf-8")

    def verify(self, body: bytes, header_signature: str | None) -> None:
        """Validate that the provided signature matches the payload."""

        if not header_signature:
            raise SquareWebhookVerificationError("Missing signature header")

        expected = self.compute_signature(body)
        if not hmac.compare_digest(expected, header_signature):
            raise SquareWebhookVerificationError("Signature mismatch")


def acknowledge_payload() -> Mapping[str, str]:
    """Return the canonical acknowledgement payload for Square webhooks."""

    return {"status": "acknowledged"}


def _coerce_datetime(value: str | None) -> datetime:
    if not value:
        raise ValueError("timestamp missing from payload")
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_prep_time_update(payload: Mapping[str, Any]) -> PrepTimeUpdate:
    """Extract a :class:`PrepTimeUpdate` from a Square KDS webhook payload."""

    try:
        location_id = str(payload["location_id"])
        data = payload["data"]
        prep_time = data["object"]["prep_time"]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Missing expected field in payload: {exc}") from exc

    order_id = str(prep_time.get("order_id") or data.get("id"))
    if not order_id:
        raise ValueError("order_id missing from prep_time payload")

    duration = prep_time.get("duration_seconds")
    if duration is None:
        raise ValueError("duration_seconds missing from prep_time payload")

    try:
        prep_time_seconds = int(duration)
    except (TypeError, ValueError) as exc:
        raise ValueError("duration_seconds must be an integer") from exc

    ready_at = _coerce_datetime(prep_time.get("ready_at"))
    updated_at = _coerce_datetime(prep_time.get("updated_at"))

    return PrepTimeUpdate(
        location_id=location_id,
        order_id=order_id,
        prep_time_seconds=prep_time_seconds,
        ready_at=ready_at,
        updated_at=updated_at,
    )


__all__ = [
    "PrepTimeUpdate",
    "SquareWebhookVerificationError",
    "SquareWebhookVerifier",
    "acknowledge_payload",
    "parse_prep_time_update",
]
