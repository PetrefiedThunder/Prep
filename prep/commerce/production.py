"""Simple production scheduling heuristics."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta

from prep.commerce import models


class ProductionScheduler:
    """Assign incoming orders to production slots based on due dates."""

    def __init__(self, slot_duration_minutes: int = 60, max_capacity: int = 200) -> None:
        self._slot_duration = timedelta(minutes=slot_duration_minutes)
        self._max_capacity = max_capacity

    def schedule(self, orders: Iterable[models.Order]) -> list[models.ProductionSlot]:
        slots: list[models.ProductionSlot] = []
        for order in sorted(orders, key=lambda o: o.due_at):
            slot = self._find_slot(slots, order)
            slot.add_order(order)
            order.status = "scheduled"
        return slots

    def _find_slot(
        self, slots: list[models.ProductionSlot], order: models.Order
    ) -> models.ProductionSlot:
        for slot in slots:
            if (
                slot.end >= order.due_at
                and slot.capacity + self._order_size(order) <= self._max_capacity
            ):
                return slot
        start = order.due_at - self._slot_duration
        slot = models.ProductionSlot(start=start, end=order.due_at)
        slots.append(slot)
        return slot

    def _order_size(self, order: models.Order) -> int:
        return sum(line.quantity for line in order.lines) or 1


__all__ = ["ProductionScheduler"]
