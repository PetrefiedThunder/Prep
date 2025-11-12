"""Notification service abstraction used by the compliance engine."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class NotificationService:
    """Simple notification transport that logs outgoing messages."""

    async def send_notification(
        self,
        *,
        user_id: str,
        type: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Send a notification by logging it for now."""

        payload = {
            "user_id": user_id,
            "type": type,
            "title": title,
            "body": body,
            "data": data or {},
        }
        logger.info("Notification dispatched: %s", payload)


__all__ = ["NotificationService"]
