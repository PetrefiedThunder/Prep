"""Service layer implementing advanced IoT analytics features."""

from __future__ import annotations

import contextlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from statistics import mean
from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.cache import RedisProtocol
from prep.models.analytics_models import TimeSeriesData
from prep.models.orm import Booking, BookingStatus, Kitchen, Review

from .advanced_models import (
    BehaviorCluster,
    BehaviorClusterResponse,
    BehaviorPrediction,
    BehaviorPredictionResponse,
    BehaviorPredictRequest,
    BehaviorRetentionCohort,
    BehaviorRetentionResponse,
    BehaviorTrend,
    BehaviorTrendResponse,
    DemandForecastResponse,
    DemandOptimizationRequest,
    DemandOptimizationResponse,
    DemandStrategy,
    DemandTrend,
    DemandTrendResponse,
    EquipmentUtilization,
    EquipmentUtilizationResponse,
    KitchenRevenueComparison,
    KitchenRevenueComparisonResponse,
    MaintenanceAlert,
    MaintenanceCostForecast,
    MaintenanceCostForecastResponse,
    MaintenanceHistoryEntry,
    MaintenanceHistoryResponse,
    MaintenancePredictionResponse,
    MaintenanceScheduleRequest,
    MaintenanceScheduleResponse,
    PeakUsageResponse,
    PeakUsageWindow,
    RevenueForecastPoint,
    RevenueForecastRequest,
    RevenueForecastResponse,
    RevenueOptimizationRecommendation,
    RevenueOptimizationResponse,
    RevenueTrendResponse,
    SeasonalDemandPoint,
    SeasonalDemandResponse,
    UsageForecastPoint,
    UsageForecastRequest,
    UsageForecastResponse,
    UsagePattern,
    UsagePatternResponse,
)


@dataclass(slots=True)
class _KitchenSnapshot:
    """Pre-computed metrics for a kitchen used across analytics queries."""

    kitchen: Kitchen
    bookings: list[Booking]
    reviews: list[Review]
    usage_events: list[dict[str, Any]]
    last_heartbeat: datetime | None

    @property
    def total_revenue(self) -> Decimal:
        return sum((Decimal(str(b.total_amount or 0)) for b in self.bookings), Decimal())

    @property
    def completed_bookings(self) -> list[Booking]:
        return [b for b in self.bookings if b.status == BookingStatus.COMPLETED]

    @property
    def confirmed_bookings(self) -> list[Booking]:
        return [
            b
            for b in self.bookings
            if b.status in {BookingStatus.CONFIRMED, BookingStatus.COMPLETED}
        ]

    @property
    def total_active_hours(self) -> float:
        def _duration_hours(booking: Booking) -> float:
            delta = booking.end_time - booking.start_time
            return max(delta.total_seconds() / 3600, 0)

        return sum(_duration_hours(booking) for booking in self.confirmed_bookings)

    @property
    def average_rating(self) -> float:
        ratings = [review.rating for review in self.reviews if review.rating]
        return float(mean(ratings)) if ratings else 0.0


class AdvancedAnalyticsService:
    """Provides advanced analytics aggregations for IoT data."""

    CACHE_TTL_SECONDS = 120
    NOTIFICATION_KEY = "advanced_analytics:notifications"
    NOTIFICATION_TTL = 600

    def __init__(self, session: AsyncSession, redis: RedisProtocol) -> None:
        self._session = session
        self._redis = redis

    # ------------------------------------------------------------------
    # Public API – Predictive maintenance
    # ------------------------------------------------------------------
    async def predictive_maintenance(self) -> MaintenancePredictionResponse:
        snapshots = await self._load_snapshots()
        cache_key = "advanced_analytics:maintenance_predict"
        cached = await self._read_cached(cache_key, MaintenancePredictionResponse)
        if cached:
            return cached

        now = datetime.now(UTC)
        predictions: list[MaintenanceAlert] = []
        for snapshot in snapshots:
            wear_factor = self._compute_wear_factor(snapshot)
            recent_events = self._recent_usage_events(snapshot.usage_events, hours=48)
            severity = "low"
            if wear_factor > 0.7 or recent_events >= 5:
                severity = "high"
            elif wear_factor > 0.4 or recent_events >= 3:
                severity = "medium"

            confidence = min(0.95, 0.4 + wear_factor * 0.5 + min(recent_events, 5) * 0.05)
            next_service_days = max(1, int(21 - wear_factor * 10 - recent_events))
            next_service_date = now + timedelta(days=next_service_days)
            predicted_issue = "Camera recalibration"
            if snapshot.last_heartbeat and (now - snapshot.last_heartbeat).total_seconds() > 3600:
                predicted_issue = "Device heartbeat loss"
                severity = "high"
                confidence = max(confidence, 0.85)

            predictions.append(
                MaintenanceAlert(
                    kitchen_id=snapshot.kitchen.id,
                    kitchen_name=snapshot.kitchen.name,
                    predicted_issue=predicted_issue,
                    severity=severity,
                    confidence=round(confidence, 3),
                    recommended_action=(
                        "Schedule technician visit"
                        if severity == "high"
                        else "Run remote diagnostics"
                    ),
                    next_service_date=next_service_date,
                )
            )

            if severity == "high":
                await self._notify(
                    {
                        "type": "maintenance_alert",
                        "kitchen_id": str(snapshot.kitchen.id),
                        "severity": severity,
                        "issue": predicted_issue,
                        "generated_at": now.isoformat(),
                    }
                )

        response = MaintenancePredictionResponse(generated_at=now, predictions=predictions)
        await self._persist_cache(cache_key, response)
        return response

    async def maintenance_history(self) -> MaintenanceHistoryResponse:
        snapshots = await self._load_snapshots()
        cache_key = "advanced_analytics:maintenance_history"
        cached = await self._read_cached(cache_key, MaintenanceHistoryResponse)
        if cached:
            return cached

        now = datetime.now(UTC)
        history: list[MaintenanceHistoryEntry] = []
        for snapshot in snapshots:
            for event in sorted(
                snapshot.usage_events,
                key=lambda e: e.get("recorded_at", now.isoformat()),
                reverse=True,
            )[:10]:
                recorded_at = self._parse_datetime(event.get("recorded_at")) or now
                description = event.get("event_type", "usage")
                cost = Decimal(str(event.get("metadata", {}).get("cost", 0)))
                resolved = event.get("metadata", {}).get("resolved", True)
                history.append(
                    MaintenanceHistoryEntry(
                        kitchen_id=snapshot.kitchen.id,
                        kitchen_name=snapshot.kitchen.name,
                        event=f"{description.title()} review",
                        occurred_at=recorded_at,
                        resolved=bool(resolved),
                        cost=cost if cost else None,
                    )
                )

        response = MaintenanceHistoryResponse(
            generated_at=now, history=sorted(history, key=lambda h: h.occurred_at, reverse=True)
        )
        await self._persist_cache(cache_key, response)
        return response

    async def schedule_maintenance(
        self, payload: MaintenanceScheduleRequest
    ) -> MaintenanceScheduleResponse:
        snapshots = await self._load_snapshots()
        snapshot = next((snap for snap in snapshots if snap.kitchen.id == payload.kitchen_id), None)
        now = datetime.now(UTC)
        if snapshot is None:
            return MaintenanceScheduleResponse(
                kitchen_id=payload.kitchen_id,
                scheduled_for=payload.preferred_window_start,
                tasks=payload.maintenance_tasks,
                confidence=0.4,
            )

        window_hours = max(
            (payload.preferred_window_end - payload.preferred_window_start).total_seconds() / 3600,
            1,
        )
        wear_factor = self._compute_wear_factor(snapshot)
        optimal_offset = min(window_hours / 2, 6)
        scheduled_for = payload.preferred_window_start + timedelta(hours=optimal_offset)
        if payload.preferred_window_start < now:
            scheduled_for = now + timedelta(hours=4)
        confidence = max(0.5, min(0.95, 0.6 + wear_factor * 0.3))

        await self._notify(
            {
                "type": "maintenance_schedule",
                "kitchen_id": str(payload.kitchen_id),
                "scheduled_for": scheduled_for.isoformat(),
            }
        )

        return MaintenanceScheduleResponse(
            kitchen_id=payload.kitchen_id,
            scheduled_for=scheduled_for,
            tasks=payload.maintenance_tasks or ["Inspection", "Calibration"],
            confidence=round(confidence, 3),
        )

    async def maintenance_costs(self) -> MaintenanceCostForecastResponse:
        snapshots = await self._load_snapshots()
        cache_key = "advanced_analytics:maintenance_costs"
        cached = await self._read_cached(cache_key, MaintenanceCostForecastResponse)
        if cached:
            return cached

        now = datetime.now(UTC)
        forecasts: list[MaintenanceCostForecast] = []
        for snapshot in snapshots:
            utilisation = snapshot.total_active_hours
            usage_events = len(snapshot.usage_events)
            base_cost = Decimal("150")
            variable_cost = Decimal(str(utilisation * 5 + usage_events * 10))
            projected = base_cost + variable_cost
            confidence = min(0.95, 0.5 + (utilisation / 100) + (usage_events * 0.02))
            forecasts.append(
                MaintenanceCostForecast(
                    kitchen_id=snapshot.kitchen.id,
                    kitchen_name=snapshot.kitchen.name,
                    timeframe="30_days",
                    projected_cost=projected.quantize(Decimal("0.01")),
                    confidence=round(confidence, 3),
                )
            )

        response = MaintenanceCostForecastResponse(generated_at=now, forecasts=forecasts)
        await self._persist_cache(cache_key, response)
        return response

    # ------------------------------------------------------------------
    # Public API – Usage patterns
    # ------------------------------------------------------------------
    async def usage_patterns(self) -> UsagePatternResponse:
        snapshots = await self._load_snapshots()
        cache_key = "advanced_analytics:usage_patterns"
        cached = await self._read_cached(cache_key, UsagePatternResponse)
        if cached:
            return cached

        now = datetime.now(UTC)
        patterns: list[UsagePattern] = []
        for snapshot in snapshots:
            bookings_by_day: dict[int, list[Booking]] = defaultdict(list)
            for booking in snapshot.confirmed_bookings:
                bookings_by_day[booking.start_time.weekday()].append(booking)

            for weekday, bookings in bookings_by_day.items():
                hours = sum(
                    (booking.end_time - booking.start_time).total_seconds() / 3600
                    for booking in bookings
                )
                utilisation = min(1.0, hours / 12)
                confidence = min(0.95, 0.5 + len(bookings) * 0.05)
                patterns.append(
                    UsagePattern(
                        kitchen_id=snapshot.kitchen.id,
                        kitchen_name=snapshot.kitchen.name,
                        day_of_week=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][weekday],
                        average_active_hours=round(hours / max(len(bookings), 1), 2),
                        utilization_rate=round(utilisation, 3),
                        confidence=round(confidence, 3),
                    )
                )

        response = UsagePatternResponse(generated_at=now, patterns=patterns)
        await self._persist_cache(cache_key, response)
        return response

    async def peak_usage(self) -> PeakUsageResponse:
        snapshots = await self._load_snapshots()
        cache_key = "advanced_analytics:usage_peaks"
        cached = await self._read_cached(cache_key, PeakUsageResponse)
        if cached:
            return cached

        now = datetime.now(UTC)
        peaks: list[PeakUsageWindow] = []
        for snapshot in snapshots:
            hours_counter: Counter[int] = Counter()
            for booking in snapshot.confirmed_bookings:
                start_hour = booking.start_time.hour
                end_hour = booking.end_time.hour or start_hour
                for hour in range(start_hour, min(end_hour + 1, 24)):
                    hours_counter[hour] += 1
            if not hours_counter:
                continue
            best_hour, usage_index = hours_counter.most_common(1)[0]
            peaks.append(
                PeakUsageWindow(
                    kitchen_id=snapshot.kitchen.id,
                    kitchen_name=snapshot.kitchen.name,
                    start_hour=best_hour,
                    end_hour=min(best_hour + 2, 24),
                    usage_index=float(usage_index),
                    confidence=min(0.95, 0.6 + usage_index * 0.05),
                )
            )

        response = PeakUsageResponse(generated_at=now, peaks=peaks)
        await self._persist_cache(cache_key, response)
        return response

    async def usage_forecast(self, payload: UsageForecastRequest) -> UsageForecastResponse:
        snapshots = await self._load_snapshots()
        snapshot = next((snap for snap in snapshots if snap.kitchen.id == payload.kitchen_id), None)
        now = datetime.now(UTC)
        if snapshot is None:
            return UsageForecastResponse(
                kitchen_id=payload.kitchen_id,
                generated_at=now,
                horizon_days=payload.horizon_days,
                forecast=[],
            )

        historical: list[tuple[date, float]] = []
        for booking in snapshot.confirmed_bookings:
            booking_date = booking.start_time.date()
            duration_hours = max((booking.end_time - booking.start_time).total_seconds() / 3600, 0)
            historical.append((booking_date, duration_hours))

        averages: dict[date, list[float]] = defaultdict(list)
        for booking_date, duration in historical:
            averages[booking_date].append(duration)

        if not averages:
            baseline = 2.0
        else:
            baseline = sum(map(mean, averages.values())) / max(len(averages), 1)

        forecast: list[UsageForecastPoint] = []
        for offset in range(1, payload.horizon_days + 1):
            target_date = now.date() + timedelta(days=offset)
            seasonal_factor = 1.1 if target_date.weekday() in {4, 5} else 0.9
            projected = max(baseline * seasonal_factor, 0.5)
            confidence = min(0.95, 0.6 + len(historical) * 0.02)
            forecast.append(
                UsageForecastPoint(
                    date=target_date,
                    projected_hours=round(projected, 2),
                    confidence=round(confidence, 3),
                )
            )

        return UsageForecastResponse(
            kitchen_id=snapshot.kitchen.id,
            generated_at=now,
            horizon_days=payload.horizon_days,
            forecast=forecast,
        )

    async def equipment_usage(self) -> EquipmentUtilizationResponse:
        snapshots = await self._load_snapshots()
        cache_key = "advanced_analytics:usage_equipment"
        cached = await self._read_cached(cache_key, EquipmentUtilizationResponse)
        if cached:
            return cached

        now = datetime.now(UTC)
        equipment: list[EquipmentUtilization] = []
        for snapshot in snapshots:
            equipment_events: Counter[str] = Counter()
            for event in snapshot.usage_events:
                equipment_type = event.get("metadata", {}).get("equipment", "general")
                equipment_events[equipment_type] += 1
            total = sum(equipment_events.values()) or 1
            for equipment_type, count in equipment_events.items():
                utilisation = min(1.0, count / total)
                downtime = max(0.0, 1.0 - utilisation * 0.8)
                confidence = min(0.95, 0.5 + count * 0.05)
                equipment.append(
                    EquipmentUtilization(
                        kitchen_id=snapshot.kitchen.id,
                        equipment_type=equipment_type,
                        utilization_rate=round(utilisation, 3),
                        downtime_rate=round(downtime, 3),
                        confidence=round(confidence, 3),
                    )
                )

        response = EquipmentUtilizationResponse(generated_at=now, equipment=equipment)
        await self._persist_cache(cache_key, response)
        return response

    # ------------------------------------------------------------------
    # Public API – Revenue
    # ------------------------------------------------------------------
    async def revenue_optimisation(self) -> RevenueOptimizationResponse:
        snapshots = await self._load_snapshots()
        cache_key = "advanced_analytics:revenue_optimize"
        cached = await self._read_cached(cache_key, RevenueOptimizationResponse)
        if cached:
            return cached

        now = datetime.now(UTC)
        recommendations: list[RevenueOptimizationRecommendation] = []
        for snapshot in snapshots:
            avg_value = (
                snapshot.total_revenue / Decimal(len(snapshot.confirmed_bookings))
                if snapshot.confirmed_bookings
                else Decimal("0")
            )
            lift = float(min(0.35, 0.1 + snapshot.average_rating * 0.02))
            recommendation = "Introduce peak-hour premium"
            if avg_value and avg_value < Decimal("250"):
                recommendation = "Bundle equipment upsells"
            recommendations.append(
                RevenueOptimizationRecommendation(
                    kitchen_id=snapshot.kitchen.id,
                    kitchen_name=snapshot.kitchen.name,
                    recommendation=recommendation,
                    projected_lift=round(lift, 3),
                    confidence=round(min(0.95, 0.6 + lift), 3),
                )
            )

        response = RevenueOptimizationResponse(generated_at=now, recommendations=recommendations)
        await self._persist_cache(cache_key, response)
        return response

    async def revenue_trends(self) -> RevenueTrendResponse:
        snapshots = await self._load_snapshots()
        cache_key = "advanced_analytics:revenue_trends"
        cached = await self._read_cached(cache_key, RevenueTrendResponse)
        if cached:
            return cached

        now = datetime.now(UTC)
        weekly_totals: defaultdict[date, Decimal] = defaultdict(Decimal)
        for snapshot in snapshots:
            for booking in snapshot.confirmed_bookings:
                week_start = booking.start_time.date() - timedelta(
                    days=booking.start_time.weekday()
                )
                weekly_totals[week_start] += Decimal(str(booking.total_amount or 0))

        trends = [
            TimeSeriesData(date=week, value=total.quantize(Decimal("0.01")))
            for week, total in sorted(weekly_totals.items())
        ]
        growth_rate = self._calculate_growth_rate(trends)
        confidence = min(0.95, 0.5 + len(trends) * 0.05)

        response = RevenueTrendResponse(
            generated_at=now,
            trends=trends,
            growth_rate=round(growth_rate, 3),
            confidence=round(confidence, 3),
        )
        await self._persist_cache(cache_key, response)
        return response

    async def revenue_forecast(self, payload: RevenueForecastRequest) -> RevenueForecastResponse:
        snapshots = await self._load_snapshots()
        now = datetime.now(UTC)

        monthly_totals: defaultdict[tuple[int, int], Decimal] = defaultdict(Decimal)
        for snapshot in snapshots:
            for booking in snapshot.confirmed_bookings:
                period_key = (booking.start_time.year, booking.start_time.month)
                monthly_totals[period_key] += Decimal(str(booking.total_amount or 0))

        if monthly_totals:
            baseline = sum(monthly_totals.values()) / Decimal(len(monthly_totals))
        else:
            baseline = Decimal("15000")

        forecast: list[RevenueForecastPoint] = []
        period = date(year=now.year, month=now.month, day=1)
        for offset in range(1, payload.horizon_months + 1):
            month = (period.month - 1 + offset) % 12 + 1
            year = period.year + (period.month - 1 + offset) // 12
            projection_date = date(year=year, month=month, day=1)
            seasonal = Decimal("1.1") if month in {5, 6, 11} else Decimal("0.95")
            projected = (baseline * seasonal).quantize(Decimal("0.01"))
            confidence = min(0.95, 0.6 + len(monthly_totals) * 0.03)
            forecast.append(
                RevenueForecastPoint(
                    period=projection_date,
                    projected_revenue=projected,
                    confidence=round(confidence, 3),
                )
            )

        return RevenueForecastResponse(
            generated_at=now,
            horizon_months=payload.horizon_months,
            forecast=forecast,
        )

    async def revenue_by_kitchen(self) -> KitchenRevenueComparisonResponse:
        snapshots = await self._load_snapshots()
        cache_key = "advanced_analytics:revenue_by_kitchen"
        cached = await self._read_cached(cache_key, KitchenRevenueComparisonResponse)
        if cached:
            return cached

        now = datetime.now(UTC)
        kitchens: list[KitchenRevenueComparison] = []
        for snapshot in snapshots:
            bookings = snapshot.confirmed_bookings
            total_revenue = snapshot.total_revenue
            average_value = (
                total_revenue / Decimal(len(bookings)) if bookings else Decimal("0")
            ).quantize(Decimal("0.01"))
            confidence = min(0.95, 0.6 + len(bookings) * 0.03)
            kitchens.append(
                KitchenRevenueComparison(
                    kitchen_id=snapshot.kitchen.id,
                    kitchen_name=snapshot.kitchen.name,
                    total_revenue=total_revenue.quantize(Decimal("0.01")),
                    average_booking_value=average_value,
                    confidence=round(confidence, 3),
                )
            )

        response = KitchenRevenueComparisonResponse(
            generated_at=now,
            kitchens=sorted(kitchens, key=lambda item: item.total_revenue, reverse=True),
        )
        await self._persist_cache(cache_key, response)
        return response

    # ------------------------------------------------------------------
    # Public API – Demand
    # ------------------------------------------------------------------
    async def demand_forecast(self) -> DemandForecastResponse:
        snapshots = await self._load_snapshots()
        cache_key = "advanced_analytics:demand_forecast"
        cached = await self._read_cached(cache_key, DemandForecastResponse)
        if cached:
            return cached

        now = datetime.now(UTC)
        monthly_demand: defaultdict[date, int] = defaultdict(int)
        for snapshot in snapshots:
            for booking in snapshot.confirmed_bookings:
                month_start = booking.start_time.date().replace(day=1)
                monthly_demand[month_start] += 1

        trends = [
            TimeSeriesData(date=month, value=count)
            for month, count in sorted(monthly_demand.items())
        ]
        confidence = min(0.95, 0.5 + len(trends) * 0.04)
        response = DemandForecastResponse(
            generated_at=now,
            forecast=trends,
            confidence=round(confidence, 3),
        )
        await self._persist_cache(cache_key, response)
        return response

    async def demand_trends(self) -> DemandTrendResponse:
        snapshots = await self._load_snapshots()
        cache_key = "advanced_analytics:demand_trends"
        cached = await self._read_cached(cache_key, DemandTrendResponse)
        if cached:
            return cached

        now = datetime.now(UTC)
        region_counts: defaultdict[str, int] = defaultdict(int)
        for snapshot in snapshots:
            region = f"{snapshot.kitchen.city or 'Unknown'}, {snapshot.kitchen.state or 'N/A'}"
            region_counts[region] += len(snapshot.confirmed_bookings)

        trends = [
            DemandTrend(
                region=region,
                demand_index=float(count),
                change_rate=round(0.05 + min(count, 50) * 0.01, 3),
                confidence=round(min(0.95, 0.5 + count * 0.02), 3),
            )
            for region, count in region_counts.items()
        ]

        response = DemandTrendResponse(generated_at=now, trends=trends)
        await self._persist_cache(cache_key, response)
        return response

    async def demand_optimize(
        self, payload: DemandOptimizationRequest
    ) -> DemandOptimizationResponse:
        snapshots = await self._load_snapshots()
        now = datetime.now(UTC)
        strategies: list[DemandStrategy] = []
        regions = payload.regions or list(
            {
                f"{snapshot.kitchen.city or 'Unknown'}, {snapshot.kitchen.state or 'N/A'}"
                for snapshot in snapshots
            }
        )

        for region in regions:
            intensity = 0
            for snapshot in snapshots:
                kitchen_region = (
                    f"{snapshot.kitchen.city or 'Unknown'}, {snapshot.kitchen.state or 'N/A'}"
                )
                if kitchen_region == region:
                    intensity += len(snapshot.confirmed_bookings)
            confidence = min(0.95, 0.5 + intensity * 0.02)
            strategies.append(
                DemandStrategy(
                    region=region,
                    strategy="Launch targeted promotions"
                    if intensity < 10
                    else "Introduce tiered pricing",
                    expected_impact=round(min(0.5, 0.1 + intensity * 0.01), 3),
                    confidence=round(confidence, 3),
                )
            )

        return DemandOptimizationResponse(generated_at=now, strategies=strategies)

    async def demand_seasonal(self) -> SeasonalDemandResponse:
        snapshots = await self._load_snapshots()
        cache_key = "advanced_analytics:demand_seasonal"
        cached = await self._read_cached(cache_key, SeasonalDemandResponse)
        if cached:
            return cached

        now = datetime.now(UTC)
        season_map = {
            0: "Winter",
            1: "Spring",
            2: "Summer",
            3: "Autumn",
        }
        counts = defaultdict(int)
        for snapshot in snapshots:
            for booking in snapshot.confirmed_bookings:
                season_index = (booking.start_time.month % 12) // 3
                counts[season_map[season_index]] += 1

        seasonal = [
            SeasonalDemandPoint(
                season=season,
                demand_index=float(count),
                confidence=round(min(0.95, 0.5 + count * 0.03), 3),
            )
            for season, count in counts.items()
        ]

        response = SeasonalDemandResponse(generated_at=now, seasonal=seasonal)
        await self._persist_cache(cache_key, response)
        return response

    # ------------------------------------------------------------------
    # Public API – Behaviour
    # ------------------------------------------------------------------
    async def behavior_clusters(self) -> BehaviorClusterResponse:
        snapshots = await self._load_snapshots()
        cache_key = "advanced_analytics:behavior_clusters"
        cached = await self._read_cached(cache_key, BehaviorClusterResponse)
        if cached:
            return cached

        now = datetime.now(UTC)
        user_booking_counts: Counter[UUID] = Counter()
        for snapshot in snapshots:
            for booking in snapshot.bookings:
                user_booking_counts[booking.customer_id] += 1

        clusters: list[BehaviorCluster] = []
        if user_booking_counts:
            low = [count for count in user_booking_counts.values() if count <= 2]
            medium = [count for count in user_booking_counts.values() if 2 < count <= 5]
            high = [count for count in user_booking_counts.values() if count > 5]

            if low:
                clusters.append(
                    BehaviorCluster(
                        label="New Guests",
                        user_count=len(low),
                        characteristics=["Occasional bookings", "High churn risk"],
                        retention_score=0.35,
                        confidence=round(min(0.95, 0.6 + len(low) * 0.03), 3),
                    )
                )
            if medium:
                clusters.append(
                    BehaviorCluster(
                        label="Growing Teams",
                        user_count=len(medium),
                        characteristics=["Consistent bookings", "Responsive to promotions"],
                        retention_score=0.62,
                        confidence=round(min(0.95, 0.6 + len(medium) * 0.03), 3),
                    )
                )
            if high:
                clusters.append(
                    BehaviorCluster(
                        label="Power Users",
                        user_count=len(high),
                        characteristics=["High utilisation", "Cross-city expansion"],
                        retention_score=0.82,
                        confidence=round(min(0.95, 0.6 + len(high) * 0.03), 3),
                    )
                )

        response = BehaviorClusterResponse(generated_at=now, clusters=clusters)
        await self._persist_cache(cache_key, response)
        return response

    async def behavior_trends(self) -> BehaviorTrendResponse:
        snapshots = await self._load_snapshots()
        cache_key = "advanced_analytics:behavior_trends"
        cached = await self._read_cached(cache_key, BehaviorTrendResponse)
        if cached:
            return cached

        now = datetime.now(UTC)
        total_bookings = sum(len(snapshot.bookings) for snapshot in snapshots)
        repeat_users = 0
        for snapshot in snapshots:
            counts: Counter[UUID] = Counter(booking.customer_id for booking in snapshot.bookings)
            repeat_users += sum(1 for _, value in counts.items() if value > 1)

        trends = [
            BehaviorTrend(
                metric="repeat_users",
                change_rate=round(min(0.5, repeat_users * 0.02), 3),
                confidence=round(min(0.95, 0.6 + total_bookings * 0.01), 3),
            ),
            BehaviorTrend(
                metric="booking_frequency",
                change_rate=round(min(0.5, total_bookings * 0.005), 3),
                confidence=round(min(0.95, 0.6 + total_bookings * 0.008), 3),
            ),
        ]

        response = BehaviorTrendResponse(generated_at=now, trends=trends)
        await self._persist_cache(cache_key, response)
        return response

    async def behavior_predict(self, payload: BehaviorPredictRequest) -> BehaviorPredictionResponse:
        snapshots = await self._load_snapshots()
        now = datetime.now(UTC)

        user_bookings: list[Booking] = []
        user_spend = Decimal("0")
        for snapshot in snapshots:
            for booking in snapshot.bookings:
                if booking.customer_id == payload.user_id:
                    user_bookings.append(booking)
                    user_spend += Decimal(str(booking.total_amount or 0))

        booking_count = len(user_bookings)
        retention_probability = min(0.95, 0.4 + booking_count * 0.1)
        churn_risk = round(max(0.05, 1 - retention_probability), 3)
        projected_ltv = user_spend * Decimal("1.2") if user_spend else Decimal("500")
        confidence = min(0.95, 0.5 + booking_count * 0.05)

        prediction = BehaviorPrediction(
            user_id=payload.user_id,
            retention_probability=round(retention_probability, 3),
            churn_risk=churn_risk,
            projected_ltv=projected_ltv.quantize(Decimal("0.01")),
            confidence=round(confidence, 3),
        )

        if churn_risk > 0.4:
            await self._notify(
                {
                    "type": "behavior_churn_risk",
                    "user_id": str(payload.user_id),
                    "churn_risk": churn_risk,
                    "generated_at": now.isoformat(),
                }
            )

        return BehaviorPredictionResponse(generated_at=now, prediction=prediction)

    async def behavior_retention(self) -> BehaviorRetentionResponse:
        snapshots = await self._load_snapshots()
        cache_key = "advanced_analytics:behavior_retention"
        cached = await self._read_cached(cache_key, BehaviorRetentionResponse)
        if cached:
            return cached

        now = datetime.now(UTC)
        user_counts: Counter[UUID] = Counter()
        for snapshot in snapshots:
            for booking in snapshot.bookings:
                user_counts[booking.customer_id] += 1

        total_users = len(user_counts)
        retained_users = sum(1 for count in user_counts.values() if count > 1)
        overall_retention = (retained_users / total_users) if total_users else 0.0
        cohorts = [
            BehaviorRetentionCohort(
                cohort="New",
                retention_rate=round(min(0.5, total_users * 0.01), 3),
                confidence=round(min(0.95, 0.5 + total_users * 0.02), 3),
            ),
            BehaviorRetentionCohort(
                cohort="Established",
                retention_rate=round(min(0.95, overall_retention + 0.2), 3),
                confidence=round(min(0.95, 0.6 + retained_users * 0.03), 3),
            ),
        ]

        response = BehaviorRetentionResponse(
            generated_at=now,
            overall_retention_rate=round(overall_retention, 3),
            confidence=round(min(0.95, 0.5 + total_users * 0.02), 3),
            cohorts=cohorts,
        )
        await self._persist_cache(cache_key, response)
        return response

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _load_snapshots(self) -> list[_KitchenSnapshot]:
        kitchens = await self._session.execute(self._kitchen_query())
        kitchen_rows = kitchens.scalars().all()
        if not kitchen_rows:
            return []

        kitchen_ids = [kitchen.id for kitchen in kitchen_rows]
        bookings = await self._session.execute(self._booking_query(kitchen_ids))
        booking_rows = list(bookings.scalars().all())
        reviews = await self._session.execute(self._review_query(kitchen_ids))
        review_rows = list(reviews.scalars().all())

        bookings_by_kitchen: defaultdict[UUID, list[Booking]] = defaultdict(list)
        for booking in booking_rows:
            bookings_by_kitchen[booking.kitchen_id].append(booking)

        reviews_by_kitchen: defaultdict[UUID, list[Review]] = defaultdict(list)
        for review in review_rows:
            reviews_by_kitchen[review.kitchen_id].append(review)

        usage_events = await self._load_usage_events(kitchen_ids)
        heartbeats = await self._load_heartbeats(kitchen_ids)

        return [
            _KitchenSnapshot(
                kitchen=kitchen,
                bookings=bookings_by_kitchen.get(kitchen.id, []),
                reviews=reviews_by_kitchen.get(kitchen.id, []),
                usage_events=usage_events.get(kitchen.id, []),
                last_heartbeat=heartbeats.get(kitchen.id),
            )
            for kitchen in kitchen_rows
        ]

    def _kitchen_query(self) -> Select[tuple[Kitchen]]:
        return select(Kitchen)

    def _booking_query(self, kitchen_ids: Iterable[UUID]) -> Select[tuple[Booking]]:
        return select(Booking).where(Booking.kitchen_id.in_(list(kitchen_ids)))

    def _review_query(self, kitchen_ids: Iterable[UUID]) -> Select[tuple[Review]]:
        return select(Review).where(Review.kitchen_id.in_(list(kitchen_ids)))

    async def _load_usage_events(
        self, kitchen_ids: Iterable[UUID]
    ) -> dict[UUID, list[dict[str, Any]]]:
        events: dict[UUID, list[dict[str, Any]]] = {}
        for kitchen_id in kitchen_ids:
            payload = await self._redis.get(f"kitchen_cam:usage:{kitchen_id}")
            if not isinstance(payload, str):
                continue
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                data = []
            parsed: list[dict[str, Any]] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                parsed.append(item)
            events[kitchen_id] = parsed
        return events

    async def _load_heartbeats(self, kitchen_ids: Iterable[UUID]) -> dict[UUID, datetime]:
        heartbeats: dict[UUID, datetime] = {}
        for kitchen_id in kitchen_ids:
            payload = await self._redis.get(f"kitchen_cam:last_heartbeat:{kitchen_id}")
            if not isinstance(payload, str):
                continue
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                data = {}
            last_recorded = self._parse_datetime(data.get("recorded_at"))
            if last_recorded:
                heartbeats[kitchen_id] = last_recorded
        return heartbeats

    async def _read_cached(self, key: str, model_type: type[Any]) -> Any | None:
        payload = await self._redis.get(key)
        if not isinstance(payload, str):
            return None
        try:
            return model_type.model_validate_json(payload)
        except Exception:
            return None

    async def _persist_cache(self, key: str, value: Any) -> None:
        with contextlib.suppress(Exception):
            await self._redis.setex(key, self.CACHE_TTL_SECONDS, value.model_dump_json())

    async def _notify(self, message: dict[str, Any]) -> None:
        try:
            payload = await self._redis.get(self.NOTIFICATION_KEY)
            notifications = json.loads(payload) if isinstance(payload, str) else []
            if not isinstance(notifications, list):
                notifications = []
            notifications.append(message)
            await self._redis.setex(
                self.NOTIFICATION_KEY,
                self.NOTIFICATION_TTL,
                json.dumps(notifications),
            )
        except Exception:
            pass

    def _compute_wear_factor(self, snapshot: _KitchenSnapshot) -> float:
        utilisation = snapshot.total_active_hours / 120  # approx 5 days of 24h usage
        event_pressure = len(snapshot.usage_events) / 10
        rating_modifier = (5 - snapshot.average_rating) * 0.05 if snapshot.average_rating else 0.1
        return min(1.0, max(0.0, utilisation + event_pressure + rating_modifier))

    def _recent_usage_events(self, events: list[dict[str, Any]], *, hours: int) -> int:
        if not events:
            return 0
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        count = 0
        for event in events:
            recorded_at = self._parse_datetime(event.get("recorded_at"))
            if recorded_at and recorded_at >= cutoff:
                count += 1
        return count

    def _parse_datetime(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                return parsed.astimezone(UTC)
            except ValueError:
                return None
        return None

    def _calculate_growth_rate(self, series: list[TimeSeriesData]) -> float:
        if len(series) < 2:
            return 0.0
        first = float(series[0].value)
        last = float(series[-1].value)
        if first == 0:
            return 0.0
        return (last - first) / abs(first)


__all__ = ["AdvancedAnalyticsService"]
