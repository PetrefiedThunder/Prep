"""Domain service powering the review API surface."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from prep.cache import RedisProtocol
from prep.models.orm import (
    Booking,
    BookingStatus,
    Kitchen,
    Review,
    ReviewFlag,
    ReviewFlagStatus,
    ReviewPhoto,
    ReviewStatus,
    ReviewVote,
    User,
)

from .notifications import ReviewNotifier
from .schemas import (
    HostResponseUpdate,
    RatingAggregate,
    RatingBreakdown,
    ReviewFlagModel,
    ReviewFlagRequest,
    ReviewListResponse,
    ReviewModel,
    ReviewModerationRequest,
    ReviewPhotoModel,
    ReviewSubmissionRequest,
    ReviewVoteRequest,
    UserReviewListResponse,
)

logger = logging.getLogger(__name__)

DEFAULT_CACHE_TTL = 600
DEFAULT_SPAM_THRESHOLD = 0.75


def _coerce_breakdown(request: ReviewSubmissionRequest) -> RatingBreakdown:
    ratings = request.ratings
    if ratings is None:
        return RatingBreakdown(
            equipment=request.overall_rating,
            cleanliness=request.overall_rating,
            communication=request.overall_rating,
            value=request.overall_rating,
        )
    return ratings


def _calculate_spam_score(comment: str | None) -> float:
    """Return a naive spam score for a comment between 0 and 1."""

    if not comment:
        return 0.0

    lowered = comment.lower()
    score = 0.0
    if "http://" in lowered or "https://" in lowered:
        score += 0.4
    if any(keyword in lowered for keyword in {"buy now", "free money", "visit my blog"}):
        score += 0.4
    if len(comment) < 20:
        score += 0.1
    if any(lowered.count(char * 4) for char in {"!", "?", "$"}):
        score += 0.2
    return min(score, 1.0)


class ReviewService:
    """Coordinates review persistence, aggregation, and notifications."""

    def __init__(
        self,
        session: AsyncSession,
        redis_client: RedisProtocol,
        notifier: ReviewNotifier,
        *,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        spam_threshold: float = DEFAULT_SPAM_THRESHOLD,
    ) -> None:
        self._session = session
        self._redis = redis_client
        self._notifier = notifier
        self._cache_ttl = cache_ttl
        self._spam_threshold = spam_threshold

    async def submit_review(self, user: User, payload: ReviewSubmissionRequest) -> ReviewModel:
        booking = await self._session.get(
            Booking,
            payload.booking_id,
            options=(selectinload(Booking.kitchen),),
        )
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
        if booking.customer_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Cannot review this booking"
            )
        if booking.kitchen_id != payload.kitchen_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kitchen mismatch")
        if booking.status != BookingStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Booking not completed"
            )

        ratings = _coerce_breakdown(payload)
        spam_score = _calculate_spam_score(payload.comment)
        status_value = (
            ReviewStatus.APPROVED if spam_score < self._spam_threshold else ReviewStatus.PENDING
        )

        review = Review(
            booking_id=booking.id,
            kitchen_id=booking.kitchen_id,
            host_id=booking.host_id,
            customer_id=user.id,
            rating=payload.overall_rating,
            equipment_rating=ratings.equipment,
            cleanliness_rating=ratings.cleanliness,
            communication_rating=ratings.communication,
            value_rating=ratings.value,
            comment=payload.comment,
            status=status_value,
            spam_score=spam_score,
            moderated_at=datetime.now(UTC) if status_value == ReviewStatus.APPROVED else None,
            moderated_by=user.id if status_value == ReviewStatus.APPROVED else None,
        )

        self._session.add(review)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            logger.info("Duplicate review submission detected", exc_info=exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this booking",
            ) from exc

        await self._session.commit()
        await self._session.refresh(review)

        await self._refresh_rating_cache(booking.kitchen_id)

        if status_value == ReviewStatus.APPROVED:
            await self._notifier.notify_review_submitted(
                host_id=booking.host_id,
                review_id=review.id,
                kitchen_id=booking.kitchen_id,
            )

        return self._to_schema(review)

    async def add_photo(
        self, user: User, review_id: UUID, payload: ReviewPhotoCreate
    ) -> ReviewPhoto:
        review = await self._get_review(review_id)
        if review.customer_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to add photos"
            )

        photo = ReviewPhoto(review_id=review.id, url=str(payload.url), caption=payload.caption)
        self._session.add(photo)
        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(photo)
        return photo

    async def host_response(
        self, user: User, review_id: UUID, payload: HostResponseUpdate
    ) -> ReviewModel:
        review = await self._get_review(review_id)
        if review.host_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only the host may respond"
            )

        review.host_response = payload.response
        review.host_response_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(review)

        await self._notifier.notify_host_response(
            reviewer_id=review.customer_id,
            review_id=review.id,
            kitchen_id=review.kitchen_id,
        )
        return self._to_schema(review)

    async def list_kitchen_reviews(
        self, kitchen_id: UUID, requester: User | None
    ) -> ReviewListResponse:
        kitchen = await self._session.get(Kitchen, kitchen_id)
        if kitchen is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")

        aggregate = await self._get_cached_aggregate(kitchen_id)
        reviews = await self._fetch_reviews_for_kitchen(kitchen_id, requester)
        return ReviewListResponse(items=reviews, aggregate=aggregate)

    async def list_user_reviews(self, user_id: UUID) -> UserReviewListResponse:
        result = await self._session.execute(
            select(Review)
            .options(selectinload(Review.photos))
            .where(Review.customer_id == user_id)
            .order_by(Review.created_at.desc())
        )
        reviews = [self._to_schema(review) for review in result.scalars().all()]

        flags_result = await self._session.execute(
            select(ReviewFlag).where(
                and_(
                    ReviewFlag.reporter_id == user_id,
                    ReviewFlag.status == ReviewFlagStatus.OPEN,
                )
            )
        )
        pending_flags = [
            ReviewFlagModel.model_validate(flag) for flag in flags_result.scalars().all()
        ]
        return UserReviewListResponse(items=reviews, pending_flags=pending_flags)

    async def delete_review(self, review_id: UUID) -> None:
        review = await self._get_review(review_id)
        kitchen_id = review.kitchen_id
        await self._session.delete(review)
        await self._session.commit()
        await self._refresh_rating_cache(kitchen_id)

    async def vote_review(
        self, user: User, review_id: UUID, payload: ReviewVoteRequest
    ) -> ReviewModel:
        review = await self._get_review(review_id)
        if review.customer_id == user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot vote on own review"
            )

        try:
            vote = ReviewVote(review_id=review_id, user_id=user.id, is_helpful=payload.helpful)
            self._session.add(vote)
            await self._session.flush()
        except IntegrityError:
            result = await self._session.execute(
                select(ReviewVote).where(
                    ReviewVote.review_id == review_id, ReviewVote.user_id == user.id
                )
            )
            vote = result.scalar_one()
            vote.is_helpful = payload.helpful
            vote.updated_at = datetime.now(UTC)

        helpful_count_result = await self._session.execute(
            select(func.count())
            .select_from(ReviewVote)
            .where(ReviewVote.review_id == review_id, ReviewVote.is_helpful.is_(True))
        )
        review.helpful_count = helpful_count_result.scalar_one()
        await self._session.commit()
        await self._session.refresh(review)
        return self._to_schema(review)

    async def flag_review(
        self, user: User, review_id: UUID, payload: ReviewFlagRequest
    ) -> ReviewFlagModel:
        review = await self._get_review(review_id)
        flag = ReviewFlag(
            review_id=review.id,
            reporter_id=user.id,
            reason=payload.reason,
            notes=payload.notes,
        )
        self._session.add(flag)
        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(flag)

        await self._notifier.notify_review_flagged(
            reviewer_id=review.customer_id,
            review_id=review.id,
            reason=payload.reason,
        )
        return ReviewFlagModel.model_validate(flag)

    async def moderate_review(
        self, admin: User, review_id: UUID, payload: ReviewModerationRequest
    ) -> ReviewModel:
        review = await self._get_review(review_id)
        now = datetime.now(UTC)
        if payload.action == "approve":
            review.status = ReviewStatus.APPROVED
        else:
            review.status = ReviewStatus.REJECTED
        review.moderated_at = now
        review.moderated_by = admin.id

        for flag in review.flags:
            flag.status = (
                ReviewFlagStatus.RESOLVED
                if payload.action == "approve"
                else ReviewFlagStatus.REJECTED
            )
            flag.resolved_at = now
            flag.resolved_by = admin.id

        await self._session.commit()
        await self._session.refresh(review)
        await self._refresh_rating_cache(review.kitchen_id)

        await self._notifier.notify_review_moderated(
            reviewer_id=review.customer_id,
            review_id=review.id,
            status=review.status.value,
            notes=payload.notes,
        )
        return self._to_schema(review)

    async def _get_review(self, review_id: UUID) -> Review:
        review = await self._session.get(
            Review,
            review_id,
            options=(
                selectinload(Review.photos),
                selectinload(Review.flags),
                selectinload(Review.votes),
            ),
        )
        if review is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
        return review

    async def _fetch_reviews_for_kitchen(
        self, kitchen_id: UUID, requester: User | None
    ) -> list[ReviewModel]:
        conditions = [Review.kitchen_id == kitchen_id]
        if requester is None:
            conditions.append(Review.status == ReviewStatus.APPROVED)
        else:
            conditions.append(
                or_(
                    Review.status == ReviewStatus.APPROVED,
                    Review.customer_id == requester.id,
                    Review.host_id == requester.id,
                )
            )
        result = await self._session.execute(
            select(Review)
            .options(selectinload(Review.photos))
            .where(and_(*conditions))
            .order_by(Review.created_at.desc())
        )
        return [self._to_schema(review) for review in result.scalars().all()]

    async def _get_cached_aggregate(self, kitchen_id: UUID) -> RatingAggregate:
        cache_key = f"kitchen:ratings:{kitchen_id}"
        try:
            cached = await self._redis.get(cache_key)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception(
                "Failed to read rating aggregate cache", extra={"cache_key": cache_key}
            )
            cached = None
        if cached:
            try:
                payload = json.loads(cached)
                return RatingAggregate.model_validate(payload)
            except (json.JSONDecodeError, TypeError, ValueError):
                logger.warning("Invalid cached rating payload", extra={"cache_key": cache_key})
        aggregate = await self._calculate_aggregate(kitchen_id)
        await self._persist_aggregate(cache_key, aggregate)
        return aggregate

    async def _refresh_rating_cache(self, kitchen_id: UUID) -> None:
        cache_key = f"kitchen:ratings:{kitchen_id}"
        aggregate = await self._calculate_aggregate(kitchen_id)
        await self._persist_aggregate(cache_key, aggregate)

    async def _persist_aggregate(self, cache_key: str, aggregate: RatingAggregate) -> None:
        try:
            await self._redis.setex(cache_key, self._cache_ttl, aggregate.model_dump_json())
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to persist rating aggregate", extra={"cache_key": cache_key})

    async def _calculate_aggregate(self, kitchen_id: UUID) -> RatingAggregate:
        result = await self._session.execute(
            select(
                func.count(Review.id),
                func.avg(Review.rating),
                func.avg(Review.equipment_rating),
                func.avg(Review.cleanliness_rating),
                func.avg(Review.communication_rating),
                func.avg(Review.value_rating),
            ).where(Review.kitchen_id == kitchen_id, Review.status == ReviewStatus.APPROVED)
        )
        (
            total,
            avg_rating,
            avg_equipment,
            avg_cleanliness,
            avg_communication,
            avg_value,
        ) = result.one()
        return RatingAggregate(
            total_reviews=int(total or 0),
            average_rating=float(avg_rating or 0.0),
            average_equipment=float(avg_equipment or 0.0),
            average_cleanliness=float(avg_cleanliness or 0.0),
            average_communication=float(avg_communication or 0.0),
            average_value=float(avg_value or 0.0),
        )

    def _to_schema(self, review: Review) -> ReviewModel:
        ratings = RatingBreakdown(
            equipment=review.equipment_rating,
            cleanliness=review.cleanliness_rating,
            communication=review.communication_rating,
            value=review.value_rating,
        )
        photos = review.__dict__.get("photos")
        if photos is None:
            photos = []
        photo_models = [ReviewPhotoModel.model_validate(photo) for photo in photos]
        return ReviewModel(
            id=review.id,
            booking_id=review.booking_id,
            kitchen_id=review.kitchen_id,
            host_id=review.host_id,
            customer_id=review.customer_id,
            rating=review.rating,
            ratings=ratings,
            comment=review.comment,
            status=review.status,
            spam_score=review.spam_score,
            helpful_count=review.helpful_count,
            created_at=review.created_at,
            updated_at=review.updated_at,
            host_response=review.host_response,
            host_response_at=review.host_response_at,
            photos=photo_models,
        )


__all__ = ["ReviewService"]
