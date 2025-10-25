"""Pydantic schemas supporting the multi-city expansion APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ConfidenceSignal(BaseModel):
    """Represents the confidence level for a computed metric."""

    metric: str
    score: float = Field(ge=0.0, le=1.0)
    description: str


class MarketInsight(BaseModel):
    """Key takeaway surfaced for a city."""

    title: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)


class ExpansionRecommendation(BaseModel):
    """Actionable recommendation for expansion planning."""

    action: str
    impact: str
    priority: Literal["low", "medium", "high"]
    confidence: float = Field(ge=0.0, le=1.0)


class TrendPoint(BaseModel):
    """Aggregated booking trend datapoint."""

    period_start: datetime
    bookings: int
    revenue: float


class CityKitchenHighlight(BaseModel):
    """Summary of a high-performing kitchen within a city."""

    kitchen_id: UUID
    name: str
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    hourly_rate: float | None = None
    converted_hourly_rate: float | None = Field(default=None, description="Rate in the requested currency")
    currency: str = Field(description="Currency code for converted values")
    popularity_index: float | None = Field(default=None, ge=0.0, le=1.0)
    demand_forecast: float | None = Field(default=None, ge=0.0, le=1.0)


class CityMarketMetrics(BaseModel):
    """Aggregate metrics that describe market health."""

    kitchen_count: int
    active_kitchens: int
    average_hourly_rate: float | None
    average_trust_score: float | None
    bookings_last_30_days: int
    revenue_last_30_days: float
    demand_index: float = Field(ge=0.0, le=1.0)


class CityMarketAnalyticsResponse(BaseModel):
    """Response model for the city market analytics endpoint."""

    city: str
    currency: str
    metrics: CityMarketMetrics
    trends: list[TrendPoint]
    top_kitchens: list[CityKitchenHighlight]
    confidence: list[ConfidenceSignal]
    insights: list[MarketInsight]
    recommendations: list[ExpansionRecommendation]


class CompetitorProfile(BaseModel):
    """Represents a competitor within the city."""

    kitchen_id: UUID
    name: str
    hourly_rate: float | None
    converted_hourly_rate: float | None
    occupancy_rate: float | None
    rating: float | None
    confidence: float = Field(ge=0.0, le=1.0)


class CityCompetitionResponse(BaseModel):
    """Response body for city competition analysis."""

    city: str
    currency: str
    competitors: list[CompetitorProfile]
    market_share_estimate: float = Field(ge=0.0, le=1.0)
    confidence: list[ConfidenceSignal]
    insights: list[MarketInsight]
    recommendations: list[ExpansionRecommendation]


class DemandForecastPoint(BaseModel):
    """Future booking forecast datapoint."""

    period_start: datetime
    projected_bookings: float
    projected_revenue: float
    confidence: float = Field(ge=0.0, le=1.0)


class CityDemandForecastResponse(BaseModel):
    """Response for the demand forecasting endpoint."""

    city: str
    currency: str
    demand_index: float = Field(ge=0.0, le=1.0)
    forecast: list[DemandForecastPoint]
    confidence: list[ConfidenceSignal]
    insights: list[MarketInsight]
    recommendations: list[ExpansionRecommendation]


class PricingBand(BaseModel):
    """Represents pricing distribution percentile data."""

    percentile: int
    hourly_rate: float | None
    converted_rate: float | None


class PricingIntelResponse(BaseModel):
    """Response for pricing intelligence endpoint."""

    city: str
    currency: str
    median_hourly_rate: float | None
    average_hourly_rate: float | None
    pricing_bands: list[PricingBand]
    confidence: list[ConfidenceSignal]
    insights: list[MarketInsight]
    recommendations: list[ExpansionRecommendation]


class RegulationItem(BaseModel):
    """Single regulation requirement entry."""

    category: str
    description: str
    due_in_days: int | None = None


class CityRegulationResponse(BaseModel):
    """Describes regulatory requirements for a city."""

    city: str
    requirements: list[RegulationItem]
    confidence: list[ConfidenceSignal]
    insights: list[MarketInsight]
    recommendations: list[ExpansionRecommendation]


class ComplianceCheckRequest(BaseModel):
    """Payload for compliance readiness checks."""

    city: str
    kitchen_id: UUID | None = None
    submitted_documents: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class ComplianceCheckResponse(BaseModel):
    """Result of a compliance readiness check."""

    city: str
    status: Literal["pass", "pending", "fail"]
    missing_requirements: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    insights: list[MarketInsight]
    recommendations: list[ExpansionRecommendation]


class ComplianceTemplate(BaseModel):
    """Document template metadata."""

    city: str
    name: str
    description: str
    url: str


class ComplianceTemplatesResponse(BaseModel):
    """Response containing compliance document templates."""

    templates: list[ComplianceTemplate]
    confidence: list[ConfidenceSignal]
    insights: list[MarketInsight]
    recommendations: list[ExpansionRecommendation]


class CurrencyDescriptor(BaseModel):
    """Details about a supported currency."""

    code: str
    name: str
    symbol: str


class CurrencyListResponse(BaseModel):
    """List of supported currencies."""

    currencies: list[CurrencyDescriptor]
    confidence: list[ConfidenceSignal]


class CurrencyRatesResponse(BaseModel):
    """Exchange rate payload."""

    base_currency: str
    timestamp: datetime
    rates: dict[str, float]


class BookingQuoteRequest(BaseModel):
    """Payload for multi-currency booking quote calculations."""

    kitchen_id: UUID
    hours: float = Field(gt=0)
    currency: str = Field(default="USD")
    include_fees: bool = Field(default=True)


class BookingQuoteResponse(BaseModel):
    """Response for booking quote calculations."""

    kitchen_id: UUID
    hours: float
    base_currency: str
    target_currency: str
    hourly_rate: float | None
    converted_hourly_rate: float | None
    total_cost: float | None
    converted_total_cost: float | None
    fees: float | None
    converted_fees: float | None
    confidence: float = Field(ge=0.0, le=1.0)
    insights: list[MarketInsight]
    recommendations: list[ExpansionRecommendation]


class AddressValidationRequest(BaseModel):
    """Payload for validating addresses within a city."""

    city: str
    address_line: str
    state: str | None = None
    postal_code: str | None = None


class AddressValidationResponse(BaseModel):
    """Result of address validation."""

    city: str
    is_valid: bool
    normalized_address: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    issues: list[str]
    recommendations: list[ExpansionRecommendation]


class ServiceZone(BaseModel):
    """Represents a serviceable zone inside a city."""

    name: str
    coverage: str
    restrictions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class CityServiceZonesResponse(BaseModel):
    """Response for service zone definitions."""

    city: str
    zones: list[ServiceZone]
    insights: list[MarketInsight]
    recommendations: list[ExpansionRecommendation]


class DemographicMetric(BaseModel):
    """Demographic indicator for a city."""

    name: str
    value: float
    unit: str
    confidence: float = Field(ge=0.0, le=1.0)


class CityDemographicsResponse(BaseModel):
    """Response for demographic insights."""

    city: str
    population_estimate: int
    median_income: float | None
    food_business_density: float | None
    metrics: list[DemographicMetric]
    insights: list[MarketInsight]
    recommendations: list[ExpansionRecommendation]


class CityLaunchRequest(BaseModel):
    """Payload to initialize a city launch."""

    target_launch_date: datetime | None = None
    marketing_budget: float | None = None
    lead_owner: str | None = None
    notes: str | None = None


class LaunchStep(BaseModel):
    """Individual launch plan step."""

    name: str
    status: Literal["pending", "in_progress", "completed"]
    owner: str | None = None


class CityLaunchResponse(BaseModel):
    """Launch initialization response."""

    city: str
    launched_at: datetime
    plan: list[LaunchStep]
    confidence: list[ConfidenceSignal]
    insights: list[MarketInsight]
    recommendations: list[ExpansionRecommendation]


class ChecklistItem(BaseModel):
    """Single readiness checklist item."""

    name: str
    status: Literal["complete", "in_progress", "blocked"]
    confidence: float = Field(ge=0.0, le=1.0)


class CityReadinessResponse(BaseModel):
    """Launch readiness checklist response."""

    city: str
    readiness_score: float = Field(ge=0.0, le=1.0)
    checklist: list[ChecklistItem]
    insights: list[MarketInsight]
    recommendations: list[ExpansionRecommendation]


class CityPromotionRequest(BaseModel):
    """Payload describing promotion strategy."""

    channels: list[str] = Field(default_factory=list)
    launch_date: datetime | None = None
    budget: float | None = None


class PromotionCampaign(BaseModel):
    """Marketing campaign suggestion."""

    channel: str
    allocation: float
    kpi: str
    confidence: float = Field(ge=0.0, le=1.0)


class CityPromotionResponse(BaseModel):
    """Response for marketing promotion planning."""

    city: str
    budget: float | None
    campaigns: list[PromotionCampaign]
    insights: list[MarketInsight]
    recommendations: list[ExpansionRecommendation]


__all__ = [
    "AddressValidationRequest",
    "AddressValidationResponse",
    "BookingQuoteRequest",
    "BookingQuoteResponse",
    "ChecklistItem",
    "CityCompetitionResponse",
    "CityDemandForecastResponse",
    "CityDemographicsResponse",
    "CityLaunchRequest",
    "CityLaunchResponse",
    "CityMarketAnalyticsResponse",
    "CityMarketMetrics",
    "CityPromotionRequest",
    "CityPromotionResponse",
    "CityReadinessResponse",
    "CityRegulationResponse",
    "CityServiceZonesResponse",
    "CompetitorProfile",
    "ComplianceCheckRequest",
    "ComplianceCheckResponse",
    "ComplianceTemplate",
    "ComplianceTemplatesResponse",
    "ConfidenceSignal",
    "DemandForecastPoint",
    "DemographicMetric",
    "ExpansionRecommendation",
    "LaunchStep",
    "MarketInsight",
    "PricingBand",
    "PricingIntelResponse",
    "PromotionCampaign",
    "RegulationItem",
    "ServiceZone",
    "TrendPoint",
    "CityKitchenHighlight",
    "CurrencyDescriptor",
    "CurrencyListResponse",
    "CurrencyRatesResponse",
]
