"""Regulatory notification helpers for compliance workflows."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from typing import AsyncIterator, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database.connection import AsyncSessionLocal
from prep.models import Kitchen

from .service import NotificationService


class RegulatoryNotifier:
    """Helper responsible for pushing regulatory notifications to hosts."""

    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        self.logger = logging.getLogger(__name__)

    async def notify_compliance_change(
        self,
        kitchen_id: str,
        old_status: str,
        new_status: str,
        reasons: List[str],
    ) -> None:
        """Notify a host when their kitchen compliance status changes."""

        kitchen = await self.get_kitchen(kitchen_id)
        if kitchen is None:
            self.logger.warning("Unable to load kitchen %s for compliance change notification", kitchen_id)
            return

        message = f"Compliance status changed from {old_status or 'unknown'} to {new_status} for {kitchen.name}"
        if reasons:
            message += f". Reasons: {', '.join(reasons)}"

        await self.notification_service.send_notification(
            user_id=str(kitchen.host_id),
            type="compliance_change",
            title="Compliance Status Update",
            body=message,
            data={
                "kitchen_id": kitchen_id,
                "old_status": old_status,
                "new_status": new_status,
                "reasons": reasons,
            },
        )

    async def notify_regulatory_update(
        self,
        state: str,
        city: Optional[str],
        regulation_changes: List[Dict],
    ) -> None:
        """Notify hosts within a jurisdiction about new regulations."""

        kitchens = await self.get_kitchens_by_jurisdiction(state, city)
        for kitchen in kitchens:
            message = f"New regulatory updates in {city or 'your area'}, {state} may affect your kitchen"
            await self.notification_service.send_notification(
                user_id=str(kitchen.host_id),
                type="regulatory_update",
                title="Regulatory Update Alert",
                body=message,
                data={
                    "state": state,
                    "city": city,
                    "changes": regulation_changes,
                    "kitchen_id": str(kitchen.id),
                },
            )

    async def notify_compliance_deadline(
        self,
        kitchen_id: str,
        deadline: datetime,
        requirement: str,
    ) -> None:
        """Notify a host about an upcoming compliance deadline."""

        kitchen = await self.get_kitchen(kitchen_id)
        if kitchen is None:
            self.logger.warning("Unable to load kitchen %s for compliance deadline notification", kitchen_id)
            return

        days_until = max((deadline - datetime.now(UTC)).days, 0)
        await self.notification_service.send_notification(
            user_id=str(kitchen.host_id),
            type="compliance_deadline",
            title=f"Compliance Deadline: {requirement}",
            body=f"Deadline in {days_until} days for {kitchen.name}",
            data={
                "kitchen_id": kitchen_id,
                "deadline": deadline.isoformat(),
                "requirement": requirement,
                "days_until": days_until,
            },
        )

    async def get_kitchen(self, kitchen_id: str) -> Optional[Kitchen]:
        """Fetch a kitchen by ID using a short-lived database session."""

        try:
            kitchen_uuid = UUID(kitchen_id)
        except ValueError:
            return None

        async with self._session() as session:
            result = await session.execute(select(Kitchen).where(Kitchen.id == kitchen_uuid))
            return result.scalar_one_or_none()

    async def get_kitchens_by_jurisdiction(self, state: str, city: Optional[str]) -> List[Kitchen]:
        """Fetch kitchens within a given jurisdiction."""

        async with self._session() as session:
            query = select(Kitchen).where(func.upper(Kitchen.state) == state.upper())
            if city:
                query = query.where(Kitchen.city == city)
            result = await session.execute(query)
            return result.scalars().all()

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[AsyncSession]:
        session: AsyncSession = AsyncSessionLocal()
        try:
            yield session
        finally:
            await session.close()


__all__ = ["RegulatoryNotifier"]
