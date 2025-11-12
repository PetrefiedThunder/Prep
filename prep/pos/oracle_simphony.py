"""Oracle Simphony enterprise connector."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import httpx

from prep.commerce import models


class OracleSimphonyError(RuntimeError):
    """Raised when the Simphony API returns a non-success response."""


@dataclass(slots=True)
class OracleSimphonyClient:
    """Lightweight client for Oracle Simphony's enterprise REST APIs."""

    host: str | None
    username: str | None
    password: str | None
    enterprise_id: str | None
    timeout: float = 10.0

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.username and self.password and self.enterprise_id)

    async def sync_orders(self, location_id: str, orders: Iterable[models.Order]) -> None:
        if not self.is_configured:
            return
        payload = {
            "enterpriseId": self.enterprise_id,
            "locationId": location_id,
            "orders": [order.to_fulfillment_payload() for order in orders],
        }
        async with httpx.AsyncClient(base_url=str(self.host), timeout=self.timeout) as client:
            response = await client.post(
                "/simphony/v1/orders",
                json=payload,
                auth=(self.username or "", self.password or ""),
            )
            if response.status_code >= 400:
                raise OracleSimphonyError(
                    f"Simphony synchronization failed: {response.status_code} {response.text}"
                )


class FranchiseSyncService:
    """Coordinate Simphony syncs across multiple franchise locations."""

    def __init__(self, client: OracleSimphonyClient) -> None:
        self._client = client

    async def sync(self, orders: Iterable[models.Order]) -> dict[str, int]:
        bucket: dict[str, list[models.Order]] = {}
        for order in orders:
            bucket.setdefault(order.location_id, []).append(order)
        results: dict[str, int] = {}
        for location_id, location_orders in bucket.items():
            await self._client.sync_orders(location_id, location_orders)
            results[location_id] = len(location_orders)
        return results


__all__ = ["OracleSimphonyClient", "OracleSimphonyError", "FranchiseSyncService"]
