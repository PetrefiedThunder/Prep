"""External delivery network client adapters."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from prep.models.orm import DeliveryStatus
from prep.settings import Settings

logger = logging.getLogger("prep.delivery.clients")


@dataclass(slots=True)
class DeliveryIntegrationResult:
    """Normalized response from a delivery integration."""

    provider_delivery_id: str
    status: DeliveryStatus
    eta: datetime | None
    tracking_url: str | None
    courier_name: str | None = None
    courier_phone: str | None = None
    raw: dict[str, Any] | None = None


class DeliveryIntegrationError(RuntimeError):
    """Raised when an integration returns an unrecoverable error."""

    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class DoorDashDriveClient:
    """Lightweight HTTP client for the DoorDash Drive API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = str(settings.doordash_drive_base_url).rstrip("/")
        self._client_id = settings.doordash_drive_client_id
        self._client_secret = settings.doordash_drive_client_secret

    @property
    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    async def create_delivery(self, payload: dict[str, Any]) -> DeliveryIntegrationResult:
        """Create a delivery through DoorDash Drive."""

        if self._settings.use_fixtures or not self.is_configured:
            identifier = payload.get("external_delivery_id") or payload.get("external_order_id")
            if not identifier:
                identifier = f"dd-{datetime.now(UTC).timestamp():.0f}"
            tracking_url = f"https://doordash.test/track/{identifier}"
            logger.debug("Returning fixture DoorDash delivery response", extra={"id": identifier})
            return DeliveryIntegrationResult(
                provider_delivery_id=identifier,
                status=DeliveryStatus.CREATED,
                eta=datetime.now(UTC) + timedelta(minutes=45),
                tracking_url=tracking_url,
                raw={"mode": "fixture"},
            )

        auth = httpx.BasicAuth(self._client_id or "", self._client_secret or "")
        url = f"{self._base_url}/drive/v2/deliveries"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, auth=auth)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network specific failures
            logger.exception(
                "DoorDash Drive returned error", extra={"status": exc.response.status_code}
            )
            raise DeliveryIntegrationError(
                "Failed to create DoorDash delivery",
                status_code=exc.response.status_code,
            ) from exc

        data = response.json()
        return DeliveryIntegrationResult(
            provider_delivery_id=str(data.get("delivery_id")),
            status=_map_doordash_status(data.get("status")),
            eta=_parse_timestamp(data.get("dropoff_time")),
            tracking_url=data.get("tracking_url"),
            courier_name=data.get("dasher", {}).get("name"),
            courier_phone=data.get("dasher", {}).get("phone_number"),
            raw=data,
        )

    def verify_webhook(self, payload: bytes, signature: str | None) -> None:
        """Verify webhook authenticity using the shared secret."""

        secret = self._settings.doordash_drive_webhook_secret
        if not secret:
            logger.debug("No DoorDash webhook secret configured; skipping verification")
            return
        if not signature:
            raise DeliveryIntegrationError("Missing DoorDash webhook signature", status_code=400)
        computed = base64.b64encode(payload + secret.encode("utf-8")).decode("utf-8")
        if not hmac_compare(signature, computed):
            raise DeliveryIntegrationError("Invalid DoorDash webhook signature", status_code=400)


class UberDirectClient:
    """Client for the Uber Direct API with OAuth2 support."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = str(settings.uber_direct_base_url).rstrip("/")
        self._client_id = settings.uber_direct_client_id
        self._client_secret = settings.uber_direct_client_secret
        self._token_url = str(settings.uber_direct_token_url)
        self._scope = settings.uber_direct_scope
        self._audience = settings.uber_direct_audience
        self._access_token: str | None = None
        self._token_expiration: datetime | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    async def create_delivery(self, payload: dict[str, Any]) -> DeliveryIntegrationResult:
        """Create a delivery using the Uber Direct API."""

        if self._settings.use_fixtures or not self.is_configured:
            identifier = payload.get("external_delivery_id") or payload.get("reference_id")
            if not identifier:
                identifier = f"uber-{datetime.now(UTC).timestamp():.0f}"
            tracking_url = f"https://uber.test/track/{identifier}"
            logger.debug("Returning fixture Uber Direct response", extra={"id": identifier})
            return DeliveryIntegrationResult(
                provider_delivery_id=identifier,
                status=DeliveryStatus.CREATED,
                eta=datetime.now(UTC) + timedelta(minutes=40),
                tracking_url=tracking_url,
                raw={"mode": "fixture"},
            )

        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self._base_url}/v1/deliveries"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network specific failures
            logger.exception(
                "Uber Direct returned error", extra={"status": exc.response.status_code}
            )
            raise DeliveryIntegrationError(
                "Failed to create Uber Direct delivery",
                status_code=exc.response.status_code,
            ) from exc

        data = response.json()
        return DeliveryIntegrationResult(
            provider_delivery_id=str(data.get("delivery_id")),
            status=_map_uber_status(data.get("status")),
            eta=_parse_timestamp(data.get("estimated_dropoff")),
            tracking_url=data.get("tracking_url"),
            courier_name=data.get("courier", {}).get("name"),
            courier_phone=data.get("courier", {}).get("phone_number"),
            raw=data,
        )

    async def _get_token(self) -> str:
        if (
            self._access_token
            and self._token_expiration
            and self._token_expiration > datetime.now(UTC) + timedelta(seconds=30)
        ):
            return self._access_token

        if not self.is_configured:
            raise DeliveryIntegrationError(
                "Uber Direct credentials are not configured", status_code=500
            )

        data = {
            "grant_type": "client_credentials",
            "scope": self._scope,
            "audience": self._audience,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._token_url,
                data=data,
                auth=httpx.BasicAuth(self._client_id or "", self._client_secret or ""),
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network specific failures
            logger.exception(
                "Uber Direct token request failed", extra={"status": exc.response.status_code}
            )
            raise DeliveryIntegrationError(
                "Failed to authenticate with Uber Direct", status_code=exc.response.status_code
            ) from exc

        token_data = response.json()
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)
        if not access_token:
            raise DeliveryIntegrationError(
                "Uber Direct token response missing access_token", status_code=502
            )

        self._access_token = access_token
        self._token_expiration = datetime.now(UTC) + timedelta(seconds=int(expires_in))
        return access_token


def _map_doordash_status(status: Any) -> DeliveryStatus:
    mapping = {
        "created": DeliveryStatus.CREATED,
        "pending": DeliveryStatus.CREATED,
        "confirmed": DeliveryStatus.DISPATCHED,
        "enroute_pickup": DeliveryStatus.DISPATCHED,
        "picked_up": DeliveryStatus.IN_TRANSIT,
        "enroute_dropoff": DeliveryStatus.IN_TRANSIT,
        "delivered": DeliveryStatus.DELIVERED,
        "cancelled": DeliveryStatus.CANCELLED,
        "returned": DeliveryStatus.RETURNED,
        "failed": DeliveryStatus.FAILED,
    }
    return mapping.get(str(status or "").lower(), DeliveryStatus.CREATED)


def _map_uber_status(status: Any) -> DeliveryStatus:
    mapping = {
        "processing": DeliveryStatus.CREATED,
        "accepted": DeliveryStatus.DISPATCHED,
        "courier_en_route_to_pickup": DeliveryStatus.DISPATCHED,
        "courier_arrived_at_pickup": DeliveryStatus.DISPATCHED,
        "picked_up": DeliveryStatus.IN_TRANSIT,
        "en_route_to_dropoff": DeliveryStatus.IN_TRANSIT,
        "delivered": DeliveryStatus.DELIVERED,
        "return_in_progress": DeliveryStatus.RETURNED,
        "cancelled": DeliveryStatus.CANCELLED,
        "delivery_failed": DeliveryStatus.FAILED,
    }
    return mapping.get(str(status or "").lower(), DeliveryStatus.CREATED)


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def hmac_compare(expected: str, actual: str) -> bool:
    """Constant-time comparison helper."""

    if len(expected) != len(actual):
        return False
    result = 0
    for x, y in zip(expected.encode("utf-8"), actual.encode("utf-8"), strict=False):
        result |= x ^ y
    return result == 0


__all__ = [
    "DoorDashDriveClient",
    "UberDirectClient",
    "DeliveryIntegrationResult",
    "DeliveryIntegrationError",
]
