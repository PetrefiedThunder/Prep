"""Realtime analytics processing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass
class Booking:
    """Lightweight booking event used by the realtime engine."""

    id: UUID
    host_id: UUID
    kitchen_id: UUID
    total_amount: float
    status: str
    created_at: datetime


@dataclass
class Review:
    """Review event emitted by the reviews service."""

    id: UUID
    host_id: UUID
    kitchen_id: UUID
    rating: float
    created_at: datetime


class AnalyticsRepository(Protocol):
    """Protocol describing repository operations used by the engine."""

    async def update_booking_statistics(self, booking: Booking) -> None: ...

    async def update_revenue_statistics(self, booking: Booking) -> None: ...

    async def update_host_performance(self, host_id: UUID) -> None: ...

    async def update_rating_statistics(self, kitchen_id: UUID, rating: float) -> None: ...

    async def update_host_reputation(self, host_id: UUID) -> None: ...


class RealtimeAnalyticsEngine:
    """Process real-time events for analytics updates."""

    def __init__(self, repository: AnalyticsRepository) -> None:
        self._repository = repository

    async def process_booking_event(self, booking: Booking) -> None:
        """Update analytics when booking events occur."""

        await self._repository.update_booking_statistics(booking)
        await self._repository.update_revenue_statistics(booking)
        await self._repository.update_host_performance(booking.host_id)

    async def process_review_event(self, review: Review) -> None:
        """Update analytics when review events occur."""

        await self._repository.update_rating_statistics(review.kitchen_id, review.rating)
        await self._repository.update_host_reputation(review.host_id)
