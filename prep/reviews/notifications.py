"""Notification utilities for the review service."""

from __future__ import annotations

import logging
from typing import Any, Protocol
from uuid import UUID

logger = logging.getLogger(__name__)


class ReviewNotificationTransport(Protocol):
    """Protocol describing the outbound notification transport."""

    async def send(
        self,
        *,
        recipient_id: UUID,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Send a notification to the downstream system."""


class LoggingNotificationTransport:
    """Fallback transport that simply logs notifications for observability."""

    async def send(
        self,
        *,
        recipient_id: UUID,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        logger.info(
            "Dispatching review notification",
            extra={
                "recipient_id": str(recipient_id),
                "title": title,
                "body": body,
                "data": data or {},
            },
        )


class ReviewNotifier:
    """High-level helper for emitting structured review notifications."""

    def __init__(self, transport: ReviewNotificationTransport | None = None) -> None:
        self._transport = transport or LoggingNotificationTransport()

    async def notify_review_submitted(
        self,
        *,
        host_id: UUID,
        review_id: UUID,
        kitchen_id: UUID,
    ) -> None:
        await self._transport.send(
            recipient_id=host_id,
            title="New kitchen review received",
            body="A guest just shared feedback on your kitchen",
            data={"review_id": str(review_id), "kitchen_id": str(kitchen_id)},
        )

    async def notify_host_response(
        self,
        *,
        reviewer_id: UUID,
        review_id: UUID,
        kitchen_id: UUID,
    ) -> None:
        await self._transport.send(
            recipient_id=reviewer_id,
            title="Host responded to your review",
            body="The host left a public response to your review.",
            data={"review_id": str(review_id), "kitchen_id": str(kitchen_id)},
        )

    async def notify_review_flagged(
        self,
        *,
        reviewer_id: UUID,
        review_id: UUID,
        reason: str,
    ) -> None:
        await self._transport.send(
            recipient_id=reviewer_id,
            title="Review under moderation",
            body="Your review has been flagged for moderator review.",
            data={"review_id": str(review_id), "reason": reason},
        )

    async def notify_review_moderated(
        self,
        *,
        reviewer_id: UUID,
        review_id: UUID,
        status: str,
        notes: str | None = None,
    ) -> None:
        await self._transport.send(
            recipient_id=reviewer_id,
            title="Review moderation update",
            body="A moderator updated the status of your review.",
            data={"review_id": str(review_id), "status": status, "notes": notes or ""},
        )


__all__ = ["ReviewNotifier", "ReviewNotificationTransport", "LoggingNotificationTransport"]
