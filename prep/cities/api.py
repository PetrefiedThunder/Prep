"""FastAPI router exposing multi-city expansion tools."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from prep.auth import get_current_user, require_admin_role
from prep.cache import RedisProtocol, get_redis
from prep.database import get_db
from prep.matching.service import MatchingService

from .schemas import (
    AddressValidationRequest,
    AddressValidationResponse,
    BookingQuoteRequest,
    BookingQuoteResponse,
    CityCompetitionResponse,
    CityDemandForecastResponse,
    CityDemographicsResponse,
    CityLaunchRequest,
    CityLaunchResponse,
    CityMarketAnalyticsResponse,
    CityPromotionRequest,
    CityPromotionResponse,
    CityReadinessResponse,
    CityRegulationResponse,
    CityServiceZonesResponse,
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ComplianceTemplatesResponse,
    CurrencyDescriptor,
    CurrencyListResponse,
    CurrencyRatesResponse,
    PricingIntelResponse,
)
from .service import CityExpansionService

router = APIRouter(prefix="/api/v1", tags=["city-expansion"])


async def get_city_expansion_service(
    session=Depends(get_db),
    redis: RedisProtocol = Depends(get_redis),
) -> CityExpansionService:
    matching_service = MatchingService(session, redis)
    return CityExpansionService(session, redis, matching_service=matching_service)


@router.get("/cities/{city}/analytics", response_model=CityMarketAnalyticsResponse)
async def city_market_analytics(
    city: str,
    currency: str | None = Query(None, description="Target currency for monetary metrics"),
    current_admin=Depends(require_admin_role),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> CityMarketAnalyticsResponse:
    _ = current_admin
    return await service.get_city_analytics(city, currency=currency)


@router.get("/cities/{city}/competition", response_model=CityCompetitionResponse)
async def city_competition(
    city: str,
    currency: str | None = Query(None),
    current_admin=Depends(require_admin_role),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> CityCompetitionResponse:
    _ = current_admin
    return await service.get_city_competition(city, currency=currency)


@router.get("/cities/{city}/demand", response_model=CityDemandForecastResponse)
async def city_demand(
    city: str,
    currency: str | None = Query(None),
    current_admin=Depends(require_admin_role),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> CityDemandForecastResponse:
    _ = current_admin
    return await service.get_city_demand(city, currency=currency)


@router.get("/cities/{city}/pricing", response_model=PricingIntelResponse)
async def city_pricing(
    city: str,
    currency: str | None = Query(None),
    current_admin=Depends(require_admin_role),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> PricingIntelResponse:
    _ = current_admin
    return await service.get_city_pricing(city, currency=currency)


@router.get("/cities/{city}/regulations", response_model=CityRegulationResponse)
async def city_regulations(
    city: str,
    current_admin=Depends(require_admin_role),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> CityRegulationResponse:
    _ = current_admin
    return await service.get_city_regulations(city)


@router.post("/compliance/check", response_model=ComplianceCheckResponse)
async def compliance_check(
    payload: ComplianceCheckRequest,
    current_admin=Depends(require_admin_role),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> ComplianceCheckResponse:
    _ = current_admin
    return await service.check_compliance(payload)


@router.get("/compliance/templates", response_model=ComplianceTemplatesResponse)
async def compliance_templates(
    city: str | None = Query(None, description="Filter templates by city"),
    current_admin=Depends(require_admin_role),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> ComplianceTemplatesResponse:
    _ = current_admin
    return await service.get_compliance_templates(city)


@router.get("/currencies", response_model=CurrencyListResponse)
async def list_currencies(
    current_admin=Depends(require_admin_role),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> CurrencyListResponse:
    _ = current_admin
    currencies, confidence = await service.list_currencies()
    return CurrencyListResponse(
        currencies=[CurrencyDescriptor(**currency) for currency in currencies],
        confidence=confidence,
    )


@router.get("/currencies/rates", response_model=CurrencyRatesResponse)
async def currency_rates(
    base_currency: str | None = Query(None),
    current_admin=Depends(require_admin_role),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> CurrencyRatesResponse:
    _ = current_admin
    base, rates, timestamp = await service.get_currency_rates(base_currency)
    return CurrencyRatesResponse(base_currency=base, rates=rates, timestamp=timestamp)


@router.post("/bookings/quote", response_model=BookingQuoteResponse)
async def booking_quote(
    payload: BookingQuoteRequest,
    current_user=Depends(get_current_user),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> BookingQuoteResponse:
    _ = current_user
    return await service.quote_booking(payload)


@router.post("/locations/validate", response_model=AddressValidationResponse)
async def validate_address(
    payload: AddressValidationRequest,
    current_admin=Depends(require_admin_role),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> AddressValidationResponse:
    _ = current_admin
    return await service.validate_address(payload)


@router.get("/locations/{city}/zones", response_model=CityServiceZonesResponse)
async def city_zones(
    city: str,
    current_admin=Depends(require_admin_role),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> CityServiceZonesResponse:
    _ = current_admin
    return await service.get_service_zones(city)


@router.get("/locations/{city}/demographics", response_model=CityDemographicsResponse)
async def city_demographics(
    city: str,
    current_admin=Depends(require_admin_role),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> CityDemographicsResponse:
    _ = current_admin
    return await service.get_demographics(city)


@router.post("/cities/{city}/launch", response_model=CityLaunchResponse)
async def launch_city(
    city: str,
    payload: CityLaunchRequest,
    current_admin=Depends(require_admin_role),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> CityLaunchResponse:
    _ = current_admin
    return await service.initialize_launch(city, payload)


@router.get("/cities/{city}/readiness", response_model=CityReadinessResponse)
async def launch_readiness(
    city: str,
    current_admin=Depends(require_admin_role),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> CityReadinessResponse:
    _ = current_admin
    return await service.get_launch_readiness(city)


@router.post("/cities/{city}/promote", response_model=CityPromotionResponse)
async def promote_city(
    city: str,
    payload: CityPromotionRequest,
    current_admin=Depends(require_admin_role),
    service: CityExpansionService = Depends(get_city_expansion_service),
) -> CityPromotionResponse:
    _ = current_admin
    return await service.promote_city(city, payload)


__all__ = ["router"]
