"""Database helpers for POS integrations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy import insert as sa_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from prep.models.orm import POSIntegration, POSOrder, POSTransaction

from .models import NormalizedTransaction, OrderEvent


class POSIntegrationRepository:
    """Persistence helpers for POS integrations and activity."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_integration(self, *, kitchen_id: UUID, provider: str) -> POSIntegration | None:
        stmt = (
            select(POSIntegration)
            .where(POSIntegration.kitchen_id == kitchen_id)
            .where(POSIntegration.provider == provider)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_integration_by_id(self, integration_id: UUID) -> POSIntegration | None:
        return await self._session.get(POSIntegration, integration_id)

    async def update_tokens(
        self,
        integration: POSIntegration,
        *,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime | None,
    ) -> POSIntegration:
        integration.access_token = access_token
        integration.refresh_token = refresh_token
        integration.expires_at = expires_at
        integration.updated_at = datetime.now(UTC)
        await self._session.flush()
        return integration

    def _insert(self, table):
        bind = getattr(self._session, "bind", None)
        dialect = getattr(bind, "dialect", None)
        name = getattr(dialect, "name", "") if dialect else ""
        if name == "postgresql":
            return pg_insert(table)
        if name == "sqlite":  # pragma: no branch - sqlite tests
            return sqlite_insert(table)
        return sa_insert(table)

    async def upsert_transaction(
        self, integration: POSIntegration, transaction: NormalizedTransaction
    ) -> POSTransaction:
        stmt = (
            self._insert(POSTransaction)
            .values(
                id=None,
                integration_id=integration.id,
                kitchen_id=integration.kitchen_id,
                provider=transaction.provider,
                location_id=transaction.location_id,
                external_id=transaction.external_id,
                amount=transaction.amount,
                currency=transaction.currency,
                status=transaction.status,
                occurred_at=transaction.occurred_at,
                raw_data=transaction.raw,
            )
            .on_conflict_do_update(
                index_elements=[POSTransaction.provider, POSTransaction.external_id],
                set_
                ={
                    "integration_id": integration.id,
                    "kitchen_id": integration.kitchen_id,
                    "location_id": transaction.location_id,
                    "amount": transaction.amount,
                    "currency": transaction.currency,
                    "status": transaction.status,
                    "occurred_at": transaction.occurred_at,
                    "raw_data": transaction.raw,
                    "updated_at": func.now(),
                },
            )
            .returning(POSTransaction)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def upsert_order(self, integration: POSIntegration, event: OrderEvent) -> POSOrder:
        stmt = (
            self._insert(POSOrder)
            .values(
                id=None,
                integration_id=integration.id,
                kitchen_id=integration.kitchen_id,
                provider=event.provider,
                external_id=event.external_id,
                order_number=event.order_number,
                status=event.status,
                opened_at=event.opened_at,
                closed_at=event.closed_at,
                total_amount=event.total_amount,
                currency=event.currency,
                guest_count=event.guest_count,
                raw_data=event.raw,
            )
            .on_conflict_do_update(
                index_elements=[POSOrder.provider, POSOrder.external_id],
                set_
                ={
                    "integration_id": integration.id,
                    "order_number": event.order_number,
                    "status": event.status,
                    "opened_at": event.opened_at,
                    "closed_at": event.closed_at,
                    "total_amount": event.total_amount,
                    "currency": event.currency,
                    "guest_count": event.guest_count,
                    "raw_data": event.raw,
                    "updated_at": func.now(),
                },
            )
            .returning(POSOrder)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def list_integrations(self, provider: str | None = None) -> list[POSIntegration]:
        stmt = select(POSIntegration)
        if provider:
            stmt = stmt.where(POSIntegration.provider == provider)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def touch_integrations(self, integrations: Iterable[POSIntegration]) -> None:
        now = datetime.now(UTC)
        for integration in integrations:
            integration.updated_at = now
        await self._session.flush()


__all__ = ["POSIntegrationRepository"]
