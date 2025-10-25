"""FastAPI router exposing the Prep review and rating API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from prep.auth import get_current_admin, get_current_user
from prep.cache import RedisProtocol, get_redis
from prep.database import get_db

from .notifications import ReviewNotifier
from .schemas import (
    HostResponseUpdate,
    ReviewFlagModel,
    ReviewFlagRequest,
    ReviewListResponse,
    ReviewModerationRequest,
    ReviewModel,
    ReviewPhotoCreate,
    ReviewPhotoModel,
    ReviewSubmissionRequest,
    ReviewVoteRequest,
    UserReviewListResponse,
)
from .service import ReviewService

router = APIRouter(prefix="/api/v1", tags=["reviews"])


async def get_review_notifier() -> ReviewNotifier:
    """Provide the default review notifier instance."""

    return ReviewNotifier()


async def get_review_service(
    session: AsyncSession = Depends(get_db),
    redis: RedisProtocol = Depends(get_redis),
    notifier: ReviewNotifier = Depends(get_review_notifier),
) -> ReviewService:
    """Instantiate the review domain service."""

    return ReviewService(session, redis, notifier)


@router.post("/reviews", response_model=ReviewModel, status_code=status.HTTP_201_CREATED)
async def submit_review(
    payload: ReviewSubmissionRequest,
    current_user=Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewModel:
    """Submit a new review for a completed booking."""

    return await service.submit_review(current_user, payload)


@router.post(
    "/reviews/{review_id}/photos",
    response_model=ReviewPhotoModel,
    status_code=status.HTTP_201_CREATED,
)
async def upload_review_photo(
    review_id: UUID,
    payload: ReviewPhotoCreate,
    current_user=Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewPhotoModel:
    """Attach an existing photo asset to a review."""

    photo = await service.add_photo(current_user, review_id, payload)
    return ReviewPhotoModel.model_validate(photo)


@router.put("/reviews/{review_id}", response_model=ReviewModel)
async def respond_to_review(
    review_id: UUID,
    payload: HostResponseUpdate,
    current_user=Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewModel:
    """Allow the host to respond to a review."""

    return await service.host_response(current_user, review_id, payload)


@router.get("/kitchens/{kitchen_id}/reviews", response_model=ReviewListResponse)
async def list_kitchen_reviews(
    kitchen_id: UUID,
    current_user=Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewListResponse:
    """Return public reviews for a kitchen including aggregates."""

    return await service.list_kitchen_reviews(kitchen_id, current_user)


@router.get("/users/{user_id}/reviews", response_model=UserReviewListResponse)
async def list_user_reviews(
    user_id: UUID,
    current_user=Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> UserReviewListResponse:
    """Return the authenticated user's review history."""

    if current_user.id != user_id and not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return await service.list_user_reviews(user_id)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: UUID,
    current_admin=Depends(get_current_admin),
    service: ReviewService = Depends(get_review_service),
) -> Response:
    """Delete a review as part of moderation."""

    _ = current_admin
    await service.delete_review(review_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reviews/{review_id}/vote", response_model=ReviewModel)
async def vote_review_helpful(
    review_id: UUID,
    payload: ReviewVoteRequest,
    current_user=Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewModel:
    """Register a helpfulness vote for a review."""

    return await service.vote_review(current_user, review_id, payload)


@router.post("/reviews/{review_id}/flag", response_model=ReviewFlagModel, status_code=status.HTTP_201_CREATED)
async def flag_review(
    review_id: UUID,
    payload: ReviewFlagRequest,
    current_user=Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewFlagModel:
    """Flag a review for moderator attention."""

    return await service.flag_review(current_user, review_id, payload)


@router.post("/reviews/{review_id}/moderate", response_model=ReviewModel)
async def moderate_review(
    review_id: UUID,
    payload: ReviewModerationRequest,
    current_admin=Depends(get_current_admin),
    service: ReviewService = Depends(get_review_service),
) -> ReviewModel:
    """Approve or reject a review as an administrator."""

    return await service.moderate_review(current_admin, review_id, payload)


__all__ = ["router", "get_review_service", "get_review_notifier"]
