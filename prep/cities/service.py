"""Application service powering the multi-city expansion API."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from statistics import mean, median
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.cache import RedisProtocol
from prep.matching.schemas import KitchenMatchModel
from prep.matching.service import MatchingService
from prep.models.orm import Booking, BookingStatus, Kitchen

from .schemas import (
    AddressValidationRequest,
    AddressValidationResponse,
    BookingQuoteRequest,
    BookingQuoteResponse,
    ChecklistItem,
    CityCompetitionResponse,
    CityDemandForecastResponse,
    CityDemographicsResponse,
    CityKitchenHighlight,
    CityLaunchRequest,
    CityLaunchResponse,
    CityMarketAnalyticsResponse,
    CityMarketMetrics,
    CityPromotionRequest,
    CityPromotionResponse,
    CityReadinessResponse,
    CityRegulationResponse,
    CityServiceZonesResponse,
    CompetitorProfile,
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ComplianceTemplate,
    ComplianceTemplatesResponse,
    ConfidenceSignal,
    DemandForecastPoint,
    DemographicMetric,
    ExpansionRecommendation,
    LaunchStep,
    MarketInsight,
    PricingBand,
    PricingIntelResponse,
    PromotionCampaign,
    RegulationItem,
    ServiceZone,
    TrendPoint,
)

logger = logging.getLogger(__name__)


class CityExpansionService:
    """Provides market, compliance, and launch tooling for city expansion."""

    DEFAULT_CURRENCY = "USD"
    RATE_CACHE_KEY = "city-expansion:currency-rates"
    RATE_TTL_SECONDS = 3600
    LAUNCH_PLAN_TTL_SECONDS = 7 * 24 * 3600

    SUPPORTED_CURRENCIES: dict[str, dict[str, str]] = {
        "USD": {"name": "US Dollar", "symbol": "$"},
        "EUR": {"name": "Euro", "symbol": "€"},
        "GBP": {"name": "British Pound", "symbol": "£"},
        "CAD": {"name": "Canadian Dollar", "symbol": "CA$"},
        "AUD": {"name": "Australian Dollar", "symbol": "A$"},
    }

    DEFAULT_RATE_TABLE: dict[str, float] = {
        "USD": 1.0,
        "EUR": 0.92,
        "GBP": 0.79,
        "CAD": 1.36,
        "AUD": 1.52,
    }

    CITY_REGULATIONS: dict[str, list[RegulationItem]] = {
        "san francisco": [
            RegulationItem(
                category="Health Permit",
                description="Submit SFDPH food facility permit and latest inspection results",
                due_in_days=30,
            ),
            RegulationItem(
                category="Business License",
                description="Register with the San Francisco Office of the Treasurer & Tax Collector",
                due_in_days=45,
            ),
            RegulationItem(
                category="Insurance",
                description="Provide proof of $1M liability coverage with the city listed as additionally insured",
                due_in_days=15,
            ),
        ],
        "austin": [
            RegulationItem(
                category="Health Inspection",
                description="Schedule Austin Public Health commercial kitchen inspection",
                due_in_days=21,
            ),
            RegulationItem(
                category="Waste Disposal",
                description="Document grease trap maintenance plan and hauling provider",
                due_in_days=30,
            ),
        ],
    }

    COMPLIANCE_TEMPLATES: dict[str, list[ComplianceTemplate]] = {
        "san francisco": [
            ComplianceTemplate(
                city="San Francisco",
                name="SF Kitchen Launch Checklist",
                description="Step-by-step document outlining food permit, fire safety, and zoning approvals",
                url="https://docs.prep.local/templates/sf-launch-checklist.pdf",
            ),
            ComplianceTemplate(
                city="San Francisco",
                name="Shared Kitchen Agreement",
                description="Standard operating agreement tailored for SF shared commercial kitchens",
                url="https://docs.prep.local/templates/shared-kitchen-agreement.docx",
            ),
        ],
        "austin": [
            ComplianceTemplate(
                city="Austin",
                name="Austin Food Enterprise Permit Packet",
                description="Compilation of all forms required by Austin Public Health",
                url="https://docs.prep.local/templates/austin-permit-packet.pdf",
            )
        ],
    }

    def __init__(
        self,
        session: AsyncSession,
        redis: RedisProtocol,
        *,
        matching_service: MatchingService | None = None,
    ) -> None:
        self._session = session
        self._redis = redis
        self._matching_service = matching_service or MatchingService(session, redis)
        self._rate_table: dict[str, float] = dict(self.DEFAULT_RATE_TABLE)

    # ------------------------------------------------------------------
    # Public API - City Market Intelligence
    # ------------------------------------------------------------------
    async def get_city_analytics(
        self,
        city: str,
        *,
        currency: str | None = None,
    ) -> CityMarketAnalyticsResponse:
        normalized_city = self._normalize_city(city)
        currency_code = self._normalize_currency(currency or self.DEFAULT_CURRENCY)

        kitchen_stats = await self._session.execute(
            select(
                func.count(Kitchen.id).label("kitchen_count"),
                func.sum(case((Kitchen.published.is_(True), 1), else_=0)).label("published"),
                func.avg(Kitchen.hourly_rate).label("avg_rate"),
                func.avg(Kitchen.trust_score).label("avg_trust"),
            ).where(func.lower(Kitchen.city) == normalized_city)
        )
        stats_row = kitchen_stats.one()
        total_kitchens = int(stats_row.kitchen_count or 0)
        active_kitchens = int(stats_row.published or 0)
        average_rate = float(stats_row.avg_rate) if stats_row.avg_rate is not None else None
        average_trust = float(stats_row.avg_trust) if stats_row.avg_trust is not None else None

        window_start = datetime.now(UTC) - timedelta(days=30)
        booking_stmt = (
            select(
                func.count(Booking.id).label("bookings"),
                func.sum(Booking.total_amount).label("revenue"),
            )
            .join(Kitchen, Kitchen.id == Booking.kitchen_id)
            .where(func.lower(Kitchen.city) == normalized_city)
            .where(Booking.status == BookingStatus.COMPLETED)
            .where(Booking.start_time >= window_start)
        )
        booking_row = (await self._session.execute(booking_stmt)).one()
        booking_count_30d = int(booking_row.bookings or 0)
        revenue_30d = float(booking_row.revenue or 0.0)

        trends = await self._load_trends(normalized_city)
        demand_index = self._calculate_demand_index(total_kitchens, booking_count_30d)

        top_kitchens_raw = await self._matching_service.recommend_top_kitchens_for_city(
            normalized_city
        )
        top_kitchens = await self._to_highlights(top_kitchens_raw, currency_code)

        metrics = CityMarketMetrics(
            kitchen_count=total_kitchens,
            active_kitchens=active_kitchens,
            average_hourly_rate=self._convert_value(average_rate, currency_code),
            average_trust_score=average_trust,
            bookings_last_30_days=booking_count_30d,
            revenue_last_30_days=self._convert_value(revenue_30d, currency_code),
            demand_index=demand_index,
        )

        confidence = [
            ConfidenceSignal(
                metric="kitchen_sample",
                score=min(total_kitchens / 10, 1.0),
                description=f"{total_kitchens} kitchens analysed",
            ),
            ConfidenceSignal(
                metric="booking_sample",
                score=min(booking_count_30d / 50, 1.0),
                description=f"{booking_count_30d} bookings in last 30 days",
            ),
        ]

        insights = self._build_market_insights(metrics, top_kitchens)
        recommendations = self._build_market_recommendations(metrics)

        return CityMarketAnalyticsResponse(
            city=self._title_case_city(normalized_city),
            currency=currency_code,
            metrics=metrics,
            trends=trends,
            top_kitchens=top_kitchens,
            confidence=confidence,
            insights=insights,
            recommendations=recommendations,
        )

    async def get_city_competition(
        self,
        city: str,
        *,
        currency: str | None = None,
    ) -> CityCompetitionResponse:
        normalized_city = self._normalize_city(city)
        currency_code = self._normalize_currency(currency or self.DEFAULT_CURRENCY)

        matches = await self._matching_service.recommend_top_kitchens_for_city(
            normalized_city, limit=8
        )
        competitors: list[CompetitorProfile] = []
        for match in matches:
            converted_rate = self._convert_value(match.hourly_rate, currency_code)
            competitors.append(
                CompetitorProfile(
                    kitchen_id=match.kitchen_id,
                    name=match.kitchen_name,
                    hourly_rate=match.hourly_rate,
                    converted_hourly_rate=converted_rate,
                    occupancy_rate=match.popularity_index,
                    rating=match.external_rating,
                    confidence=match.confidence,
                )
            )

        market_share = min(
            sum((item.occupancy_rate or 0) for item in competitors) / len(competitors or [1]), 1.0
        )

        confidence = [
            ConfidenceSignal(
                metric="competitor_sample",
                score=min(len(competitors) / 5, 1.0),
                description=f"Analyzed {len(competitors)} leading competitors",
            )
        ]
        insights = self._build_competition_insights(competitors)
        recommendations = self._build_competition_recommendations(competitors)

        return CityCompetitionResponse(
            city=self._title_case_city(normalized_city),
            currency=currency_code,
            competitors=competitors,
            market_share_estimate=market_share,
            confidence=confidence,
            insights=insights,
            recommendations=recommendations,
        )

    async def get_city_demand(
        self,
        city: str,
        *,
        currency: str | None = None,
    ) -> CityDemandForecastResponse:
        normalized_city = self._normalize_city(city)
        currency_code = self._normalize_currency(currency or self.DEFAULT_CURRENCY)

        trends = await self._load_trends(normalized_city)
        demand_index = self._calculate_demand_index_from_trends(trends)
        forecast = self._forecast_demand(trends, currency_code)

        confidence = [
            ConfidenceSignal(
                metric="trend_depth",
                score=min(len(trends) / 6, 1.0),
                description=f"{len(trends)} months of history",
            )
        ]
        insights = self._build_demand_insights(demand_index, forecast)
        recommendations = self._build_demand_recommendations(demand_index)

        return CityDemandForecastResponse(
            city=self._title_case_city(normalized_city),
            currency=currency_code,
            demand_index=demand_index,
            forecast=forecast,
            confidence=confidence,
            insights=insights,
            recommendations=recommendations,
        )

    async def get_city_pricing(
        self,
        city: str,
        *,
        currency: str | None = None,
    ) -> PricingIntelResponse:
        normalized_city = self._normalize_city(city)
        currency_code = self._normalize_currency(currency or self.DEFAULT_CURRENCY)

        rates_stmt = (
            select(Kitchen.hourly_rate)
            .where(func.lower(Kitchen.city) == normalized_city)
            .where(Kitchen.hourly_rate.is_not(None))
        )
        rows = await self._session.execute(rates_stmt)
        rates = [float(row.hourly_rate) for row in rows if row.hourly_rate is not None]
        rates.sort()

        if rates:
            avg_rate = mean(rates)
            median_rate = median(rates)
        else:
            avg_rate = None
            median_rate = None

        pricing_bands = []
        for percentile in (25, 50, 75, 90):
            rate_value = self._percentile(rates, percentile)
            pricing_bands.append(
                PricingBand(
                    percentile=percentile,
                    hourly_rate=rate_value,
                    converted_rate=self._convert_value(rate_value, currency_code),
                )
            )

        confidence = [
            ConfidenceSignal(
                metric="pricing_sample",
                score=min(len(rates) / 20, 1.0),
                description=f"{len(rates)} kitchens with published rates",
            )
        ]
        insights = self._build_pricing_insights(avg_rate, median_rate)
        recommendations = self._build_pricing_recommendations(avg_rate, median_rate)

        return PricingIntelResponse(
            city=self._title_case_city(normalized_city),
            currency=currency_code,
            median_hourly_rate=self._convert_value(median_rate, currency_code),
            average_hourly_rate=self._convert_value(avg_rate, currency_code),
            pricing_bands=pricing_bands,
            confidence=confidence,
            insights=insights,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Compliance utilities
    # ------------------------------------------------------------------
    async def get_city_regulations(self, city: str) -> CityRegulationResponse:
        normalized_city = self._normalize_city(city)
        requirements = self.CITY_REGULATIONS.get(
            normalized_city,
            [
                RegulationItem(
                    category="General",
                    description="Verify local business licensing, zoning approval, and fire inspections",
                    due_in_days=30,
                )
            ],
        )

        confidence = [
            ConfidenceSignal(
                metric="regulation_sources",
                score=0.7 if normalized_city in self.CITY_REGULATIONS else 0.4,
                description="Sourced from curated compliance playbooks",
            )
        ]
        insights = [
            MarketInsight(
                title="Plan regulatory submissions early",
                description="Average approval timelines range between 3-6 weeks across food safety, fire, and licensing agencies.",
                confidence=confidence[0].score,
            )
        ]
        recommendations = [
            ExpansionRecommendation(
                action="Sequence compliance milestones",
                impact="Avoid launch delays by preparing documents in parallel",
                priority="high",
                confidence=confidence[0].score,
            )
        ]

        return CityRegulationResponse(
            city=self._title_case_city(normalized_city),
            requirements=requirements,
            confidence=confidence,
            insights=insights,
            recommendations=recommendations,
        )

    async def check_compliance(self, payload: ComplianceCheckRequest) -> ComplianceCheckResponse:
        normalized_city = self._normalize_city(payload.city)
        requirements = {
            item.category.lower(): item for item in self.CITY_REGULATIONS.get(normalized_city, [])
        }

        submitted = {doc.lower() for doc in payload.submitted_documents}
        certifications = {cert.lower() for cert in payload.certifications}

        missing: list[str] = []
        for requirement in requirements.values():
            category = requirement.category.lower()
            if category not in submitted and category not in certifications:
                missing.append(requirement.category)

        if missing:
            status_value: str = "pending"
        else:
            status_value = "pass" if requirements else "pending"

        confidence = 0.6 + 0.4 * (1 - len(missing) / max(len(requirements) or 1, 1))
        insights = [
            MarketInsight(
                title="Compliance coverage",
                description=f"{len(requirements) - len(missing)} of {len(requirements)} requirements satisfied",
                confidence=confidence,
            )
        ]
        recommendations = [
            ExpansionRecommendation(
                action="Address outstanding requirements",
                impact="Complete submissions to unblock launch approval",
                priority="high" if missing else "medium",
                confidence=confidence,
            )
        ]

        return ComplianceCheckResponse(
            city=self._title_case_city(normalized_city),
            status=status_value if requirements else "pending",
            missing_requirements=missing,
            confidence=min(confidence, 1.0),
            insights=insights,
            recommendations=recommendations,
        )

    async def get_compliance_templates(
        self, city: str | None = None
    ) -> ComplianceTemplatesResponse:
        if city:
            normalized_city = self._normalize_city(city)
            templates = self.COMPLIANCE_TEMPLATES.get(normalized_city, [])
        else:
            templates = [
                template
                for template_list in self.COMPLIANCE_TEMPLATES.values()
                for template in template_list
            ]

        insights = [
            MarketInsight(
                title="Standardized templates",
                description="Templates accelerate regulatory submissions and keep documentation consistent across markets.",
                confidence=0.8,
            )
        ]
        recommendations = [
            ExpansionRecommendation(
                action="Localize documentation",
                impact="Tailor templates with city-specific contact details and submission portals",
                priority="medium",
                confidence=0.7,
            )
        ]

        return ComplianceTemplatesResponse(
            templates=templates,
            confidence=[
                ConfidenceSignal(
                    metric="template_coverage",
                    score=0.7,
                    description="Curated compliance templates",
                ),
            ],
            insights=insights,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Currency and pricing utilities
    # ------------------------------------------------------------------
    async def list_currencies(self) -> tuple[list[dict[str, str]], list[ConfidenceSignal]]:
        currencies = [{"code": code, **meta} for code, meta in self.SUPPORTED_CURRENCIES.items()]
        confidence = [
            ConfidenceSignal(
                metric="fx_sources",
                score=0.8,
                description="Daily reference rates cached for 1 hour",
            )
        ]
        return currencies, confidence

    async def get_currency_rates(
        self, base_currency: str | None = None
    ) -> tuple[str, dict[str, float], datetime]:
        normalized_base = self._normalize_currency(base_currency or self.DEFAULT_CURRENCY)
        rate_table = await self._load_rate_table()
        self._rate_table = rate_table
        base_rate = rate_table.get(normalized_base)
        if base_rate is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported base currency"
            )

        normalized_rates = {code: round(value / base_rate, 6) for code, value in rate_table.items()}
        return normalized_base, normalized_rates, datetime.now(UTC)

    async def quote_booking(self, payload: BookingQuoteRequest) -> BookingQuoteResponse:
        kitchen = await self._session.get(Kitchen, payload.kitchen_id)
        if kitchen is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")

        hourly_rate = float(kitchen.hourly_rate) if kitchen.hourly_rate is not None else None
        base_currency = self.DEFAULT_CURRENCY
        target_currency = self._normalize_currency(payload.currency)

        converted_hourly = self._convert_value(hourly_rate, target_currency)
        total_cost = hourly_rate * payload.hours if hourly_rate is not None else None
        converted_total = self._convert_value(total_cost, target_currency)

        fees = None
        converted_fees = None
        if payload.include_fees and total_cost is not None:
            fees = round(total_cost * 0.08, 2)
            converted_fees = self._convert_value(fees, target_currency)
            total_cost += fees
            converted_total = self._convert_value(total_cost, target_currency)

        insights = [
            MarketInsight(
                title="Dynamic currency conversion",
                description=f"Quote generated using latest {target_currency} conversion rate.",
                confidence=0.8,
            )
        ]
        recommendations = [
            ExpansionRecommendation(
                action="Lock quote",
                impact="Secure pricing for the customer within 24 hours",
                priority="medium",
                confidence=0.7,
            )
        ]

        return BookingQuoteResponse(
            kitchen_id=payload.kitchen_id,
            hours=payload.hours,
            base_currency=base_currency,
            target_currency=target_currency,
            hourly_rate=hourly_rate,
            converted_hourly_rate=converted_hourly,
            total_cost=total_cost,
            converted_total_cost=converted_total,
            fees=fees,
            converted_fees=converted_fees,
            confidence=0.8,
            insights=insights,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Geographic intelligence
    # ------------------------------------------------------------------
    async def validate_address(
        self, payload: AddressValidationRequest
    ) -> AddressValidationResponse:
        normalized_city = self._normalize_city(payload.city)
        issues: list[str] = []
        is_valid = True

        if not payload.address_line.strip():
            issues.append("Address line required")
            is_valid = False
        if payload.city.strip().lower() != normalized_city:
            issues.append("City mismatch detected")
            is_valid = False
        if payload.postal_code and len(payload.postal_code) < 4:
            issues.append("Postal code appears incomplete")
            is_valid = False

        normalized_address = (
            f"{payload.address_line.strip()}, {self._title_case_city(normalized_city)}"
        )
        if payload.state:
            normalized_address += f", {payload.state.upper()}"
        if payload.postal_code:
            normalized_address += f" {payload.postal_code.upper()}"

        recommendations = [
            ExpansionRecommendation(
                action="Verify local geo-coding",
                impact="Ensure routing and delivery services recognize the address",
                priority="medium",
                confidence=0.6,
            )
        ]

        return AddressValidationResponse(
            city=self._title_case_city(normalized_city),
            is_valid=is_valid,
            normalized_address=normalized_address if is_valid else None,
            confidence=0.6 if is_valid else 0.4,
            issues=issues,
            recommendations=recommendations,
        )

    async def get_service_zones(self, city: str) -> CityServiceZonesResponse:
        normalized_city = self._normalize_city(city)
        top_kitchens = await self._matching_service.recommend_top_kitchens_for_city(
            normalized_city, limit=6
        )

        if not top_kitchens:
            zones = [
                ServiceZone(
                    name="Core Market",
                    coverage="City center",
                    restrictions=[],
                    confidence=0.4,
                )
            ]
        else:
            zones = [
                ServiceZone(
                    name="Downtown Core",
                    coverage="High-density commercial district",
                    restrictions=["Peak-hour logistics coordination"],
                    confidence=0.7,
                ),
                ServiceZone(
                    name="Expansion Ring",
                    coverage="Neighborhood clusters within 15km",
                    restrictions=["Coordinate shared storage"],
                    confidence=0.6,
                ),
                ServiceZone(
                    name="Pilot Fringe",
                    coverage="Outlying suburbs suitable for pilot hosts",
                    restrictions=["Limited delivery partners"],
                    confidence=0.5,
                ),
            ]

        insights = [
            MarketInsight(
                title="Optimize zone roll-out",
                description="Prioritize onboarding in high-density zones before extending to fringe areas",
                confidence=0.7,
            )
        ]
        recommendations = [
            ExpansionRecommendation(
                action="Sequence onboarding by zone",
                impact="Concentrate marketing and support resources for faster traction",
                priority="high",
                confidence=0.7,
            )
        ]

        return CityServiceZonesResponse(
            city=self._title_case_city(normalized_city),
            zones=zones,
            insights=insights,
            recommendations=recommendations,
        )

    async def get_demographics(self, city: str) -> CityDemographicsResponse:
        normalized_city = self._normalize_city(city)

        total_kitchens = await self._session.scalar(
            select(func.count(Kitchen.id)).where(func.lower(Kitchen.city) == normalized_city)
        )
        unique_hosts = await self._session.scalar(
            select(func.count(func.distinct(Kitchen.host_id))).where(
                func.lower(Kitchen.city) == normalized_city
            )
        )
        bookings_last_quarter = await self._session.scalar(
            select(func.count(Booking.id))
            .join(Kitchen, Kitchen.id == Booking.kitchen_id)
            .where(func.lower(Kitchen.city) == normalized_city)
            .where(Booking.status == BookingStatus.COMPLETED)
            .where(Booking.start_time >= datetime.now(UTC) - timedelta(days=90))
        )

        food_business_density = (total_kitchens or 0) / max((unique_hosts or 1), 1)

        metrics = [
            DemographicMetric(
                name="Active hosts",
                value=float(unique_hosts or 0),
                unit="hosts",
                confidence=0.6,
            ),
            DemographicMetric(
                name="Quarterly bookings",
                value=float(bookings_last_quarter or 0),
                unit="bookings",
                confidence=0.6,
            ),
            DemographicMetric(
                name="Kitchen-to-host ratio",
                value=float(food_business_density),
                unit="ratio",
                confidence=0.6,
            ),
        ]

        insights = [
            MarketInsight(
                title="Host concentration",
                description="Balanced host-to-kitchen ratio indicates healthy supply distribution.",
                confidence=0.6,
            )
        ]
        recommendations = [
            ExpansionRecommendation(
                action="Recruit anchor hosts",
                impact="Increase density by onboarding multi-location operators",
                priority="medium",
                confidence=0.6,
            )
        ]

        return CityDemographicsResponse(
            city=self._title_case_city(normalized_city),
            population_estimate=int((unique_hosts or 0) * 25 + (total_kitchens or 0) * 10),
            median_income=None,
            food_business_density=food_business_density if food_business_density else None,
            metrics=metrics,
            insights=insights,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Launch management
    # ------------------------------------------------------------------
    async def initialize_launch(
        self,
        city: str,
        payload: CityLaunchRequest,
    ) -> CityLaunchResponse:
        normalized_city = self._normalize_city(city)
        launched_at = datetime.now(UTC)

        plan = [
            LaunchStep(name="Market validation", status="completed", owner=payload.lead_owner),
            LaunchStep(name="Compliance approvals", status="in_progress", owner=payload.lead_owner),
            LaunchStep(name="Host onboarding", status="pending", owner=None),
            LaunchStep(name="Marketing launch", status="pending", owner=None),
        ]

        cache_key = self._launch_plan_cache_key(normalized_city)
        serialized = json.dumps(
            {
                "launched_at": launched_at.isoformat(),
                "plan": [step.model_dump() for step in plan],
            }
        )
        await self._redis.setex(cache_key, self.LAUNCH_PLAN_TTL_SECONDS, serialized)

        insights = [
            MarketInsight(
                title="Launch program initiated",
                description="Cross-functional launch plan cached for coordination across teams.",
                confidence=0.8,
            )
        ]
        recommendations = [
            ExpansionRecommendation(
                action="Assign owners",
                impact="Ensure every launch task has a single accountable owner",
                priority="high",
                confidence=0.8,
            )
        ]

        return CityLaunchResponse(
            city=self._title_case_city(normalized_city),
            launched_at=launched_at,
            plan=plan,
            confidence=[
                ConfidenceSignal(
                    metric="launch_plan",
                    score=0.8,
                    description="Launch plan cached in coordination workspace",
                )
            ],
            insights=insights,
            recommendations=recommendations,
        )

    async def get_launch_readiness(self, city: str) -> CityReadinessResponse:
        normalized_city = self._normalize_city(city)
        launch_plan = await self._load_launch_plan(normalized_city)
        analytics = await self.get_city_analytics(normalized_city)
        demand = await self.get_city_demand(normalized_city)

        compliance_step = next(
            (step for step in launch_plan.plan if "compliance" in step.name.lower()),
            None,
        )
        compliance_complete = compliance_step is not None and compliance_step.status == "completed"

        checklist = [
            ChecklistItem(
                name="Compliance approvals",
                status="complete" if compliance_complete else "in_progress",
                confidence=0.7 if compliance_complete else 0.5,
            ),
            ChecklistItem(
                name="Host supply",
                status="complete" if analytics.metrics.active_kitchens >= 5 else "in_progress",
                confidence=analytics.confidence[0].score,
            ),
            ChecklistItem(
                name="Demand readiness",
                status="complete" if demand.demand_index >= 0.6 else "in_progress",
                confidence=demand.confidence[0].score,
            ),
        ]

        readiness_score = mean(
            item.confidence if item.status == "complete" else item.confidence * 0.7
            for item in checklist
        )

        insights = [
            MarketInsight(
                title="Launch readiness overview",
                description="Compliance and supply metrics indicate strong readiness, continue boosting demand signals.",
                confidence=readiness_score,
            )
        ]
        recommendations = [
            ExpansionRecommendation(
                action="Close outstanding tasks",
                impact="Elevate readiness by finalizing in-progress milestones",
                priority="high",
                confidence=readiness_score,
            )
        ]

        return CityReadinessResponse(
            city=self._title_case_city(normalized_city),
            readiness_score=min(readiness_score, 1.0),
            checklist=checklist,
            insights=insights,
            recommendations=recommendations,
        )

    async def promote_city(
        self,
        city: str,
        payload: CityPromotionRequest,
    ) -> CityPromotionResponse:
        normalized_city = self._normalize_city(city)
        channels = payload.channels or ["email", "paid_social", "partnerships"]
        budget = payload.budget or 10000.0

        allocation = budget / len(channels)
        campaigns = [
            PromotionCampaign(
                channel=channel,
                allocation=round(allocation, 2),
                kpi="Launch signups" if channel != "partnerships" else "Partner activations",
                confidence=0.65,
            )
            for channel in channels
        ]

        insights = [
            MarketInsight(
                title="Multi-channel activation",
                description="Balanced spend across owned, paid, and partner channels accelerates early traction.",
                confidence=0.65,
            )
        ]
        recommendations = [
            ExpansionRecommendation(
                action="Set weekly KPIs",
                impact="Enable rapid iteration on channel mix as performance data arrives",
                priority="medium",
                confidence=0.65,
            )
        ]

        return CityPromotionResponse(
            city=self._title_case_city(normalized_city),
            budget=budget,
            campaigns=campaigns,
            insights=insights,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _load_trends(self, normalized_city: str) -> list[TrendPoint]:
        six_months_ago = datetime.now(UTC) - timedelta(days=180)

        bind = getattr(self._session, "bind", None)
        dialect_name = getattr(getattr(bind, "dialect", None), "name", "") if bind else ""
        if dialect_name == "sqlite":
            period_expr = func.strftime("%Y-%m-01", Booking.start_time)
        else:
            period_expr = func.date_trunc("month", Booking.start_time)

        stmt = (
            select(
                period_expr.label("period"),
                func.count(Booking.id).label("bookings"),
                func.sum(Booking.total_amount).label("revenue"),
            )
            .join(Kitchen, Kitchen.id == Booking.kitchen_id)
            .where(func.lower(Kitchen.city) == normalized_city)
            .where(Booking.status == BookingStatus.COMPLETED)
            .where(Booking.start_time >= six_months_ago)
            .group_by(period_expr)
            .order_by(period_expr)
        )
        rows = await self._session.execute(stmt)
        trends = [
            TrendPoint(
                period_start=self._coerce_period(row.period),
                bookings=int(row.bookings or 0),
                revenue=float(row.revenue or 0.0),
            )
            for row in rows
        ]
        return trends

    def _calculate_demand_index(self, kitchen_count: int, bookings_30d: int) -> float:
        if kitchen_count == 0:
            return 0.0
        ratio = bookings_30d / max(kitchen_count * 4, 1)
        return max(0.0, min(ratio, 1.0))

    def _coerce_period(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            normalized = value
            if len(normalized) == 7:
                normalized = f"{normalized}-01"
            try:
                parsed = datetime.fromisoformat(normalized)
            except ValueError:
                return datetime.now(UTC)
            return parsed
        return datetime.now(UTC)

    def _calculate_demand_index_from_trends(self, trends: list[TrendPoint]) -> float:
        if not trends:
            return 0.0
        latest = trends[-1]
        average = mean(point.bookings for point in trends) if trends else 0
        if average == 0:
            return 0.0
        return max(0.0, min(latest.bookings / (average * 1.5), 1.0))

    def _forecast_demand(
        self,
        trends: list[TrendPoint],
        currency_code: str,
    ) -> list[DemandForecastPoint]:
        if not trends:
            base_date = datetime.now(UTC)
            return [
                DemandForecastPoint(
                    period_start=base_date + timedelta(days=30 * i),
                    projected_bookings=0.0,
                    projected_revenue=0.0,
                    confidence=0.4,
                )
                for i in range(1, 4)
            ]

        growth = trends[-1].bookings - trends[-2].bookings if len(trends) >= 2 else 0
        avg_revenue = mean(point.revenue for point in trends) if trends else 0
        last_date = trends[-1].period_start
        last_bookings = trends[-1].bookings

        forecast: list[DemandForecastPoint] = []
        for i in range(1, 4):
            projected_bookings = max(last_bookings + growth * i, 0)
            projected_revenue = projected_bookings * (avg_revenue / max(last_bookings or 1, 1))
            forecast.append(
                DemandForecastPoint(
                    period_start=last_date + timedelta(days=30 * i),
                    projected_bookings=round(projected_bookings, 2),
                    projected_revenue=self._convert_value(projected_revenue, currency_code) or 0.0,
                    confidence=0.5 + min(i * 0.1, 0.3),
                )
            )
        return forecast

    async def _to_highlights(
        self,
        matches: list[KitchenMatchModel],
        currency_code: str,
    ) -> list[CityKitchenHighlight]:
        highlights: list[CityKitchenHighlight] = []
        for match in matches[:5]:
            highlights.append(
                CityKitchenHighlight(
                    kitchen_id=match.kitchen_id,
                    name=match.kitchen_name,
                    score=match.score,
                    confidence=match.confidence,
                    hourly_rate=match.hourly_rate,
                    converted_hourly_rate=self._convert_value(match.hourly_rate, currency_code),
                    currency=currency_code,
                    popularity_index=match.popularity_index,
                    demand_forecast=match.demand_forecast,
                )
            )
        return highlights

    def _build_market_insights(
        self,
        metrics: CityMarketMetrics,
        top_kitchens: list[CityKitchenHighlight],
    ) -> list[MarketInsight]:
        insights: list[MarketInsight] = []
        if metrics.average_trust_score and metrics.average_trust_score >= 4.2:
            insights.append(
                MarketInsight(
                    title="High customer trust",
                    description="Average trust score above 4.2 indicates strong quality perception across hosts.",
                    confidence=0.7,
                )
            )
        if metrics.bookings_last_30_days > metrics.kitchen_count * 3:
            insights.append(
                MarketInsight(
                    title="Above-average demand",
                    description="Bookings per kitchen outpace platform baseline, signaling strong renter appetite.",
                    confidence=0.75,
                )
            )
        if not insights:
            insights.append(
                MarketInsight(
                    title="Monitor supply-demand balance",
                    description="Continue tracking booking velocity as new hosts come online.",
                    confidence=0.5,
                )
            )
        if top_kitchens:
            insights.append(
                MarketInsight(
                    title="Anchor kitchens identified",
                    description=f"Top performer: {top_kitchens[0].name} with confidence {top_kitchens[0].confidence:.2f}.",
                    confidence=0.6,
                )
            )
        return insights

    def _build_market_recommendations(
        self, metrics: CityMarketMetrics
    ) -> list[ExpansionRecommendation]:
        recommendations: list[ExpansionRecommendation] = []
        if metrics.demand_index < 0.5:
            recommendations.append(
                ExpansionRecommendation(
                    action="Increase marketing activation",
                    impact="Boost renter acquisition to utilize available kitchen capacity",
                    priority="high",
                    confidence=0.65,
                )
            )
        if metrics.active_kitchens < max(5, metrics.kitchen_count // 2):
            recommendations.append(
                ExpansionRecommendation(
                    action="Onboard additional hosts",
                    impact="Expand premium inventory to capture demand",
                    priority="medium",
                    confidence=0.6,
                )
            )
        if not recommendations:
            recommendations.append(
                ExpansionRecommendation(
                    action="Maintain growth cadence",
                    impact="Current supply and demand are balanced; sustain monitoring cadence",
                    priority="medium",
                    confidence=0.5,
                )
            )
        return recommendations

    def _build_competition_insights(
        self, competitors: list[CompetitorProfile]
    ) -> list[MarketInsight]:
        if not competitors:
            return [
                MarketInsight(
                    title="Limited competition",
                    description="Few comparable kitchens published in this market.",
                    confidence=0.4,
                )
            ]
        avg_rate = (
            mean([item.hourly_rate for item in competitors if item.hourly_rate])
            if competitors
            else None
        )
        insights = [
            MarketInsight(
                title="Competitive benchmarking",
                description="Top operators show strong occupancy and rating scores.",
                confidence=0.6,
            )
        ]
        if avg_rate:
            insights.append(
                MarketInsight(
                    title="Average competitor rate",
                    description=f"Peer hourly rate benchmark ~{avg_rate:.2f}",
                    confidence=0.55,
                )
            )
        return insights

    def _build_competition_recommendations(
        self,
        competitors: list[CompetitorProfile],
    ) -> list[ExpansionRecommendation]:
        recommendations = [
            ExpansionRecommendation(
                action="Differentiate supply",
                impact="Highlight unique equipment, certifications, or extended hours",
                priority="medium",
                confidence=0.6,
            )
        ]
        if competitors and any((item.occupancy_rate or 0) > 0.7 for item in competitors):
            recommendations.append(
                ExpansionRecommendation(
                    action="Prioritize revenue management",
                    impact="Test premium pricing tiers on high-occupancy zones",
                    priority="medium",
                    confidence=0.55,
                )
            )
        return recommendations

    def _build_demand_insights(
        self,
        demand_index: float,
        forecast: list[DemandForecastPoint],
    ) -> list[MarketInsight]:
        insights = [
            MarketInsight(
                title="Demand outlook",
                description=f"Demand index at {demand_index:.2f} with growth trajectory across next 3 months.",
                confidence=0.6,
            )
        ]
        if forecast and forecast[-1].projected_bookings > forecast[0].projected_bookings:
            insights.append(
                MarketInsight(
                    title="Momentum building",
                    description="Projected bookings trending upward over the next quarter.",
                    confidence=0.6,
                )
            )
        return insights

    def _build_demand_recommendations(self, demand_index: float) -> list[ExpansionRecommendation]:
        if demand_index < 0.5:
            return [
                ExpansionRecommendation(
                    action="Accelerate renter acquisition",
                    impact="Partner with local associations to stimulate bookings",
                    priority="high",
                    confidence=0.6,
                )
            ]
        return [
            ExpansionRecommendation(
                action="Scale supply",
                impact="Add kitchens in high-growth neighborhoods to capture momentum",
                priority="medium",
                confidence=0.6,
            )
        ]

    def _build_pricing_insights(
        self,
        avg_rate: float | None,
        median_rate: float | None,
    ) -> list[MarketInsight]:
        insights: list[MarketInsight] = []
        if avg_rate:
            insights.append(
                MarketInsight(
                    title="Average hourly rate",
                    description=f"Average rate currently {avg_rate:.2f} USD",
                    confidence=0.55,
                )
            )
        if median_rate:
            insights.append(
                MarketInsight(
                    title="Median pricing",
                    description=f"Median hourly rate at {median_rate:.2f} USD indicates balanced distribution",
                    confidence=0.55,
                )
            )
        if not insights:
            insights.append(
                MarketInsight(
                    title="Pricing data limited",
                    description="Publish more rates to unlock deeper pricing intelligence.",
                    confidence=0.4,
                )
            )
        return insights

    def _build_pricing_recommendations(
        self,
        avg_rate: float | None,
        median_rate: float | None,
    ) -> list[ExpansionRecommendation]:
        recommendations: list[ExpansionRecommendation] = []
        if avg_rate and median_rate and avg_rate > median_rate * 1.15:
            recommendations.append(
                ExpansionRecommendation(
                    action="Introduce mid-tier offerings",
                    impact="Close the pricing gap to capture value-conscious renters",
                    priority="medium",
                    confidence=0.55,
                )
            )
        else:
            recommendations.append(
                ExpansionRecommendation(
                    action="Maintain pricing flexibility",
                    impact="Monitor rates as new inventory launches",
                    priority="medium",
                    confidence=0.5,
                )
            )
        return recommendations

    async def _load_rate_table(self) -> dict[str, float]:
        cached = await self._redis.get(self.RATE_CACHE_KEY)
        if cached:
            try:
                payload = json.loads(cached)
                table = {code.upper(): float(value) for code, value in payload.items()}
                self._rate_table = table
                return table
            except (TypeError, ValueError):
                logger.warning(
                    "Invalid cached currency table, regenerating", extra={"payload": cached}
                )
        await self._redis.setex(
            self.RATE_CACHE_KEY,
            self.RATE_TTL_SECONDS,
            json.dumps(self.DEFAULT_RATE_TABLE),
        )
        self._rate_table = dict(self.DEFAULT_RATE_TABLE)
        return self._rate_table

    def _convert_value(self, value: float | None, target_currency: str) -> float | None:
        if value is None:
            return None
        rate_table = self._rate_table or self.DEFAULT_RATE_TABLE
        target = self._normalize_currency(target_currency)
        base_value = rate_table.get(self.DEFAULT_CURRENCY, 1.0)
        target_rate = rate_table.get(target)
        if target_rate is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported currency"
            )
        converted = value * (target_rate / base_value)
        return round(converted, 2)

    def _normalize_city(self, city: str) -> str:
        if not city or not city.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="City name is required"
            )
        return city.strip().lower()

    def _title_case_city(self, normalized_city: str) -> str:
        return normalized_city.title()

    def _normalize_currency(self, currency: str) -> str:
        code = (currency or self.DEFAULT_CURRENCY).strip().upper()
        if code not in self.SUPPORTED_CURRENCIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported currency"
            )
        return code

    def _percentile(self, data: list[float], percentile: int) -> float | None:
        if not data:
            return None
        if percentile <= 0:
            return data[0]
        if percentile >= 100:
            return data[-1]
        index = (len(data) - 1) * (percentile / 100)
        lower = int(index)
        upper = min(lower + 1, len(data) - 1)
        weight = index - lower
        return round(data[lower] * (1 - weight) + data[upper] * weight, 2)

    def _launch_plan_cache_key(self, normalized_city: str) -> str:
        return f"city-expansion:launch:{normalized_city}"

    async def _load_launch_plan(self, normalized_city: str) -> CityLaunchResponse:
        cache_key = self._launch_plan_cache_key(normalized_city)
        cached = await self._redis.get(cache_key)
        if cached:
            try:
                payload = json.loads(cached)
                plan = [LaunchStep(**item) for item in payload.get("plan", [])]
                launched_at = datetime.fromisoformat(payload.get("launched_at"))
                return CityLaunchResponse(
                    city=self._title_case_city(normalized_city),
                    launched_at=launched_at,
                    plan=plan,
                    confidence=[
                        ConfidenceSignal(
                            metric="launch_plan", score=0.7, description="Cached launch plan"
                        )
                    ],
                    insights=[],
                    recommendations=[],
                )
            except Exception:  # pragma: no cover - defensive guard
                logger.exception(
                    "Failed to deserialize launch plan", extra={"city": normalized_city}
                )
        return await self.initialize_launch(normalized_city, CityLaunchRequest())
