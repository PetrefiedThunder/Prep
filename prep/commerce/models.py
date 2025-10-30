"""Shared dataclasses representing omni-channel order flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable


class OrderSource(str, Enum):
    SHOPIFY = "shopify"
    TIKTOK = "tiktok"


@dataclass(slots=True)
class OrderLine:
    sku: str
    quantity: int


@dataclass(slots=True)
class Order:
    id: str
    source: OrderSource
    created_at: datetime
    due_at: datetime
    location_id: str
    customer_name: str
    lines: list[OrderLine] = field(default_factory=list)
    status: str = "pending"

    def to_fulfillment_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "status": self.status,
            "lines": [
                {"sku": line.sku, "quantity": line.quantity} for line in self.lines
            ],
            "due_at": self.due_at.isoformat(),
        }


@dataclass(slots=True)
class ProductionSlot:
    start: datetime
    end: datetime
    orders: list[Order] = field(default_factory=list)

    def add_order(self, order: Order) -> None:
        self.orders.append(order)

    @property
    def capacity(self) -> int:
        return sum(line.quantity for order in self.orders for line in order.lines)


def normalize_timestamp(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def coerce_order_lines(payload: Iterable[dict[str, object]]) -> list[OrderLine]:
    return [
        OrderLine(sku=str(item["sku"]), quantity=int(item.get("quantity", 1)))
        for item in payload
    ]


__all__ = [
    "Order",
    "OrderLine",
    "OrderSource",
    "ProductionSlot",
    "normalize_timestamp",
    "coerce_order_lines",
]
