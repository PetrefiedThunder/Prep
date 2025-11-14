"""Pydantic models for the advanced IoT analytics API surface."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from prep.models.analytics_models import TimeSeriesData


class MaintenanceAlert(BaseModel):
    """Predicted maintenance action for a kitchen."""

    kitchen_id: UUID
    kitchen_name: str
    predicted_issue: str
    severity: str = Field(pattern="^(low|medium|high)$")
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_action: str
    next_service_date: datetime


class MaintenancePredictionResponse(BaseModel):
    """Response envelope with predictive maintenance alerts."""

    generated_at: datetime
    predictions: list[MaintenanceAlert] = Field(default_factory=list)


class MaintenanceHistoryEntry(BaseModel):
    """Historical maintenance record derived from IoT telemetry."""

    kitchen_id: UUID
    kitchen_name: str
    event: str
    occurred_at: datetime
    resolved: bool
    cost: Decimal | None = None


class MaintenanceHistoryResponse(BaseModel):
    """Collection of maintenance history entries."""

    generated_at: datetime
    history: list[MaintenanceHistoryEntry] = Field(default_factory=list)


class MaintenanceScheduleRequest(BaseModel):
    """Request payload for optimising a maintenance window."""

    kitchen_id: UUID
    preferred_window_start: datetime
    preferred_window_end: datetime
    maintenance_tasks: list[str] = Field(default_factory=list)


class MaintenanceScheduleResponse(BaseModel):
    """Optimised maintenance schedule recommendation."""

    kitchen_id: UUID
    scheduled_for: datetime
    tasks: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class MaintenanceCostForecast(BaseModel):
    """Projected maintenance cost for a kitchen."""

    kitchen_id: UUID
    kitchen_name: str
    timeframe: str
    projected_cost: Decimal
    confidence: float = Field(ge=0.0, le=1.0)


class MaintenanceCostForecastResponse(BaseModel):
    """Envelope for maintenance cost forecasts."""

    generated_at: datetime
    forecasts: list[MaintenanceCostForecast] = Field(default_factory=list)


class UsagePattern(BaseModel):
    """Usage pattern summary by day of week."""

    kitchen_id: UUID
    kitchen_name: str
    day_of_week: str
    average_active_hours: float
    utilization_rate: float
    confidence: float = Field(ge=0.0, le=1.0)


class UsagePatternResponse(BaseModel):
    """Envelope for usage pattern insights."""

    generated_at: datetime
    patterns: list[UsagePattern] = Field(default_factory=list)


class PeakUsageWindow(BaseModel):
    """Identified peak usage window within the day."""

    kitchen_id: UUID
    kitchen_name: str
    start_hour: int = Field(ge=0, le=23)
    end_hour: int = Field(ge=1, le=24)
    usage_index: float = Field(ge=0.0)
    confidence: float = Field(ge=0.0, le=1.0)


class PeakUsageResponse(BaseModel):
    """Peak usage analysis payload."""

    generated_at: datetime
    peaks: list[PeakUsageWindow] = Field(default_factory=list)


class UsageForecastRequest(BaseModel):
    """Request payload for usage demand forecasting."""

    kitchen_id: UUID
    horizon_days: int = Field(ge=1, le=30)


class UsageForecastPoint(BaseModel):
    """Projected active hours for a future day."""

    date: date
    projected_hours: float
    confidence: float = Field(ge=0.0, le=1.0)


class UsageForecastResponse(BaseModel):
    """Usage forecast time series."""

    kitchen_id: UUID
    generated_at: datetime
    horizon_days: int
    forecast: list[UsageForecastPoint] = Field(default_factory=list)


class EquipmentUtilization(BaseModel):
    """Utilisation metrics for a category of kitchen equipment."""

    kitchen_id: UUID
    equipment_type: str
    utilization_rate: float
    downtime_rate: float
    confidence: float = Field(ge=0.0, le=1.0)


class EquipmentUtilizationResponse(BaseModel):
    """Equipment utilisation response payload."""

    generated_at: datetime
    equipment: list[EquipmentUtilization] = Field(default_factory=list)


class RevenueOptimizationRecommendation(BaseModel):
    """Revenue optimisation recommendation for a kitchen."""

    kitchen_id: UUID
    kitchen_name: str
    recommendation: str
    projected_lift: float
    confidence: float = Field(ge=0.0, le=1.0)


class RevenueOptimizationResponse(BaseModel):
    """Response payload with revenue optimisation guidance."""

    generated_at: datetime
    recommendations: list[RevenueOptimizationRecommendation] = Field(default_factory=list)


class RevenueTrendResponse(BaseModel):
    """Revenue trend analysis."""

    generated_at: datetime
    trends: list[TimeSeriesData] = Field(default_factory=list)
    growth_rate: float
    confidence: float = Field(ge=0.0, le=1.0)


class RevenueForecastRequest(BaseModel):
    """Request payload for revenue forecasting."""

    horizon_months: int = Field(ge=1, le=12)


class RevenueForecastPoint(BaseModel):
    """Projected revenue for a future month."""

    period: date
    projected_revenue: Decimal
    confidence: float = Field(ge=0.0, le=1.0)


class RevenueForecastResponse(BaseModel):
    """Revenue forecast response payload."""

    generated_at: datetime
    horizon_months: int
    forecast: list[RevenueForecastPoint] = Field(default_factory=list)


class KitchenRevenueComparison(BaseModel):
    """Revenue comparison across kitchens."""

    kitchen_id: UUID
    kitchen_name: str
    total_revenue: Decimal
    average_booking_value: Decimal
    confidence: float = Field(ge=0.0, le=1.0)


class KitchenRevenueComparisonResponse(BaseModel):
    """Response payload comparing kitchen revenue."""

    generated_at: datetime
    kitchens: list[KitchenRevenueComparison] = Field(default_factory=list)


class DemandForecastResponse(BaseModel):
    """Market demand forecast."""

    generated_at: datetime
    forecast: list[TimeSeriesData] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class DemandTrend(BaseModel):
    """Trend insight for a region or segment."""

    region: str
    demand_index: float
    change_rate: float
    confidence: float = Field(ge=0.0, le=1.0)


class DemandTrendResponse(BaseModel):
    """Demand trend analysis response."""

    generated_at: datetime
    trends: list[DemandTrend] = Field(default_factory=list)


class DemandOptimizationRequest(BaseModel):
    """Request payload for demand optimisation strategies."""

    regions: list[str] = Field(default_factory=list)
    horizon_weeks: int = Field(ge=1, le=12)


class DemandStrategy(BaseModel):
    """Recommended strategy to optimise demand."""

    region: str
    strategy: str
    expected_impact: float
    confidence: float = Field(ge=0.0, le=1.0)


class DemandOptimizationResponse(BaseModel):
    """Response payload with demand optimisation guidance."""

    generated_at: datetime
    strategies: list[DemandStrategy] = Field(default_factory=list)


class SeasonalDemandPoint(BaseModel):
    """Seasonal demand insight."""

    season: str
    demand_index: float
    confidence: float = Field(ge=0.0, le=1.0)


class SeasonalDemandResponse(BaseModel):
    """Response describing seasonal demand patterns."""

    generated_at: datetime
    seasonal: list[SeasonalDemandPoint] = Field(default_factory=list)


class BehaviorCluster(BaseModel):
    """Cluster of users exhibiting similar behaviour."""

    label: str
    user_count: int
    characteristics: list[str] = Field(default_factory=list)
    retention_score: float
    confidence: float = Field(ge=0.0, le=1.0)


class BehaviorClusterResponse(BaseModel):
    """Response payload with user behaviour clusters."""

    generated_at: datetime
    clusters: list[BehaviorCluster] = Field(default_factory=list)


class BehaviorTrend(BaseModel):
    """Trend metric describing user behaviour shifts."""

    metric: str
    change_rate: float
    confidence: float = Field(ge=0.0, le=1.0)


class BehaviorTrendResponse(BaseModel):
    """Behaviour trend analysis response."""

    generated_at: datetime
    trends: list[BehaviorTrend] = Field(default_factory=list)


class BehaviorPredictRequest(BaseModel):
    """Request payload for predicting individual user behaviour."""

    user_id: UUID
    kitchen_id: UUID | None = None


class BehaviorPrediction(BaseModel):
    """Predicted behaviour metrics for a user."""

    user_id: UUID
    retention_probability: float = Field(ge=0.0, le=1.0)
    churn_risk: float = Field(ge=0.0, le=1.0)
    projected_ltv: Decimal
    confidence: float = Field(ge=0.0, le=1.0)


class BehaviorPredictionResponse(BaseModel):
    """Response payload with behaviour prediction for a single user."""

    generated_at: datetime
    prediction: BehaviorPrediction


class BehaviorRetentionCohort(BaseModel):
    """Retention metrics for a cohort."""

    cohort: str
    retention_rate: float
    confidence: float = Field(ge=0.0, le=1.0)


class BehaviorRetentionResponse(BaseModel):
    """Response payload summarising retention performance."""

    generated_at: datetime
    overall_retention_rate: float
    confidence: float = Field(ge=0.0, le=1.0)
    cohorts: list[BehaviorRetentionCohort] = Field(default_factory=list)


__all__ = [
    "MaintenanceAlert",
    "MaintenancePredictionResponse",
    "MaintenanceHistoryEntry",
    "MaintenanceHistoryResponse",
    "MaintenanceScheduleRequest",
    "MaintenanceScheduleResponse",
    "MaintenanceCostForecast",
    "MaintenanceCostForecastResponse",
    "UsagePattern",
    "UsagePatternResponse",
    "PeakUsageWindow",
    "PeakUsageResponse",
    "UsageForecastRequest",
    "UsageForecastPoint",
    "UsageForecastResponse",
    "EquipmentUtilization",
    "EquipmentUtilizationResponse",
    "RevenueOptimizationRecommendation",
    "RevenueOptimizationResponse",
    "RevenueTrendResponse",
    "RevenueForecastRequest",
    "RevenueForecastPoint",
    "RevenueForecastResponse",
    "KitchenRevenueComparison",
    "KitchenRevenueComparisonResponse",
    "DemandForecastResponse",
    "DemandTrend",
    "DemandTrendResponse",
    "DemandOptimizationRequest",
    "DemandStrategy",
    "DemandOptimizationResponse",
    "SeasonalDemandPoint",
    "SeasonalDemandResponse",
    "BehaviorCluster",
    "BehaviorClusterResponse",
    "BehaviorTrend",
    "BehaviorTrendResponse",
    "BehaviorPredictRequest",
    "BehaviorPrediction",
    "BehaviorPredictionResponse",
    "BehaviorRetentionCohort",
    "BehaviorRetentionResponse",
]
