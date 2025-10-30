"""Analytics adapter for POS integrations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Iterable, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.cache import RedisProtocol
from prep.models.orm import Booking, BookingStatus, POSOrder, POSTransaction

from .models import POSAnalyticsResponse, POSAnalyticsSnapshot

_POS_BOOKING_STATUSES = {BookingStatus.CONFIRMED, BookingStatus.COMPLETED}
_CACHE_TTL_SECONDS = 300


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class POSAnalyticsService:
    """Compute aggregated analytics for POS integrations."""

    def __init__(self, session: AsyncSession, cache: RedisProtocol | None = None) -> None:
        self._session = session
        self._cache = cache

    def _cache_key(self, *, kitchen_id: UUID | None, start: datetime, end: datetime) -> str:
        return f"analytics:pos:{kitchen_id or 'all'}:{start.isoformat()}:{end.isoformat()}"

    async def _get_cached(self, key: str) -> POSAnalyticsSnapshot | None:
        if self._cache is None:
            return None
        payload = await self._cache.get(key)
        if not payload:
            return None
        try:
            return POSAnalyticsSnapshot.model_validate_json(payload)
        except Exception:  # pragma: no cover - validation guard
            return None

    async def _set_cache(self, key: str, snapshot: POSAnalyticsSnapshot) -> None:
        if self._cache is None:
            return
        await self._cache.setex(key, _CACHE_TTL_SECONDS, snapshot.model_dump_json())

    async def compute_metrics(
        self,
        *,
        start: datetime,
        end: datetime,
        kitchen_id: UUID | None = None,
    ) -> POSAnalyticsResponse:
        start_utc = _ensure_utc(start)
        end_utc = _ensure_utc(end)
        if end_utc <= start_utc:
            raise ValueError("end must be after start")

        cache_key = self._cache_key(kitchen_id=kitchen_id, start=start_utc, end=end_utc)
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return POSAnalyticsResponse.model_validate(cached.model_dump())

        txn_filters = [
            POSTransaction.occurred_at >= start_utc,
            POSTransaction.occurred_at <= end_utc,
        ]
        if kitchen_id is not None:
            txn_filters.append(POSTransaction.kitchen_id == kitchen_id)

        txn_stmt = select(
            func.count(POSTransaction.id),
            func.coalesce(func.sum(POSTransaction.amount), 0),
        ).where(*txn_filters)
        txn_result = await self._session.execute(txn_stmt)
        txn_count, txn_total = txn_result.one_or_none() or (0, Decimal("0"))
        if txn_total is None:
            txn_total = Decimal("0")
        if not isinstance(txn_total, Decimal):
            txn_total = Decimal(str(txn_total))

        order_filters = [
            POSOrder.closed_at.is_not(None),
            POSOrder.closed_at >= start_utc,
            POSOrder.closed_at <= end_utc,
        ]
        if kitchen_id is not None:
            order_filters.append(POSOrder.kitchen_id == kitchen_id)
        order_stmt = select(func.coalesce(func.sum(POSOrder.total_amount), 0)).where(*order_filters)
        order_result = await self._session.execute(order_stmt)
        order_total = order_result.scalar_one_or_none() or Decimal("0")
        if not isinstance(order_total, Decimal):
            order_total = Decimal(str(order_total))

        total_sales = txn_total + order_total

        duration_seconds = (end_utc - start_utc).total_seconds()
        total_hours = Decimal(str(duration_seconds)) / Decimal("3600") if duration_seconds > 0 else Decimal("0")
        if total_hours <= 0:
            total_hours = Decimal("1")

        average_ticket = total_sales / Decimal(txn_count) if txn_count else Decimal("0")
        sales_per_hour = total_sales / total_hours if total_hours > 0 else Decimal("0")

        booking_stmt = select(Booking.start_time, Booking.end_time).where(
            Booking.start_time < end_utc,
            Booking.end_time > start_utc,
            Booking.status.in_(_POS_BOOKING_STATUSES),
        )
        if kitchen_id is not None:
            booking_stmt = booking_stmt.where(Booking.kitchen_id == kitchen_id)
        booking_result = await self._session.execute(booking_stmt)
        booking_hours = Decimal("0")
        for start_time, end_time in booking_result.all():
            if start_time is None or end_time is None:
                continue
            normalized_start = _ensure_utc(start_time)
            normalized_end = _ensure_utc(end_time)
            overlap_start = max(normalized_start, start_utc)
            overlap_end = min(normalized_end, end_utc)
            delta = (overlap_end - overlap_start).total_seconds()
            if delta <= 0:
                continue
            booking_hours += Decimal(str(delta)) / Decimal("3600")

        utilization = 0.0
        if total_hours > 0:
            utilization = float(min(booking_hours / total_hours, Decimal("1")))

        snapshot = POSAnalyticsResponse(
            kitchen_id=kitchen_id,
            start=start_utc,
            end=end_utc,
            total_transactions=int(txn_count),
            total_sales=total_sales,
            avg_ticket=average_ticket,
            sales_per_hour=sales_per_hour,
            utilization_rate=utilization,
        )
        await self._set_cache(cache_key, snapshot)
        return snapshot

    async def invalidate_cache(self, kitchen_ids: Sequence[UUID] | None = None) -> int:
        if self._cache is None:
            return 0
        patterns: list[str]
        if kitchen_ids:
            patterns = [f"analytics:pos:{k_id}:*" for k_id in kitchen_ids]
        else:
            patterns = ["analytics:pos:*"]
        keys: list[str] = []
        for pattern in patterns:
            keys.extend(await self._cache.keys(pattern))
        if not keys:
            return 0
        await self._cache.delete(*keys)
        return len(keys)

    async def refresh_cache(
        self,
        *,
        kitchen_ids: Iterable[UUID] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[POSAnalyticsResponse]:
        start_dt = _ensure_utc(start or datetime.now(UTC) - timedelta(hours=24))
        end_dt = _ensure_utc(end or datetime.now(UTC))
        targets = list(kitchen_ids or [])
        await self.invalidate_cache(kitchen_ids=targets)
        snapshots: list[POSAnalyticsResponse] = []
        if targets:
            for kitchen_id in targets:
                snapshots.append(
                    await self.compute_metrics(kitchen_id=kitchen_id, start=start_dt, end=end_dt)
                )
        snapshots.append(await self.compute_metrics(kitchen_id=None, start=start_dt, end=end_dt))
        return snapshots


__all__ = ["POSAnalyticsService"]
