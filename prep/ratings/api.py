"""FastAPI router exposing external ratings integrations."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from prep.auth import get_current_user, require_admin_role
from prep.cache import RedisProtocol, get_redis
from prep.database import get_db

from .clients import ExternalAPIError
from .schemas import (
    ExternalBusinessDetails,
    ExternalBusinessSearchResponse,
    ExternalRatingSyncRequest,
    ExternalRatingSyncResponse,
    ExternalReviewListResponse,
    KitchenRatingHistoryResponse,
    KitchenRatingResponse,
    SentimentAnalysisRequest,
    SentimentAnalysisResponse,
    SentimentTrendResponse,
)
from .service import RatingIntegrationService

router = APIRouter(prefix="/api/v1", tags=["ratings"])


async def get_rating_service(
    session=Depends(get_db),
    redis: RedisProtocol = Depends(get_redis),
) -> RatingIntegrationService:
    return RatingIntegrationService(session, redis)


def _external_error_to_http(exc: ExternalAPIError) -> HTTPException:
    status_code = exc.status_code or status.HTTP_502_BAD_GATEWAY
    status_code = max(400, min(status_code, 599))
    return HTTPException(
        status_code=status_code,
        detail={
            "provider": exc.provider,
            "message": str(exc),
        },
    )


@router.get(
    "/ratings/yelp/businesses",
    response_model=ExternalBusinessSearchResponse,
)
async def search_yelp_businesses(
    term: str = Query(..., min_length=1),
    location: str | None = Query(None, min_length=2),
    latitude: float | None = Query(None),
    longitude: float | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    current_user=Depends(get_current_user),
    service: RatingIntegrationService = Depends(get_rating_service),
) -> ExternalBusinessSearchResponse:
    _ = current_user
    try:
        return await service.search_yelp_businesses(
            term=term,
            location=location,
            latitude=latitude,
            longitude=longitude,
            limit=limit,
        )
    except ExternalAPIError as exc:
        raise _external_error_to_http(exc) from exc


@router.get(
    "/ratings/yelp/businesses/{business_id}",
    response_model=ExternalBusinessDetails,
)
async def get_yelp_business(
    business_id: str,
    current_user=Depends(get_current_user),
    service: RatingIntegrationService = Depends(get_rating_service),
) -> ExternalBusinessDetails:
    _ = current_user
    try:
        return await service.get_yelp_business(business_id)
    except ExternalAPIError as exc:
        raise _external_error_to_http(exc) from exc


@router.get(
    "/ratings/yelp/businesses/{business_id}/reviews",
    response_model=ExternalReviewListResponse,
)
async def get_yelp_reviews(
    business_id: str,
    current_user=Depends(get_current_user),
    service: RatingIntegrationService = Depends(get_rating_service),
) -> ExternalReviewListResponse:
    _ = current_user
    try:
        return await service.get_yelp_reviews(business_id)
    except ExternalAPIError as exc:
        raise _external_error_to_http(exc) from exc


@router.get(
    "/ratings/google/places",
    response_model=ExternalBusinessSearchResponse,
)
async def search_google_places(
    query: str = Query(..., min_length=1),
    location: str | None = Query(None, min_length=2),
    limit: int = Query(20, ge=1, le=50),
    current_user=Depends(get_current_user),
    service: RatingIntegrationService = Depends(get_rating_service),
) -> ExternalBusinessSearchResponse:
    _ = current_user
    try:
        return await service.search_google_places(query=query, location=location, limit=limit)
    except ExternalAPIError as exc:
        raise _external_error_to_http(exc) from exc


@router.get(
    "/ratings/google/places/{place_id}",
    response_model=ExternalBusinessDetails,
)
async def get_google_place(
    place_id: str,
    current_user=Depends(get_current_user),
    service: RatingIntegrationService = Depends(get_rating_service),
) -> ExternalBusinessDetails:
    _ = current_user
    try:
        return await service.get_google_place(place_id)
    except ExternalAPIError as exc:
        raise _external_error_to_http(exc) from exc


@router.get(
    "/ratings/google/places/{place_id}/reviews",
    response_model=ExternalReviewListResponse,
)
async def get_google_reviews(
    place_id: str,
    current_user=Depends(get_current_user),
    service: RatingIntegrationService = Depends(get_rating_service),
) -> ExternalReviewListResponse:
    _ = current_user
    try:
        return await service.get_google_reviews(place_id)
    except ExternalAPIError as exc:
        raise _external_error_to_http(exc) from exc


@router.post(
    "/ratings/sync",
    response_model=ExternalRatingSyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def sync_external_ratings(
    payload: ExternalRatingSyncRequest,
    current_admin=Depends(require_admin_role),
    service: RatingIntegrationService = Depends(get_rating_service),
) -> ExternalRatingSyncResponse:
    _ = current_admin
    return await service.sync_external_ratings(payload)


@router.get(
    "/kitchens/{kitchen_id}/ratings",
    response_model=KitchenRatingResponse,
)
async def get_kitchen_ratings(
    kitchen_id: UUID,
    current_user=Depends(get_current_user),
    service: RatingIntegrationService = Depends(get_rating_service),
) -> KitchenRatingResponse:
    _ = current_user
    return await service.get_kitchen_ratings(kitchen_id)


@router.get(
    "/kitchens/{kitchen_id}/ratings/history",
    response_model=KitchenRatingHistoryResponse,
)
async def get_kitchen_rating_history(
    kitchen_id: UUID,
    current_user=Depends(get_current_user),
    service: RatingIntegrationService = Depends(get_rating_service),
) -> KitchenRatingHistoryResponse:
    _ = current_user
    return await service.get_rating_history(kitchen_id)


@router.post(
    "/ratings/analyze",
    response_model=SentimentAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_ratings_sentiment(
    payload: SentimentAnalysisRequest,
    current_admin=Depends(require_admin_role),
    service: RatingIntegrationService = Depends(get_rating_service),
) -> SentimentAnalysisResponse:
    _ = current_admin
    try:
        return await service.analyze_sentiment(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/ratings/sentiment/trends",
    response_model=SentimentTrendResponse,
)
async def get_sentiment_trends(
    kitchen_id: UUID | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    current_admin=Depends(require_admin_role),
    service: RatingIntegrationService = Depends(get_rating_service),
) -> SentimentTrendResponse:
    _ = current_admin
    return await service.get_sentiment_trends(kitchen_id=kitchen_id, source=source, limit=limit)


__all__ = ["router", "get_rating_service"]
