"""Thin async client for interacting with Onfleet's logistics API."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from prep.logistics import schemas


class OnfleetError(RuntimeError):
    """Base exception raised for Onfleet integration failures."""


class OnfleetConfigurationError(OnfleetError):
    """Raised when the client is instantiated without the required credentials."""


@dataclass(slots=True)
class OnfleetClient:
    """Asynchronous HTTP client encapsulating the Onfleet REST API."""

    base_url: str
    api_key: str | None
    timeout: float = 10.0

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def optimize_route(
        self, payload: schemas.RouteOptimizationRequest
    ) -> list[schemas.RouteStop]:
        """Delegate route optimization to Onfleet.

        Parameters
        ----------
        payload:
            The structured route optimization request received from the API layer.
        """

        if not self.is_configured:
            raise OnfleetConfigurationError("Onfleet API credentials are not configured")

        request_body = self._build_request(payload)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            response = await client.post(
                "/tasks/autoassign/advanced",
                json=request_body,
                headers={"Authorization": f"Basic {self._basic_auth_token}"},
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:  # pragma: no cover - network failure guard
                raise OnfleetError(f"Onfleet request failed: {exc.response.text}") from exc

            data = response.json()

        return self._parse_response(data)

    def _build_request(self, payload: schemas.RouteOptimizationRequest) -> dict[str, Any]:
        stops: list[dict[str, Any]] = []
        for stop in payload.stops:
            due_at = int(stop.due_at.timestamp()) if stop.due_at else None
            stops.append(
                {
                    "id": stop.id,
                    "type": stop.type,
                    "location": {
                        "lat": stop.location.latitude,
                        "lng": stop.location.longitude,
                    },
                    "serviceTime": stop.service_time_minutes * 60,
                    "completeAfter": due_at,
                }
            )
        body: dict[str, Any] = {
            "vehicleId": payload.vehicle_id,
            "tasks": stops,
            "options": {
                "considerDueAfter": True,
                "softCapacity": payload.soft_capacity,
            },
        }
        if payload.start_time:
            body["options"]["startTime"] = int(payload.start_time.timestamp())
        body["options"]["origin"] = {
            "lat": payload.start_location.latitude,
            "lng": payload.start_location.longitude,
        }
        return body

    def _parse_response(self, data: dict[str, Any]) -> list[schemas.RouteStop]:
        route: Iterable[dict[str, Any]] = data.get("route", [])
        stops: list[schemas.RouteStop] = []
        for index, element in enumerate(route, start=1):
            eta_value = element.get("eta")
            eta = (
                datetime.fromtimestamp(eta_value, tz=UTC)
                if isinstance(eta_value, (int, float))
                else None
            )
            metrics = element.get("metrics", {})
            stops.append(
                schemas.RouteStop(
                    id=str(element.get("taskId") or element.get("id")),
                    eta=eta,
                    sequence=index,
                    travel_distance_meters=float(metrics.get("distance", 0.0)),
                    travel_duration_seconds=float(metrics.get("duration", 0.0)),
                )
            )
        if not stops:
            raise OnfleetError("Onfleet response did not include any route waypoints")
        return stops

    @property
    def _basic_auth_token(self) -> str:
        if not self.api_key:
            raise OnfleetConfigurationError("Onfleet API key is required")
        import base64

        token = f"{self.api_key}:".encode()
        return base64.b64encode(token).decode("ascii")


__all__ = ["OnfleetClient", "OnfleetError", "OnfleetConfigurationError"]
