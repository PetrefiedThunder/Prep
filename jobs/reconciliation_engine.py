"""Nightly reconciliation engine for bookings versus POS sales."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import boto3
from botocore.client import BaseClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from prep.cache import RedisProtocol, get_redis
from prep.database import get_session_factory
from prep.models.orm import Booking, BookingStatus, POSOrder, POSTransaction
from prep.pos.analytics import POSAnalyticsService
from prep.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ReconciliationEntry:
    """Ledger entry summarizing a kitchen's activity."""

    kitchen_id: UUID
    booking_total: Decimal = Decimal("0")
    booking_count: int = 0
    pos_transaction_total: Decimal = Decimal("0")
    pos_transaction_count: int = 0
    pos_order_total: Decimal = Decimal("0")
    pos_order_count: int = 0

    @property
    def variance(self) -> Decimal:
        return (self.pos_transaction_total + self.pos_order_total) - self.booking_total

    def as_dict(self) -> dict[str, object]:
        return {
            "kitchen_id": str(self.kitchen_id),
            "booking_total": format(self.booking_total, "f"),
            "booking_count": self.booking_count,
            "pos_transaction_total": format(self.pos_transaction_total, "f"),
            "pos_transaction_count": self.pos_transaction_count,
            "pos_order_total": format(self.pos_order_total, "f"),
            "pos_order_count": self.pos_order_count,
            "variance": format(self.variance, "f"),
        }


@dataclass(slots=True)
class ReconciliationReport:
    """Structured result from a reconciliation run."""

    start: datetime
    end: datetime
    entries: list[ReconciliationEntry] = field(default_factory=list)
    s3_object_key: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "entries": [entry.as_dict() for entry in self.entries],
            "s3_object_key": self.s3_object_key,
            "generated_at": datetime.now(UTC).isoformat(),
        }


def _ensure_decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


async def _collect_booking_aggregates(
    session: AsyncSession,
    *,
    start: datetime,
    end: datetime,
) -> dict[UUID, tuple[Decimal, int]]:
    stmt = (
        select(
            Booking.kitchen_id,
            func.count(Booking.id),
            func.coalesce(func.sum(Booking.total_amount), 0),
        )
        .where(Booking.start_time < end)
        .where(Booking.end_time > start)
        .where(Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]))
        .group_by(Booking.kitchen_id)
    )
    result = await session.execute(stmt)
    aggregates: dict[UUID, tuple[Decimal, int]] = {}
    for kitchen_id, count, total in result.all():
        aggregates[kitchen_id] = (_ensure_decimal(total), int(count))
    return aggregates


async def _collect_transaction_aggregates(
    session: AsyncSession,
    *,
    start: datetime,
    end: datetime,
) -> dict[UUID, tuple[Decimal, int]]:
    stmt = (
        select(
            POSTransaction.kitchen_id,
            func.count(POSTransaction.id),
            func.coalesce(func.sum(POSTransaction.amount), 0),
        )
        .where(POSTransaction.occurred_at >= start)
        .where(POSTransaction.occurred_at <= end)
        .group_by(POSTransaction.kitchen_id)
    )
    result = await session.execute(stmt)
    aggregates: dict[UUID, tuple[Decimal, int]] = {}
    for kitchen_id, count, total in result.all():
        aggregates[kitchen_id] = (_ensure_decimal(total), int(count))
    return aggregates


async def _collect_order_aggregates(
    session: AsyncSession,
    *,
    start: datetime,
    end: datetime,
) -> dict[UUID, tuple[Decimal, int]]:
    stmt = (
        select(
            POSOrder.kitchen_id,
            func.count(POSOrder.id),
            func.coalesce(func.sum(POSOrder.total_amount), 0),
        )
        .where(POSOrder.closed_at.is_not(None))
        .where(POSOrder.closed_at >= start)
        .where(POSOrder.closed_at <= end)
        .group_by(POSOrder.kitchen_id)
    )
    result = await session.execute(stmt)
    aggregates: dict[UUID, tuple[Decimal, int]] = {}
    for kitchen_id, count, total in result.all():
        aggregates[kitchen_id] = (_ensure_decimal(total), int(count))
    return aggregates


async def _upload_ledger(
    *,
    s3_client: BaseClient,
    bucket: str,
    key: str,
    payload: dict[str, object],
) -> None:
    body = json.dumps(payload).encode("utf-8")
    await asyncio.to_thread(
        s3_client.put_object,
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
    )


async def run_pos_reconciliation(
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    s3_client: BaseClient | None = None,
    cache: RedisProtocol | None = None,
) -> ReconciliationReport:
    """Reconcile bookings against POS sales and upload a ledger to S3."""

    settings = get_settings()
    if not settings.pos_ledger_bucket:
        raise RuntimeError("POS_LEDGER_BUCKET is not configured")

    start_dt = start or (datetime.now(UTC) - timedelta(days=1))
    end_dt = end or datetime.now(UTC)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=UTC)
    else:
        start_dt = start_dt.astimezone(UTC)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=UTC)
    else:
        end_dt = end_dt.astimezone(UTC)
    if end_dt <= start_dt:
        raise RuntimeError("Reconciliation end must be after start")

    session_factory = session_factory or get_session_factory()
    report = ReconciliationReport(start=start_dt, end=end_dt)

    analytics_cache = cache or await get_redis()
    created_s3_client = False
    if s3_client is None:
        s3_client = boto3.client("s3")
        created_s3_client = True

    async with session_factory() as session:  # type: ignore[arg-type]
        booking_totals = await _collect_booking_aggregates(session, start=start_dt, end=end_dt)
        transaction_totals = await _collect_transaction_aggregates(
            session, start=start_dt, end=end_dt
        )
        order_totals = await _collect_order_aggregates(session, start=start_dt, end=end_dt)

        kitchen_ids = set(booking_totals) | set(transaction_totals) | set(order_totals)
        entries: list[ReconciliationEntry] = []
        for kitchen_id in kitchen_ids:
            booking_total, booking_count = booking_totals.get(kitchen_id, (Decimal("0"), 0))
            txn_total, txn_count = transaction_totals.get(kitchen_id, (Decimal("0"), 0))
            order_total, order_count = order_totals.get(kitchen_id, (Decimal("0"), 0))
            entries.append(
                ReconciliationEntry(
                    kitchen_id=kitchen_id,
                    booking_total=booking_total,
                    booking_count=booking_count,
                    pos_transaction_total=txn_total,
                    pos_transaction_count=txn_count,
                    pos_order_total=order_total,
                    pos_order_count=order_count,
                )
            )

        entries.sort(key=lambda entry: entry.kitchen_id)
        report.entries = entries

        key = f"ledgers/pos/{start_dt.strftime('%Y%m%d%H%M%S')}_{end_dt.strftime('%Y%m%d%H%M%S')}.json"
        await _upload_ledger(
            s3_client=s3_client,
            bucket=settings.pos_ledger_bucket,
            key=key,
            payload=report.as_dict(),
        )
        report.s3_object_key = key

        analytics_service = POSAnalyticsService(session, analytics_cache)
        await analytics_service.refresh_cache(
            kitchen_ids=list(kitchen_ids), start=start_dt, end=end_dt
        )

    if created_s3_client and hasattr(s3_client, "close"):
        try:
            s3_client.close()
        except Exception:  # pragma: no cover - boto3 close semantics vary
            logger.debug("Failed to close S3 client", exc_info=True)

    logger.info(
        "POS reconciliation completed",
        extra={
            "start": report.start.isoformat(),
            "end": report.end.isoformat(),
            "entries": len(report.entries),
            "s3_key": report.s3_object_key,
        },
    )

    return report


__all__ = ["ReconciliationEntry", "ReconciliationReport", "run_pos_reconciliation"]
