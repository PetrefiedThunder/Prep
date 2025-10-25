"""FastAPI router implementing the analytics dashboard API surface."""

from __future__ import annotations

import calendar
import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ValidationError
from sqlalchemy import case, desc, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from prep.auth import get_current_admin, get_current_user
from prep.cache import get_redis
from prep.database import get_db
from prep.models import (
    AdminPerformanceMetrics,
    AdminTeamMemberPerformance,
    BookingAnalytics,
    FinancialHealthMetrics,
    GrowthChannelBreakdown,
    HostOverview,
    KitchenPerformance,
    KitchenRevenue,
    ModerationQueueMetrics,
    PaymentMethodBreakdown,
    PlatformGrowthMetrics,
    PlatformOverviewMetrics,
    RecentBooking,
    RegionPerformance,
    RevenueAnalytics,
    TimeSeriesData,
    TimeSlotPopularity,
    Timeframe,
)
from prep.models.orm import (
    Booking,
    BookingStatus,
    Kitchen,
    KitchenModerationEvent,
    OperationalExpense,
    Review,
    User as UserORM,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

HOST_CACHE_TTL_SECONDS = 300
PLATFORM_CACHE_TTL_SECONDS = 600
ADMIN_CACHE_TTL_SECONDS = 180
FORECAST_MONTHS = 6


def _timeframe_start(timeframe: Timeframe, *, now: datetime) -> datetime:
    """Return the inclusive start datetime for the requested timeframe."""

    if timeframe == Timeframe.DAY:
        return now - timedelta(days=1)
    if timeframe == Timeframe.WEEK:
        return now - timedelta(days=7)
    if timeframe == Timeframe.MONTH:
        return now - timedelta(days=30)
    if timeframe == Timeframe.YEAR:
        return now - timedelta(days=365)
    return now - timedelta(days=30)


def _safe_decimal(value: Any) -> Decimal:
    """Cast arbitrary numeric values to :class:`Decimal`."""

    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _safe_float(value: Any) -> float:
    """Return a floating point representation for analytics output."""

    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(Decimal(str(value)))
    except Exception:  # pragma: no cover - defensive conversion guard
        return 0.0


def _safe_int(value: Any) -> int:
    """Return an integer representation."""

    if value is None:
        return 0
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except Exception:  # pragma: no cover - defensive conversion guard
        return 0


def _add_months(dt: datetime, months: int) -> datetime:
    """Return a datetime shifted by ``months`` months preserving the day."""

    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


class AnalyticsDashboardService:
    """Application service powering analytics dashboard endpoints."""

    def __init__(self, session: AsyncSession, redis_client: Any) -> None:
        self._session = session
        self._redis = redis_client

    async def _get_cached(self, key: str, model_type: type[BaseModel]) -> Any | None:
        try:
            cached = await self._redis.get(key)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to read analytics cache", extra={"cache_key": key})
            return None
        if not cached:
            return None
        try:
            return model_type.model_validate_json(cached)
        except ValidationError:
            logger.warning("Invalid cached analytics payload", extra={"cache_key": key})
            return None

    async def _set_cache(self, key: str, value: Any, ttl: int) -> None:
        try:
            await self._redis.setex(key, ttl, value.model_dump_json())
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to persist analytics cache", extra={"cache_key": key})

    async def _get_cached_list(self, key: str, model_type: type[BaseModel]) -> list[BaseModel] | None:
        try:
            raw = await self._redis.get(key)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to read list cache", extra={"cache_key": key})
            return None
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            logger.warning("Invalid cached list payload", extra={"cache_key": key})
            return None
        items: list[BaseModel] = []
        for entry in payload:
            try:
                items.append(model_type.model_validate(entry))
            except ValidationError:
                logger.warning("Failed to hydrate cached item", extra={"cache_key": key})
                return None
        return items

    async def _set_cached_list(self, key: str, ttl: int, values: Sequence[BaseModel]) -> None:
        try:
            payload = json.dumps([value.model_dump(mode="json") for value in values])
            await self._redis.setex(key, ttl, payload)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to cache list payload", extra={"cache_key": key})

    async def _ensure_host(self, host_id: UUID) -> UserORM:
        host = await self._session.get(UserORM, host_id)
        if host is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Host {host_id} not found"
            )
        return host

    async def get_host_overview(self, host_id: UUID) -> HostOverview:
        cache_key = f"analytics:host:{host_id}:overview"
        cached = await self._get_cached(cache_key, HostOverview)
        if cached:
            return cached
        await self._ensure_host(host_id)
        try:
            overview = await self._build_host_overview(host_id)
        except SQLAlchemyError as exc:  # pragma: no cover - propagated as HTTP error
            logger.exception("Failed to compute host overview", extra={"host_id": str(host_id)})
            raise HTTPException(status_code=500, detail="Unable to load host analytics") from exc
        await self._set_cache(cache_key, overview, HOST_CACHE_TTL_SECONDS)
        return overview

    async def get_host_booking_analytics(self, host_id: UUID, timeframe: Timeframe) -> BookingAnalytics:
        cache_key = f"analytics:host:{host_id}:bookings:{timeframe.value}"
        cached = await self._get_cached(cache_key, BookingAnalytics)
        if cached:
            return cached
        await self._ensure_host(host_id)
        try:
            analytics = await self._build_host_booking_analytics(host_id, timeframe)
        except SQLAlchemyError as exc:
            logger.exception(
                "Failed to compute booking analytics",
                extra={"host_id": str(host_id), "timeframe": timeframe.value},
            )
            raise HTTPException(status_code=500, detail="Unable to load booking analytics") from exc
        await self._set_cache(cache_key, analytics, HOST_CACHE_TTL_SECONDS)
        return analytics

    async def get_host_revenue_analytics(self, host_id: UUID, timeframe: Timeframe) -> RevenueAnalytics:
        cache_key = f"analytics:host:{host_id}:revenue:{timeframe.value}"
        cached = await self._get_cached(cache_key, RevenueAnalytics)
        if cached:
            return cached
        await self._ensure_host(host_id)
        try:
            analytics = await self._build_revenue_analytics(host_id=host_id, timeframe=timeframe)
        except SQLAlchemyError as exc:
            logger.exception(
                "Failed to compute revenue analytics",
                extra={"host_id": str(host_id), "timeframe": timeframe.value},
            )
            raise HTTPException(status_code=500, detail="Unable to load revenue analytics") from exc
        await self._set_cache(cache_key, analytics, HOST_CACHE_TTL_SECONDS)
        return analytics

    async def get_host_kitchen_comparison(self, host_id: UUID) -> list[KitchenPerformance]:
        cache_key = f"analytics:host:{host_id}:kitchens"
        cached = await self._get_cached_list(cache_key, KitchenPerformance)
        if cached:
            return [item for item in cached]
        await self._ensure_host(host_id)
        try:
            performances = await self._build_kitchen_performance(host_id)
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute kitchen comparison", extra={"host_id": str(host_id)})
            raise HTTPException(status_code=500, detail="Unable to load kitchen analytics") from exc
        await self._set_cached_list(cache_key, HOST_CACHE_TTL_SECONDS, performances)
        return performances

    async def get_platform_overview(self) -> PlatformOverviewMetrics:
        cache_key = "analytics:platform:overview"
        cached = await self._get_cached(cache_key, PlatformOverviewMetrics)
        if cached:
            return cached
        try:
            overview = await self._build_platform_overview()
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute platform overview")
            raise HTTPException(status_code=500, detail="Unable to load platform analytics") from exc
        await self._set_cache(cache_key, overview, PLATFORM_CACHE_TTL_SECONDS)
        return overview

    async def get_platform_revenue(self, timeframe: Timeframe) -> RevenueAnalytics:
        cache_key = f"analytics:platform:revenue:{timeframe.value}"
        cached = await self._get_cached(cache_key, RevenueAnalytics)
        if cached:
            return cached
        try:
            analytics = await self._build_revenue_analytics(host_id=None, timeframe=timeframe)
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute platform revenue", extra={"timeframe": timeframe.value})
            raise HTTPException(status_code=500, detail="Unable to load platform revenue analytics") from exc
        await self._set_cache(cache_key, analytics, PLATFORM_CACHE_TTL_SECONDS)
        return analytics

    async def get_platform_growth(self) -> PlatformGrowthMetrics:
        cache_key = "analytics:platform:growth"
        cached = await self._get_cached(cache_key, PlatformGrowthMetrics)
        if cached:
            return cached
        try:
            metrics = await self._build_growth_metrics()
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute platform growth metrics")
            raise HTTPException(status_code=500, detail="Unable to load growth analytics") from exc
        await self._set_cache(cache_key, metrics, PLATFORM_CACHE_TTL_SECONDS)
        return metrics

    async def get_platform_regions(self) -> list[RegionPerformance]:
        cache_key = "analytics:platform:regions"
        cached = await self._get_cached_list(cache_key, RegionPerformance)
        if cached:
            return [item for item in cached]
        try:
            regions = await self._build_region_performance()
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute regional performance")
            raise HTTPException(status_code=500, detail="Unable to load regional analytics") from exc
        await self._set_cached_list(cache_key, PLATFORM_CACHE_TTL_SECONDS, regions)
        return regions

    async def get_moderation_metrics(self) -> ModerationQueueMetrics:
        cache_key = "analytics:admin:moderation"
        cached = await self._get_cached(cache_key, ModerationQueueMetrics)
        if cached:
            return cached
        try:
            metrics = await self._build_moderation_metrics()
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute moderation metrics")
            raise HTTPException(status_code=500, detail="Unable to load moderation analytics") from exc
        await self._set_cache(cache_key, metrics, ADMIN_CACHE_TTL_SECONDS)
        return metrics

    async def get_admin_performance(self) -> AdminPerformanceMetrics:
        cache_key = "analytics:admin:performance"
        cached = await self._get_cached(cache_key, AdminPerformanceMetrics)
        if cached:
            return cached
        try:
            metrics = await self._build_admin_performance()
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute admin performance metrics")
            raise HTTPException(status_code=500, detail="Unable to load admin performance analytics") from exc
        await self._set_cache(cache_key, metrics, ADMIN_CACHE_TTL_SECONDS)
        return metrics

    async def get_financial_health(self) -> FinancialHealthMetrics:
        cache_key = "analytics:admin:financial"
        cached = await self._get_cached(cache_key, FinancialHealthMetrics)
        if cached:
            return cached
        try:
            metrics = await self._build_financial_health()
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute financial health metrics")
            raise HTTPException(status_code=500, detail="Unable to load financial analytics") from exc
        await self._set_cache(cache_key, metrics, ADMIN_CACHE_TTL_SECONDS)
        return metrics

    async def _build_host_overview(self, host_id: UUID) -> HostOverview:
        now = datetime.now(tz=UTC)
        thirty_days_ago = now - timedelta(days=30)

        kitchen_counts = await self._session.execute(
            select(
                func.count(Kitchen.id),
                func.sum(case((Kitchen.published.is_(True), 1), else_=0)),
            ).where(Kitchen.host_id == host_id)
        )
        total_kitchens, active_kitchens = kitchen_counts.one()
        total_kitchens = _safe_int(total_kitchens)
        active_kitchens = _safe_int(active_kitchens)

        revenue_case = case(
            (Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]), Booking.total_amount),
            else_=0,
        )
        occupied_hours_case = case(
            (Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]),
             func.extract("epoch", Booking.end_time - Booking.start_time) / 3600.0),
            else_=0,
        )
        booking_counts = await self._session.execute(
            select(
                func.count(Booking.id),
                func.sum(case((Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]), 1), else_=0)),
                func.sum(case((Booking.status == BookingStatus.CANCELLED, 1), else_=0)),
                func.coalesce(func.sum(revenue_case), 0),
                func.coalesce(func.avg(Review.rating), 0),
                func.coalesce(func.sum(occupied_hours_case), 0),
            )
            .outerjoin(Review, Review.booking_id == Booking.id)
            .where(Booking.host_id == host_id)
        )
        (
            total_bookings,
            confirmed_bookings,
            cancelled_bookings,
            total_revenue,
            average_rating,
            occupied_hours,
        ) = booking_counts.one()

        recent_revenue_row = await self._session.execute(
            select(func.coalesce(func.sum(revenue_case), 0)).where(
                Booking.host_id == host_id,
                Booking.start_time >= thirty_days_ago,
            )
        )
        last_30_days_revenue = recent_revenue_row.scalar() or Decimal("0")

        recent_hours_row = await self._session.execute(
            select(func.coalesce(func.sum(occupied_hours_case), 0)).where(
                Booking.host_id == host_id,
                Booking.start_time >= thirty_days_ago,
            )
        )
        occupied_hours_last_30 = recent_hours_row.scalar() or 0.0

        capacity_hours = total_kitchens * 30 * 12
        occupancy_rate = 0.0
        if capacity_hours:
            occupancy_rate = min(100.0, float(occupied_hours_last_30) / capacity_hours * 100)

        confirmed = _safe_float(confirmed_bookings)
        cancelled = _safe_float(cancelled_bookings)
        response_rate = 0.0
        if confirmed + cancelled:
            response_rate = (confirmed / (confirmed + cancelled)) * 100

        revenue_by_kitchen_stmt = (
            select(
                Booking.kitchen_id,
                Kitchen.name,
                func.count(Booking.id),
                func.coalesce(func.sum(revenue_case), 0),
                func.coalesce(func.avg(Review.rating), 0),
                func.coalesce(func.sum(occupied_hours_case), 0),
            )
            .join(Kitchen, Kitchen.id == Booking.kitchen_id)
            .outerjoin(Review, Review.booking_id == Booking.id)
            .where(Booking.host_id == host_id)
            .group_by(Booking.kitchen_id, Kitchen.name)
            .order_by(desc(func.coalesce(func.sum(revenue_case), 0)))
            .limit(5)
        )
        top_rows = await self._session.execute(revenue_by_kitchen_stmt)
        kitchen_performance = [
            KitchenPerformance(
                kitchen_id=row[0],
                kitchen_name=row[1],
                bookings=_safe_int(row[2]),
                revenue=_safe_decimal(row[3]),
                rating=float(row[4] or 0.0),
                occupancy_rate=min(100.0, float(row[5] or 0.0) / (30 * 12) * 100) if row[5] else 0.0,
            )
            for row in top_rows
        ]

        Customer = aliased(UserORM)
        recent_stmt = (
            select(
                Booking.id,
                Booking.kitchen_id,
                Kitchen.name,
                Customer.full_name,
                Booking.start_time,
                Booking.end_time,
                Booking.status,
                Booking.total_amount,
            )
            .join(Kitchen, Kitchen.id == Booking.kitchen_id)
            .join(Customer, Customer.id == Booking.customer_id)
            .where(Booking.host_id == host_id)
            .order_by(Booking.start_time.desc())
            .limit(5)
        )
        recent_rows = await self._session.execute(recent_stmt)
        recent_bookings = [
            RecentBooking(
                booking_id=row[0],
                kitchen_id=row[1],
                kitchen_name=row[2],
                guest_name=row[3],
                start_time=row[4],
                end_time=row[5],
                status=row[6].value if isinstance(row[6], BookingStatus) else str(row[6]),
                total_amount=_safe_decimal(row[7]),
            )
            for row in recent_rows
        ]

        return HostOverview(
            total_kitchens=total_kitchens,
            active_kitchens=active_kitchens,
            total_bookings=_safe_int(total_bookings),
            total_revenue=_safe_decimal(total_revenue),
            average_rating=float(average_rating or 0.0),
            occupancy_rate=occupancy_rate,
            response_rate=response_rate,
            last_30_days_revenue=_safe_decimal(last_30_days_revenue),
            top_performing_kitchen=kitchen_performance[0] if kitchen_performance else None,
            recent_bookings=recent_bookings,
        )

    async def get_host_kitchen_comparison(self, host_id: UUID) -> list[KitchenPerformance]:
        cache_key = f"analytics:host:{host_id}:kitchens"
        cached = await self._get_cached(cache_key, list[KitchenPerformance])  # type: ignore[arg-type]
        if cached:
            return cached
        await self._ensure_host(host_id)
        try:
            performances = await self._build_kitchen_performance(host_id)
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute kitchen comparison", extra={"host_id": str(host_id)})
            raise HTTPException(status_code=500, detail="Unable to load kitchen analytics") from exc
        try:
            payload = [item.model_dump() for item in performances]
            await self._redis.setex(cache_key, HOST_CACHE_TTL_SECONDS, AnalyticsDashboardService._encode_payload(payload))
        except Exception:  # pragma: no cover - fallback logging
            logger.exception("Failed to cache kitchen comparison", extra={"host_id": str(host_id)})
        return performances

    @staticmethod
    def _encode_payload(payload: Any) -> str:
        """Encode complex payloads for the Redis cache."""

        if hasattr(payload, "model_dump_json"):
            return payload.model_dump_json()
        return str(payload)

    async def get_platform_overview(self) -> PlatformOverviewMetrics:
        cache_key = "analytics:platform:overview"
        cached = await self._get_cached(cache_key, PlatformOverviewMetrics)
        if cached:
            return cached
        try:
            overview = await self._build_platform_overview()
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute platform overview")
            raise HTTPException(status_code=500, detail="Unable to load platform analytics") from exc
        await self._set_cache(cache_key, overview, PLATFORM_CACHE_TTL_SECONDS)
        return overview

    async def get_platform_revenue(self, timeframe: Timeframe) -> RevenueAnalytics:
        cache_key = f"analytics:platform:revenue:{timeframe.value}"
        cached = await self._get_cached(cache_key, RevenueAnalytics)
        if cached:
            return cached
        try:
            analytics = await self._build_revenue_analytics(host_id=None, timeframe=timeframe)
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute platform revenue", extra={"timeframe": timeframe.value})
            raise HTTPException(status_code=500, detail="Unable to load platform revenue analytics") from exc
        await self._set_cache(cache_key, analytics, PLATFORM_CACHE_TTL_SECONDS)
        return analytics

    async def get_platform_growth(self) -> PlatformGrowthMetrics:
        cache_key = "analytics:platform:growth"
        cached = await self._get_cached(cache_key, PlatformGrowthMetrics)
        if cached:
            return cached
        try:
            metrics = await self._build_growth_metrics()
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute platform growth metrics")
            raise HTTPException(status_code=500, detail="Unable to load growth analytics") from exc
        await self._set_cache(cache_key, metrics, PLATFORM_CACHE_TTL_SECONDS)
        return metrics

    async def get_platform_regions(self) -> list[RegionPerformance]:
        cache_key = "analytics:platform:regions"
        cached = await self._get_cached(cache_key, list[RegionPerformance])  # type: ignore[arg-type]
        if cached:
            return cached
        try:
            regions = await self._build_region_performance()
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute regional performance")
            raise HTTPException(status_code=500, detail="Unable to load regional analytics") from exc
        try:
            payload = [item.model_dump() for item in regions]
            await self._redis.setex(cache_key, PLATFORM_CACHE_TTL_SECONDS, AnalyticsDashboardService._encode_payload(payload))
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to cache regional analytics")
        return regions

    async def get_moderation_metrics(self) -> ModerationQueueMetrics:
        cache_key = "analytics:admin:moderation"
        cached = await self._get_cached(cache_key, ModerationQueueMetrics)
        if cached:
            return cached
        try:
            metrics = await self._build_moderation_metrics()
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute moderation metrics")
            raise HTTPException(status_code=500, detail="Unable to load moderation analytics") from exc
        await self._set_cache(cache_key, metrics, ADMIN_CACHE_TTL_SECONDS)
        return metrics

    async def get_admin_performance(self) -> AdminPerformanceMetrics:
        cache_key = "analytics:admin:performance"
        cached = await self._get_cached(cache_key, AdminPerformanceMetrics)
        if cached:
            return cached
        try:
            metrics = await self._build_admin_performance()
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute admin performance metrics")
            raise HTTPException(status_code=500, detail="Unable to load admin performance analytics") from exc
        await self._set_cache(cache_key, metrics, ADMIN_CACHE_TTL_SECONDS)
        return metrics

    async def get_financial_health(self) -> FinancialHealthMetrics:
        cache_key = "analytics:admin:financial"
        cached = await self._get_cached(cache_key, FinancialHealthMetrics)
        if cached:
            return cached
        try:
            metrics = await self._build_financial_health()
        except SQLAlchemyError as exc:
            logger.exception("Failed to compute financial health metrics")
            raise HTTPException(status_code=500, detail="Unable to load financial analytics") from exc
        await self._set_cache(cache_key, metrics, ADMIN_CACHE_TTL_SECONDS)
        return metrics

    async def _build_host_booking_analytics(self, host_id: UUID, timeframe: Timeframe) -> BookingAnalytics:
        now = datetime.now(tz=UTC)
        start = _timeframe_start(timeframe, now=now)

        total_case = func.count(Booking.id)
        confirmed_case = func.sum(case((Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]), 1), else_=0))
        cancelled_case = func.sum(case((Booking.status == BookingStatus.CANCELLED, 1), else_=0))

        counts_row = await self._session.execute(
            select(total_case, confirmed_case, cancelled_case).where(
                Booking.host_id == host_id,
                Booking.created_at >= start,
            )
        )
        total_bookings, confirmed_bookings, cancelled_bookings = counts_row.one()

        granularity = "day"
        if timeframe == Timeframe.YEAR:
            granularity = "month"
        elif timeframe == Timeframe.WEEK:
            granularity = "day"
        elif timeframe == Timeframe.DAY:
            granularity = "hour"

        bucket = func.date_trunc(granularity, Booking.created_at).label("bucket")
        trend_stmt = (
            select(bucket, func.count(Booking.id))
            .where(Booking.host_id == host_id, Booking.created_at >= start)
            .group_by(bucket)
            .order_by(bucket)
        )
        trend_rows = await self._session.execute(trend_stmt)
        booking_trends = []
        for bucket_value, count in trend_rows:
            bucket_dt: datetime = bucket_value if isinstance(bucket_value, datetime) else datetime.combine(bucket_value, datetime.min.time(), tzinfo=UTC)
            booking_trends.append(
                TimeSeriesData(date=bucket_dt.date(), value=_safe_int(count))
            )

        time_slot_stmt = (
            select(func.to_char(Booking.start_time, "HH24:MI"), func.count(Booking.id))
            .where(
                Booking.host_id == host_id,
                Booking.created_at >= start,
                Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]),
            )
            .group_by(func.to_char(Booking.start_time, "HH24:MI"))
            .order_by(desc(func.count(Booking.id)))
            .limit(5)
        )
        slot_rows = await self._session.execute(time_slot_stmt)
        popular_time_slots = [
            TimeSlotPopularity(time_slot=row[0], booking_count=_safe_int(row[1]))
            for row in slot_rows
        ]

        cancellation_stmt = (
            select(Booking.cancellation_reason, func.count(Booking.id))
            .where(
                Booking.host_id == host_id,
                Booking.created_at >= start,
                Booking.status == BookingStatus.CANCELLED,
                Booking.cancellation_reason.isnot(None),
            )
            .group_by(Booking.cancellation_reason)
            .order_by(desc(func.count(Booking.id)))
        )
        cancellation_rows = await self._session.execute(cancellation_stmt)
        cancellation_reasons = [
            CancellationReason(reason=row[0], count=_safe_int(row[1]))
            for row in cancellation_rows
        ]

        repeat_subquery = (
            select(Booking.customer_id)
            .where(Booking.host_id == host_id)
            .group_by(Booking.customer_id)
            .having(func.count(Booking.id) > 1)
            .subquery()
        )
        repeat_count_row = await self._session.execute(select(func.count()).select_from(repeat_subquery))
        repeat_customers = repeat_count_row.scalar() or 0
        total_customers_row = await self._session.execute(
            select(func.count(func.distinct(Booking.customer_id))).where(Booking.host_id == host_id)
        )
        total_customers = total_customers_row.scalar() or 0
        guest_retention_rate = 0.0
        if total_customers:
            guest_retention_rate = (repeat_customers / total_customers) * 100

        total = _safe_float(total_bookings)
        confirmed = _safe_float(confirmed_bookings)
        conversion_rate = (confirmed / total) * 100 if total else 0.0

        return BookingAnalytics(
            total_bookings=_safe_int(total_bookings),
            confirmed_bookings=_safe_int(confirmed_bookings),
            cancelled_bookings=_safe_int(cancelled_bookings),
            conversion_rate=conversion_rate,
            booking_trends=booking_trends,
            popular_time_slots=popular_time_slots,
            cancellation_reasons=cancellation_reasons,
            guest_retention_rate=guest_retention_rate,
        )

    async def _build_revenue_analytics(self, *, host_id: UUID | None, timeframe: Timeframe) -> RevenueAnalytics:
        now = datetime.now(tz=UTC)
        start = _timeframe_start(timeframe, now=now)

        filters = [Booking.created_at >= start]
        if host_id is not None:
            filters.append(Booking.host_id == host_id)

        revenue_case = case(
            (Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]), Booking.total_amount),
            else_=0,
        )

        total_row = await self._session.execute(select(func.coalesce(func.sum(revenue_case), 0), func.count(Booking.id)).where(*filters))
        total_revenue, booking_count = total_row.one()

        granularity = "day"
        if timeframe == Timeframe.YEAR:
            granularity = "month"
        elif timeframe == Timeframe.WEEK:
            granularity = "day"
        elif timeframe == Timeframe.DAY:
            granularity = "hour"

        bucket = func.date_trunc(granularity, Booking.created_at).label("bucket")
        trend_stmt = (
            select(bucket, func.coalesce(func.sum(revenue_case), 0))
            .where(*filters)
            .group_by(bucket)
            .order_by(bucket)
        )
        trend_rows = await self._session.execute(trend_stmt)
        revenue_trends = []
        for bucket_value, value in trend_rows:
            bucket_dt: datetime = bucket_value if isinstance(bucket_value, datetime) else datetime.combine(bucket_value, datetime.min.time(), tzinfo=UTC)
            revenue_trends.append(TimeSeriesData(date=bucket_dt.date(), value=_safe_decimal(value)))

        kitchen_stmt = (
            select(
                Booking.kitchen_id,
                Kitchen.name,
                func.count(Booking.id),
                func.coalesce(func.sum(revenue_case), 0),
            )
            .join(Kitchen, Kitchen.id == Booking.kitchen_id)
            .where(*filters)
            .group_by(Booking.kitchen_id, Kitchen.name)
            .order_by(desc(func.coalesce(func.sum(revenue_case), 0)))
        )
        kitchen_rows = await self._session.execute(kitchen_stmt)
        revenue_by_kitchen = [
            KitchenRevenue(
                kitchen_id=row[0],
                kitchen_name=row[1],
                booking_count=_safe_int(row[2]),
                total_revenue=_safe_decimal(row[3]),
            )
            for row in kitchen_rows
        ]

        average_booking_value = Decimal("0")
        confirmed_count_row = await self._session.execute(
            select(func.count(Booking.id)).where(
                *filters,
                Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]),
            )
        )
        confirmed_count = confirmed_count_row.scalar() or 0
        if confirmed_count:
            average_booking_value = _safe_decimal(total_revenue) / confirmed_count

        monthly_stmt = (
            select(
                func.date_trunc("month", Booking.created_at).label("bucket"),
                func.coalesce(func.sum(revenue_case), 0),
            )
            .where(*filters)
            .group_by("bucket")
            .order_by("bucket")
        )
        monthly_rows = await self._session.execute(monthly_stmt)
        monthly_points: list[tuple[datetime, Decimal]] = [
            (
                bucket if isinstance(bucket, datetime) else datetime.combine(bucket, datetime.min.time(), tzinfo=UTC),
                _safe_decimal(value),
            )
            for bucket, value in monthly_rows
        ]
        revenue_forecast = self._build_forecast(monthly_points)

        payment_stmt = (
            select(Booking.payment_method, func.coalesce(func.sum(revenue_case), 0))
            .where(*filters)
            .group_by(Booking.payment_method)
        )
        payment_rows = await self._session.execute(payment_stmt)
        method_totals = {row[0] or "unknown": _safe_decimal(row[1]) for row in payment_rows}
        total_revenue_decimal = _safe_decimal(total_revenue)
        total_revenue_value = total_revenue_decimal if total_revenue_decimal != 0 else Decimal("1")
        payment_breakdown = [
            PaymentMethodBreakdown(
                method=method,
                percentage=float((amount / total_revenue_value) * 100) if total_revenue_value else 0.0,
            )
            for method, amount in method_totals.items()
        ]

        return RevenueAnalytics(
            total_revenue=total_revenue_decimal,
            revenue_trends=revenue_trends,
            revenue_by_kitchen=revenue_by_kitchen,
            average_booking_value=average_booking_value,
            revenue_forecast=revenue_forecast,
            payment_methods_breakdown=payment_breakdown,
        )

    def _build_forecast(self, monthly_points: Sequence[tuple[datetime, Decimal]]) -> list[TimeSeriesData]:
        if not monthly_points:
            return []
        values = [point[1] for point in monthly_points]
        growth_rates = []
        for previous, current in zip(values, values[1:]):
            if previous != 0:
                growth_rates.append((current - previous) / previous)
        average_growth = sum(growth_rates, Decimal("0")) / len(growth_rates) if growth_rates else Decimal("0.05")
        last_date = monthly_points[-1][0]
        last_value = values[-1]
        forecast: list[TimeSeriesData] = []
        current_value = last_value
        for offset in range(1, FORECAST_MONTHS + 1):
            current_value = current_value * (Decimal("1") + average_growth)
            forecast_date = _add_months(last_date, offset)
            forecast.append(TimeSeriesData(date=forecast_date.date(), value=current_value.quantize(Decimal("0.01"))))
        return forecast

    async def _build_kitchen_performance(self, host_id: UUID) -> list[KitchenPerformance]:
        revenue_case = case(
            (Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]), Booking.total_amount),
            else_=0,
        )
        occupancy_case = case(
            (Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]),
             func.extract("epoch", Booking.end_time - Booking.start_time) / 3600.0),
            else_=0,
        )
        stmt = (
            select(
                Kitchen.id,
                Kitchen.name,
                func.count(Booking.id),
                func.coalesce(func.sum(revenue_case), 0),
                func.coalesce(func.avg(Review.rating), 0),
                func.coalesce(func.sum(occupancy_case), 0),
            )
            .join(Booking, Booking.kitchen_id == Kitchen.id)
            .outerjoin(Review, Review.kitchen_id == Kitchen.id)
            .where(Kitchen.host_id == host_id)
            .group_by(Kitchen.id, Kitchen.name)
            .order_by(desc(func.coalesce(func.sum(revenue_case), 0)))
        )
        rows = await self._session.execute(stmt)
        performances = [
            KitchenPerformance(
                kitchen_id=row[0],
                kitchen_name=row[1],
                bookings=_safe_int(row[2]),
                revenue=_safe_decimal(row[3]),
                rating=float(row[4] or 0.0),
                occupancy_rate=min(100.0, float(row[5] or 0.0) / (30 * 12) * 100) if row[5] else 0.0,
            )
            for row in rows
        ]
        return performances

    async def _build_platform_overview(self) -> PlatformOverviewMetrics:
        now = datetime.now(tz=UTC)
        thirty_days_ago = now - timedelta(days=30)

        user_counts_row = await self._session.execute(
            select(
                func.count(UserORM.id),
                func.count(func.nullif(UserORM.is_admin, True)),
            )
        )
        total_users, non_admin_users = user_counts_row.one()

        host_counts_row = await self._session.execute(
            select(func.count(func.distinct(Kitchen.host_id))).where(Kitchen.published.is_(True))
        )
        total_hosts = host_counts_row.scalar() or 0

        kitchen_counts_row = await self._session.execute(
            select(func.count(Kitchen.id), func.sum(case((Kitchen.published.is_(True), 1), else_=0)))
        )
        total_kitchens, active_kitchens = kitchen_counts_row.one()

        revenue_case = case(
            (Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]), Booking.total_amount),
            else_=0,
        )
        bookings_row = await self._session.execute(
            select(
                func.count(Booking.id),
                func.coalesce(func.sum(revenue_case), 0),
            )
        )
        total_bookings, total_revenue = bookings_row.one()

        recent_users_row = await self._session.execute(
            select(func.count(UserORM.id)).where(UserORM.created_at >= thirty_days_ago)
        )
        new_users = recent_users_row.scalar() or 0

        bookings_trend_rows = await self._session.execute(
            select(
                func.date_trunc("day", Booking.created_at).label("bucket"),
                func.count(Booking.id),
            )
            .where(Booking.created_at >= thirty_days_ago)
            .group_by("bucket")
            .order_by("bucket")
        )
        bookings_trend = [
            TimeSeriesData(
                date=(bucket if isinstance(bucket, datetime) else datetime.combine(bucket, datetime.min.time(), tzinfo=UTC)).date(),
                value=_safe_int(count),
            )
            for bucket, count in bookings_trend_rows
        ]

        revenue_trend_rows = await self._session.execute(
            select(
                func.date_trunc("day", Booking.created_at).label("bucket"),
                func.coalesce(func.sum(revenue_case), 0),
            )
            .where(Booking.created_at >= thirty_days_ago)
            .group_by("bucket")
            .order_by("bucket")
        )
        revenue_trend = [
            TimeSeriesData(
                date=(bucket if isinstance(bucket, datetime) else datetime.combine(bucket, datetime.min.time(), tzinfo=UTC)).date(),
                value=_safe_decimal(amount),
            )
            for bucket, amount in revenue_trend_rows
        ]

        return PlatformOverviewMetrics(
            total_users=_safe_int(total_users),
            total_hosts=_safe_int(total_hosts),
            total_kitchens=_safe_int(total_kitchens),
            active_kitchens=_safe_int(active_kitchens),
            total_bookings=_safe_int(total_bookings),
            total_revenue=_safe_decimal(total_revenue),
            new_users_last_30_days=_safe_int(new_users),
            bookings_trend=bookings_trend,
            revenue_trend=revenue_trend,
        )

    async def _build_growth_metrics(self) -> PlatformGrowthMetrics:
        now = datetime.now(tz=UTC)
        twelve_weeks_ago = now - timedelta(weeks=12)

        user_signup_rows = await self._session.execute(
            select(
                func.date_trunc("week", UserORM.created_at).label("bucket"),
                func.count(UserORM.id),
            )
            .where(UserORM.created_at >= twelve_weeks_ago, UserORM.is_admin.is_(False))
            .group_by("bucket")
            .order_by("bucket")
        )
        user_signups = [
            TimeSeriesData(
                date=(bucket if isinstance(bucket, datetime) else datetime.combine(bucket, datetime.min.time(), tzinfo=UTC)).date(),
                value=_safe_int(count),
            )
            for bucket, count in user_signup_rows
        ]

        host_signup_rows = await self._session.execute(
            select(
                func.date_trunc("week", Kitchen.created_at).label("bucket"),
                func.count(func.distinct(Kitchen.host_id)),
            )
            .where(Kitchen.created_at >= twelve_weeks_ago)
            .group_by("bucket")
            .order_by("bucket")
        )
        host_signups = [
            TimeSeriesData(
                date=(bucket if isinstance(bucket, datetime) else datetime.combine(bucket, datetime.min.time(), tzinfo=UTC)).date(),
                value=_safe_int(count),
            )
            for bucket, count in host_signup_rows
        ]

        bookings_rows = await self._session.execute(
            select(
                func.date_trunc("week", Booking.created_at).label("bucket"),
                func.count(Booking.id),
            )
            .where(Booking.created_at >= twelve_weeks_ago)
            .group_by("bucket")
            .order_by("bucket")
        )
        bookings_by_week = {
            (bucket if isinstance(bucket, datetime) else datetime.combine(bucket, datetime.min.time(), tzinfo=UTC)).date(): _safe_int(count)
            for bucket, count in bookings_rows
        }

        conversion_series: list[TimeSeriesData] = []
        for signup in user_signups:
            bookings = bookings_by_week.get(signup.date, 0)
            conversion = (bookings / signup.value) * 100 if signup.value else 0.0
            conversion_series.append(TimeSeriesData(date=signup.date, value=conversion))

        channel_rows = await self._session.execute(
            select(Booking.source, func.count(Booking.id), func.coalesce(func.sum(case((Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]), Booking.total_amount), else_=0)), 0))
            .where(Booking.created_at >= twelve_weeks_ago)
            .group_by(Booking.source)
        )
        acquisition_channels: list[GrowthChannelBreakdown] = []
        for source, count, revenue in channel_rows:
            count_int = _safe_int(count)
            revenue_decimal = _safe_decimal(revenue)
            conversion_rate = 0.0
            if count_int:
                conversion_rate = float(revenue_decimal / count_int) if revenue_decimal else 0.0
            acquisition_channels.append(
                GrowthChannelBreakdown(
                    channel=source or "organic",
                    signups=count_int,
                    conversion_rate=conversion_rate,
                )
            )

        return PlatformGrowthMetrics(
            user_signups=user_signups,
            host_signups=host_signups,
            conversion_rate=conversion_series,
            acquisition_channels=acquisition_channels,
        )

    async def _build_region_performance(self) -> list[RegionPerformance]:
        now = datetime.now(tz=UTC)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)

        revenue_case = case(
            (Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]), Booking.total_amount),
            else_=0,
        )

        current_rows = await self._session.execute(
            select(
                Kitchen.state,
                func.count(Booking.id),
                func.coalesce(func.sum(revenue_case), 0),
            )
            .join(Booking, Booking.kitchen_id == Kitchen.id, isouter=True)
            .where(Kitchen.published.is_(True), Booking.start_time >= thirty_days_ago)
            .group_by(Kitchen.state)
        )
        current_stats = {row[0] or "Unknown": (row[1], _safe_decimal(row[2])) for row in current_rows}

        previous_rows = await self._session.execute(
            select(
                Kitchen.state,
                func.count(Booking.id),
            )
            .join(Booking, Booking.kitchen_id == Kitchen.id, isouter=True)
            .where(
                Kitchen.published.is_(True),
                Booking.start_time >= sixty_days_ago,
                Booking.start_time < thirty_days_ago,
            )
            .group_by(Kitchen.state)
        )
        previous_stats = {row[0] or "Unknown": row[1] for row in previous_rows}

        regions: list[RegionPerformance] = []
        for region, (bookings, revenue) in current_stats.items():
            previous = previous_stats.get(region, 0)
            growth_rate = 0.0
            if previous:
                growth_rate = ((bookings - previous) / previous) * 100
            regions.append(
                RegionPerformance(
                    region=region,
                    bookings=_safe_int(bookings),
                    revenue=revenue,
                    growth_rate=growth_rate,
                )
            )
        regions.sort(key=lambda item: item.revenue, reverse=True)
        return regions

    async def _build_moderation_metrics(self) -> ModerationQueueMetrics:
        now = datetime.now(tz=UTC)
        forty_eight_hours_ago = now - timedelta(hours=48)
        thirty_days_ago = now - timedelta(days=30)

        pending_count_row = await self._session.execute(
            select(func.count(Kitchen.id)).where(Kitchen.moderation_status == "pending")
        )
        pending = pending_count_row.scalar() or 0

        in_review_row = await self._session.execute(
            select(func.count(Kitchen.id)).where(Kitchen.moderation_status == "changes_requested")
        )
        in_review = in_review_row.scalar() or 0

        escalated_row = await self._session.execute(
            select(func.count(KitchenModerationEvent.id)).where(
                KitchenModerationEvent.action == "escalated",
                KitchenModerationEvent.created_at >= thirty_days_ago,
            )
        )
        escalated = escalated_row.scalar() or 0

        sla_breach_row = await self._session.execute(
            select(func.count(Kitchen.id)).where(
                Kitchen.moderation_status == "pending",
                Kitchen.submitted_at <= forty_eight_hours_ago,
            )
        )
        sla_breaches = sla_breach_row.scalar() or 0

        review_time_row = await self._session.execute(
            select(
                func.avg(
                    func.extract(
                        "epoch",
                        KitchenModerationEvent.created_at - Kitchen.submitted_at,
                    )
                    / 3600.0
                )
            )
            .join(Kitchen, KitchenModerationEvent.kitchen_id == Kitchen.id)
            .where(KitchenModerationEvent.action.in_(["approved", "rejected"]))
        )
        average_review_time = review_time_row.scalar() or 0.0

        moderation_trend_rows = await self._session.execute(
            select(
                func.date_trunc("day", KitchenModerationEvent.created_at).label("bucket"),
                func.count(KitchenModerationEvent.id),
            )
            .where(KitchenModerationEvent.created_at >= thirty_days_ago)
            .group_by("bucket")
            .order_by("bucket")
        )
        moderation_trend = [
            TimeSeriesData(
                date=(bucket if isinstance(bucket, datetime) else datetime.combine(bucket, datetime.min.time(), tzinfo=UTC)).date(),
                value=_safe_int(count),
            )
            for bucket, count in moderation_trend_rows
        ]

        return ModerationQueueMetrics(
            pending=_safe_int(pending),
            in_review=_safe_int(in_review),
            escalated=_safe_int(escalated),
            sla_breaches=_safe_int(sla_breaches),
            average_review_time_hours=_safe_float(average_review_time),
            moderation_trend=moderation_trend,
        )

    async def _build_admin_performance(self) -> AdminPerformanceMetrics:
        thirty_days_ago = datetime.now(tz=UTC) - timedelta(days=30)

        resolved_case = case((KitchenModerationEvent.action.in_(["approved", "rejected"]), 1), else_=0)
        changes_requested_case = case((KitchenModerationEvent.action == "changes_requested", 1), else_=0)

        performance_rows = await self._session.execute(
            select(
                KitchenModerationEvent.admin_id,
                UserORM.full_name,
                func.sum(resolved_case),
                func.avg(
                    func.extract(
                        "epoch",
                        KitchenModerationEvent.created_at - Kitchen.submitted_at,
                    )
                    / 3600.0
                ),
                func.sum(changes_requested_case),
            )
            .join(UserORM, UserORM.id == KitchenModerationEvent.admin_id)
            .join(Kitchen, Kitchen.id == KitchenModerationEvent.kitchen_id)
            .where(KitchenModerationEvent.created_at >= thirty_days_ago)
            .group_by(KitchenModerationEvent.admin_id, UserORM.full_name)
        )

        team: list[AdminTeamMemberPerformance] = []
        total_resolved = 0
        total_changes_requested = 0
        for admin_id, admin_name, resolved, average_hours, changes_requested in performance_rows:
            resolved_count = _safe_int(resolved)
            total_resolved += resolved_count
            total_changes_requested += _safe_int(changes_requested)
            quality_score = 100.0
            if resolved_count:
                quality_score = max(0.0, 100.0 - (_safe_float(changes_requested) / resolved_count) * 100)
            team.append(
                AdminTeamMemberPerformance(
                    admin_id=admin_id,
                    admin_name=admin_name,
                    resolved_cases=resolved_count,
                    average_resolution_time_hours=_safe_float(average_hours),
                    quality_score=quality_score,
                )
            )

        backlog_row = await self._session.execute(
            select(func.count(Kitchen.id)).where(Kitchen.moderation_status == "pending")
        )
        backlog = backlog_row.scalar() or 0

        trend_rows = await self._session.execute(
            select(
                func.date_trunc("week", KitchenModerationEvent.created_at).label("bucket"),
                func.sum(resolved_case),
            )
            .where(KitchenModerationEvent.created_at >= thirty_days_ago)
            .group_by("bucket")
            .order_by("bucket")
        )
        productivity_trend = [
            TimeSeriesData(
                date=(bucket if isinstance(bucket, datetime) else datetime.combine(bucket, datetime.min.time(), tzinfo=UTC)).date(),
                value=_safe_int(count),
            )
            for bucket, count in trend_rows
        ]

        return AdminPerformanceMetrics(
            total_resolved=_safe_int(total_resolved),
            backlog=_safe_int(backlog),
            productivity_trend=productivity_trend,
            team=team,
        )

    async def _build_financial_health(self) -> FinancialHealthMetrics:
        now = datetime.now(tz=UTC)
        six_months_ago = now - timedelta(days=180)

        revenue_case = case(
            (Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]), Booking.total_amount),
            else_=0,
        )
        payout_case = case(
            (Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]), Booking.host_payout_amount),
            else_=0,
        )
        platform_fee_case = case(
            (Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]), Booking.platform_fee),
            else_=0,
        )

        totals_row = await self._session.execute(
            select(
                func.coalesce(func.sum(revenue_case), 0),
                func.coalesce(func.sum(payout_case), 0),
                func.coalesce(func.sum(platform_fee_case), 0),
            )
        )
        total_revenue, total_payouts, total_fees = totals_row.one()

        expense_row = await self._session.execute(
            select(func.coalesce(func.sum(OperationalExpense.amount), 0))
        )
        operational_expenses = expense_row.scalar() or Decimal("0")

        net_revenue = _safe_decimal(total_revenue) - _safe_decimal(total_payouts)
        gross_margin = 0.0
        revenue_decimal = _safe_decimal(total_revenue)
        if revenue_decimal:
            gross_margin = float((net_revenue / revenue_decimal) * 100)

        ebitda_margin = 0.0
        ebitda_base = revenue_decimal - _safe_decimal(operational_expenses)
        if revenue_decimal:
            ebitda_margin = float((ebitda_base / revenue_decimal) * 100)

        cash_on_hand = net_revenue - _safe_decimal(operational_expenses)
        monthly_expense_rows = await self._session.execute(
            select(
                func.date_trunc("month", OperationalExpense.incurred_on).label("bucket"),
                func.coalesce(func.sum(OperationalExpense.amount), 0),
            )
            .where(OperationalExpense.incurred_on >= six_months_ago)
            .group_by("bucket")
            .order_by("bucket")
        )
        expense_trend = [
            TimeSeriesData(
                date=(bucket if isinstance(bucket, datetime) else datetime.combine(bucket, datetime.min.time(), tzinfo=UTC)).date(),
                value=_safe_decimal(amount),
            )
            for bucket, amount in monthly_expense_rows
        ]

        monthly_revenue_rows = await self._session.execute(
            select(
                func.date_trunc("month", Booking.created_at).label("bucket"),
                func.coalesce(func.sum(revenue_case), 0),
            )
            .where(Booking.created_at >= six_months_ago)
            .group_by("bucket")
            .order_by("bucket")
        )
        revenue_trend = [
            TimeSeriesData(
                date=(bucket if isinstance(bucket, datetime) else datetime.combine(bucket, datetime.min.time(), tzinfo=UTC)).date(),
                value=_safe_decimal(amount),
            )
            for bucket, amount in monthly_revenue_rows
        ]

        average_monthly_expense = Decimal("0")
        if expense_trend:
            average_monthly_expense = sum((point.value for point in expense_trend), Decimal("0")) / len(expense_trend)

        burn_rate = average_monthly_expense
        runway_months = float(cash_on_hand / burn_rate) if burn_rate else float("inf")

        return FinancialHealthMetrics(
            total_revenue=revenue_decimal,
            net_revenue=net_revenue,
            operational_expenses=_safe_decimal(operational_expenses),
            gross_margin=gross_margin,
            ebitda_margin=ebitda_margin,
            cash_on_hand=cash_on_hand,
            burn_rate=burn_rate,
            runway_months=runway_months if runway_months != float("inf") else 0.0,
            revenue_trend=revenue_trend,
            expense_trend=expense_trend,
        )


async def get_dashboard_service(
    db: AsyncSession = Depends(get_db),
    redis_client: Any = Depends(get_redis),
) -> AnalyticsDashboardService:
    """FastAPI dependency that provisions the analytics service."""

    return AnalyticsDashboardService(db, redis_client)


def _ensure_host_access(user: UserORM, host_id: UUID) -> None:
    """Ensure a host-level request is authorized."""

    if user.is_admin or user.id == host_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this host analytics view")


@router.get("/host/{host_id}/overview", response_model=HostOverview)
async def get_host_overview(
    host_id: UUID,
    timeframe: Timeframe = Query(Timeframe.MONTH, description="Timeframe for cached analytics context"),
    current_user: UserORM = Depends(get_current_user),
    service: AnalyticsDashboardService = Depends(get_dashboard_service),
) -> HostOverview:
    """Return the primary dashboard overview for the host."""

    _ensure_host_access(current_user, host_id)
    _ = timeframe
    return await service.get_host_overview(host_id)


@router.get("/host/{host_id}/bookings", response_model=BookingAnalytics)
async def get_host_booking_analytics(
    host_id: UUID,
    timeframe: Timeframe = Query(Timeframe.MONTH),
    current_user: UserORM = Depends(get_current_user),
    service: AnalyticsDashboardService = Depends(get_dashboard_service),
) -> BookingAnalytics:
    """Return booking analytics for the requested host and timeframe."""

    _ensure_host_access(current_user, host_id)
    return await service.get_host_booking_analytics(host_id, timeframe)


@router.get("/host/{host_id}/revenue", response_model=RevenueAnalytics)
async def get_host_revenue_analytics(
    host_id: UUID,
    timeframe: Timeframe = Query(Timeframe.MONTH),
    current_user: UserORM = Depends(get_current_user),
    service: AnalyticsDashboardService = Depends(get_dashboard_service),
) -> RevenueAnalytics:
    """Return revenue analytics for the requested host and timeframe."""

    _ensure_host_access(current_user, host_id)
    return await service.get_host_revenue_analytics(host_id, timeframe)


@router.get("/host/{host_id}/kitchens", response_model=list[KitchenPerformance])
async def get_host_kitchen_comparison(
    host_id: UUID,
    current_user: UserORM = Depends(get_current_user),
    service: AnalyticsDashboardService = Depends(get_dashboard_service),
) -> list[KitchenPerformance]:
    """Return kitchen performance comparison metrics for a host."""

    _ensure_host_access(current_user, host_id)
    return await service.get_host_kitchen_comparison(host_id)


@router.get("/platform/overview", response_model=PlatformOverviewMetrics)
async def get_platform_overview(
    current_admin: UserORM = Depends(get_current_admin),
    service: AnalyticsDashboardService = Depends(get_dashboard_service),
) -> PlatformOverviewMetrics:
    """Return platform level executive metrics."""

    _ = current_admin
    return await service.get_platform_overview()


@router.get("/platform/revenue", response_model=RevenueAnalytics)
async def get_platform_revenue(
    timeframe: Timeframe = Query(Timeframe.MONTH),
    current_admin: UserORM = Depends(get_current_admin),
    service: AnalyticsDashboardService = Depends(get_dashboard_service),
) -> RevenueAnalytics:
    """Return platform-wide revenue analytics."""

    _ = current_admin
    return await service.get_platform_revenue(timeframe)


@router.get("/platform/growth", response_model=PlatformGrowthMetrics)
async def get_platform_growth(
    current_admin: UserORM = Depends(get_current_admin),
    service: AnalyticsDashboardService = Depends(get_dashboard_service),
) -> PlatformGrowthMetrics:
    """Return user acquisition and growth metrics."""

    _ = current_admin
    return await service.get_platform_growth()


@router.get("/platform/regions", response_model=list[RegionPerformance])
async def get_platform_regions(
    current_admin: UserORM = Depends(get_current_admin),
    service: AnalyticsDashboardService = Depends(get_dashboard_service),
) -> list[RegionPerformance]:
    """Return geographic performance analytics."""

    _ = current_admin
    return await service.get_platform_regions()


@router.get("/admin/moderation", response_model=ModerationQueueMetrics)
async def get_admin_moderation(
    current_admin: UserORM = Depends(get_current_admin),
    service: AnalyticsDashboardService = Depends(get_dashboard_service),
) -> ModerationQueueMetrics:
    """Return moderation queue metrics for administrators."""

    _ = current_admin
    return await service.get_moderation_metrics()


@router.get("/admin/performance", response_model=AdminPerformanceMetrics)
async def get_admin_performance(
    current_admin: UserORM = Depends(get_current_admin),
    service: AnalyticsDashboardService = Depends(get_dashboard_service),
) -> AdminPerformanceMetrics:
    """Return admin team performance analytics."""

    _ = current_admin
    return await service.get_admin_performance()


@router.get("/admin/financial", response_model=FinancialHealthMetrics)
async def get_admin_financial(
    current_admin: UserORM = Depends(get_current_admin),
    service: AnalyticsDashboardService = Depends(get_dashboard_service),
) -> FinancialHealthMetrics:
    """Return financial health analytics for administrators."""

    _ = current_admin
    return await service.get_financial_health()


__all__ = ["router", "AnalyticsDashboardService", "get_dashboard_service"]

