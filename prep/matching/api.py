"""FastAPI router exposing smart matching endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from prep.auth import require_admin_role, get_current_user
from prep.cache import RedisProtocol, get_redis
from prep.database import get_db
from prep.models.orm import User

from .schemas import (
    ExternalRatingSyncRequest,
    ExternalRatingSyncResponse,
    KitchenMatchRequest,
    KitchenRatingResponse,
    MatchResponse,
    PreferenceSettings,
    UserPreferenceModel,
)
from .service import MatchingService

router = APIRouter(prefix="/api/v1", tags=["matching"])


async def get_matching_service(
    session=Depends(get_db),
    redis: RedisProtocol = Depends(get_redis),
) -> MatchingService:
    """Provide a configured MatchingService instance."""

    return MatchingService(session, redis)


@router.post("/match/preferences", response_model=UserPreferenceModel)
async def update_preferences(
    payload: PreferenceSettings,
    current_user: User = Depends(get_current_user),
    service: MatchingService = Depends(get_matching_service),
) -> UserPreferenceModel:
    """Persist matching preferences for the authenticated user."""

    return await service.set_preferences(current_user, payload)


@router.post("/match/kitchens", response_model=MatchResponse)
async def match_kitchens(
    payload: KitchenMatchRequest,
    current_user: User = Depends(get_current_user),
    service: MatchingService = Depends(get_matching_service),
) -> MatchResponse:
    """Return kitchen recommendations tailored to the user."""

    return await service.match_kitchens(current_user, payload)


@router.get("/users/{user_id}/recommendations", response_model=MatchResponse)
async def user_recommendations(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MatchingService = Depends(get_matching_service),
) -> MatchResponse:
    """Fetch cached or freshly computed recommendations for a user."""

    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return await service.get_recommendations(user_id)


@router.get("/kitchens/{kitchen_id}/ratings", response_model=KitchenRatingResponse)
async def kitchen_ratings(
    kitchen_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MatchingService = Depends(get_matching_service),
) -> KitchenRatingResponse:
    """Return aggregated internal and external ratings for a kitchen."""

    _ = current_user
    return await service.get_kitchen_ratings(kitchen_id)


@router.post("/ratings/sync", response_model=ExternalRatingSyncResponse)
async def sync_ratings(
    payload: ExternalRatingSyncRequest,
    current_admin: User = Depends(require_admin_role),
    service: MatchingService = Depends(get_matching_service),
) -> ExternalRatingSyncResponse:
    """Sync external rating data; restricted to admin users."""

    _ = current_admin
    return await service.sync_external_ratings(payload)


__all__ = ["router"]
