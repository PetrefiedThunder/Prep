"""Pydantic models and dataclasses shared across POS integrations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


@dataclass(slots=True)
class NormalizedTransaction:
    """Canonical representation of a POS transaction."""

    provider: str
    external_id: str
    amount: Decimal
    currency: str
    status: str
    occurred_at: datetime
    location_id: str | None = None
    raw: dict[str, Any] | None = None


@dataclass(slots=True)
class OrderEvent:
    """Normalized representation of an order webhook event."""

    provider: str
    external_id: str
    status: str
    total_amount: Decimal
    currency: str
    order_number: str | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    guest_count: int | None = None
    raw: dict[str, Any] | None = None


class POSAnalyticsSnapshot(BaseModel):
    """Aggregated POS analytics across a time window."""

    model_config = ConfigDict(json_encoders={Decimal: lambda value: format(value, "f")})

    kitchen_id: UUID | None = Field(default=None)
    start: datetime = Field(default_factory=lambda: datetime.now(UTC))
    end: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_transactions: int = 0
    total_sales: Decimal = Decimal("0")
    avg_ticket: Decimal = Decimal("0")
    sales_per_hour: Decimal = Decimal("0")
    utilization_rate: float = 0.0


class POSAnalyticsResponse(POSAnalyticsSnapshot):
    """Alias maintained for backwards compatible API responses."""


__all__ = [
    "NormalizedTransaction",
    "OrderEvent",
    "POSAnalyticsResponse",
    "POSAnalyticsSnapshot",
]
