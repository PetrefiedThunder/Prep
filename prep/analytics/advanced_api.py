"""FastAPI router exposing advanced IoT analytics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from prep.auth import get_current_user
from prep.cache import RedisProtocol, get_redis
from prep.database import get_db
from prep.models.orm import User

from .advanced_models import (
    BehaviorClusterResponse,
    BehaviorPredictRequest,
    BehaviorPredictionResponse,
    BehaviorRetentionResponse,
    BehaviorTrendResponse,
    DemandForecastResponse,
    DemandOptimizationRequest,
    DemandOptimizationResponse,
    DemandTrendResponse,
    EquipmentUtilizationResponse,
    KitchenRevenueComparisonResponse,
    MaintenanceCostForecastResponse,
    MaintenanceHistoryResponse,
    MaintenancePredictionResponse,
    MaintenanceScheduleRequest,
    MaintenanceScheduleResponse,
    PeakUsageResponse,
    RevenueForecastRequest,
    RevenueForecastResponse,
    RevenueOptimizationResponse,
    RevenueTrendResponse,
    SeasonalDemandResponse,
    UsageForecastRequest,
    UsageForecastResponse,
    UsagePatternResponse,
)
from .advanced_service import AdvancedAnalyticsService


router = APIRouter(prefix="/api/v2/analytics", tags=["advanced-analytics"])


async def get_advanced_analytics_service(
    session: AsyncSession = Depends(get_db),
    redis: RedisProtocol = Depends(get_redis),
) -> AdvancedAnalyticsService:
    """Dependency wiring the advanced analytics service."""

    return AdvancedAnalyticsService(session=session, redis=redis)


@router.get("/maintenance/predict", response_model=MaintenancePredictionResponse)
async def predictive_maintenance(
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> MaintenancePredictionResponse:
    return await service.predictive_maintenance()


@router.get("/maintenance/history", response_model=MaintenanceHistoryResponse)
async def maintenance_history(
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> MaintenanceHistoryResponse:
    return await service.maintenance_history()


@router.post("/maintenance/schedule", response_model=MaintenanceScheduleResponse)
async def schedule_maintenance(
    payload: MaintenanceScheduleRequest,
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> MaintenanceScheduleResponse:
    return await service.schedule_maintenance(payload)


@router.get("/maintenance/costs", response_model=MaintenanceCostForecastResponse)
async def maintenance_costs(
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> MaintenanceCostForecastResponse:
    return await service.maintenance_costs()


@router.get("/usage/patterns", response_model=UsagePatternResponse)
async def usage_patterns(
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> UsagePatternResponse:
    return await service.usage_patterns()


@router.get("/usage/peak-times", response_model=PeakUsageResponse)
async def usage_peak_times(
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> PeakUsageResponse:
    return await service.peak_usage()


@router.post("/usage/forecast", response_model=UsageForecastResponse)
async def usage_forecast(
    payload: UsageForecastRequest,
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> UsageForecastResponse:
    return await service.usage_forecast(payload)


@router.get("/usage/equipment", response_model=EquipmentUtilizationResponse)
async def usage_equipment(
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> EquipmentUtilizationResponse:
    return await service.equipment_usage()


@router.get("/revenue/optimize", response_model=RevenueOptimizationResponse)
async def revenue_optimize(
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> RevenueOptimizationResponse:
    return await service.revenue_optimisation()


@router.get("/revenue/trends", response_model=RevenueTrendResponse)
async def revenue_trends(
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> RevenueTrendResponse:
    return await service.revenue_trends()


@router.post("/revenue/forecast", response_model=RevenueForecastResponse)
async def revenue_forecast(
    payload: RevenueForecastRequest,
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> RevenueForecastResponse:
    return await service.revenue_forecast(payload)


@router.get("/revenue/by-kitchen", response_model=KitchenRevenueComparisonResponse)
async def revenue_by_kitchen(
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> KitchenRevenueComparisonResponse:
    return await service.revenue_by_kitchen()


@router.get("/demand/forecast", response_model=DemandForecastResponse)
async def demand_forecast(
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> DemandForecastResponse:
    return await service.demand_forecast()


@router.get("/demand/trends", response_model=DemandTrendResponse)
async def demand_trends(
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> DemandTrendResponse:
    return await service.demand_trends()


@router.post("/demand/optimize", response_model=DemandOptimizationResponse)
async def demand_optimize(
    payload: DemandOptimizationRequest,
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> DemandOptimizationResponse:
    return await service.demand_optimize(payload)


@router.get("/demand/seasonal", response_model=SeasonalDemandResponse)
async def demand_seasonal(
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> SeasonalDemandResponse:
    return await service.demand_seasonal()


@router.get("/behavior/clusters", response_model=BehaviorClusterResponse)
async def behavior_clusters(
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> BehaviorClusterResponse:
    return await service.behavior_clusters()


@router.get("/behavior/trends", response_model=BehaviorTrendResponse)
async def behavior_trends(
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> BehaviorTrendResponse:
    return await service.behavior_trends()


@router.post("/behavior/predict", response_model=BehaviorPredictionResponse)
async def behavior_predict(
    payload: BehaviorPredictRequest,
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> BehaviorPredictionResponse:
    return await service.behavior_predict(payload)


@router.get("/behavior/retention", response_model=BehaviorRetentionResponse)
async def behavior_retention(
    _: User = Depends(get_current_user),
    service: AdvancedAnalyticsService = Depends(get_advanced_analytics_service),
) -> BehaviorRetentionResponse:
    return await service.behavior_retention()


__all__ = ["router", "get_advanced_analytics_service"]
