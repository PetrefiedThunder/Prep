"""Domain service orchestrating external rating integrations."""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.cache import RedisProtocol
from prep.models.orm import (
    Kitchen,
    KitchenExternalRating,
    KitchenRatingHistory,
    KitchenSentimentTrend,
    Review,
    ReviewStatus,
)

from .clients import ExternalAPIError, GooglePlacesClient, YelpAPIClient
from .schemas import (
    ExternalBusiness,
    ExternalBusinessDetails,
    ExternalBusinessReview,
    ExternalBusinessSearchResponse,
    ExternalRatingModel,
    ExternalRatingSyncRequest,
    ExternalRatingSyncResponse,
    ExternalReviewListResponse,
    KitchenRatingHistoryResponse,
    KitchenRatingResponse,
    RatingTrendPoint,
    SentimentAnalysisRequest,
    SentimentAnalysisResponse,
    SentimentTrendPoint,
    SentimentTrendResponse,
)

logger = logging.getLogger(__name__)

_POSITIVE_TERMS = {
    "amazing",
    "awesome",
    "clean",
    "excellent",
    "friendly",
    "great",
    "impeccable",
    "outstanding",
    "perfect",
    "phenomenal",
    "pleasant",
    "professional",
    "spotless",
    "stellar",
    "wonderful",
}

_NEGATIVE_TERMS = {
    "awful",
    "bad",
    "dirty",
    "disappointing",
    "horrible",
    "late",
    "messy",
    "poor",
    "rude",
    "slow",
    "terrible",
    "unprofessional",
    "unsafe",
    "unreliable",
}

_STOPWORDS = {
    "the",
    "and",
    "a",
    "of",
    "to",
    "for",
    "in",
    "on",
    "with",
    "at",
    "it",
    "was",
    "is",
    "are",
    "we",
    "they",
    "them",
}


class RatingIntegrationService:
    """Coordinates communication with external rating providers."""

    CACHE_TTL_SECONDS = 900
    SENTIMENT_TTL_SECONDS = 3600

    def __init__(
        self,
        session: AsyncSession,
        redis: RedisProtocol,
        *,
        yelp_client: YelpAPIClient | None = None,
        google_client: GooglePlacesClient | None = None,
    ) -> None:
        self.session = session
        self.redis = redis
        self.yelp_client = yelp_client or YelpAPIClient()
        self.google_client = google_client or GooglePlacesClient()

    # ------------------------------------------------------------------
    # Yelp integration
    # ------------------------------------------------------------------
    async def search_yelp_businesses(
        self,
        *,
        term: str,
        location: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        limit: int = 20,
    ) -> ExternalBusinessSearchResponse:
        cache_key = self._cache_key(
            "yelp",
            "search",
            term=term,
            location=location,
            latitude=latitude,
            longitude=longitude,
            limit=limit,
        )
        cached = await self._get_cached_model(cache_key, ExternalBusinessSearchResponse)
        if cached is not None:
            return cached

        try:
            response = await self.yelp_client.search_businesses(
                term=term,
                location=location,
                latitude=latitude,
                longitude=longitude,
                limit=limit,
            )
        except ExternalAPIError as exc:
            logger.info(
                "Falling back to local Yelp search results",
                exc_info=None,
                extra={"reason": str(exc)},
            )
            response = await self._fallback_business_search(
                provider="yelp",
                term=term,
                location=location,
                limit=limit,
            )
        else:
            await self._set_cached_model(cache_key, response)
            return response

        await self._set_cached_model(cache_key, response, ttl=self.CACHE_TTL_SECONDS // 2)
        return response

    async def get_yelp_business(self, business_id: str) -> ExternalBusinessDetails:
        cache_key = self._cache_key("yelp", "business", business_id=business_id)
        cached = await self._get_cached_model(cache_key, ExternalBusinessDetails)
        if cached is not None:
            return cached

        try:
            response = await self.yelp_client.get_business(business_id)
        except ExternalAPIError as exc:
            logger.info("Falling back to local Yelp business data", extra={"reason": str(exc)})
            response = await self._fallback_business_details("yelp", business_id)
        else:
            await self._set_cached_model(cache_key, response)
            return response

        await self._set_cached_model(cache_key, response, ttl=self.CACHE_TTL_SECONDS // 2)
        return response

    async def get_yelp_reviews(self, business_id: str) -> ExternalReviewListResponse:
        cache_key = self._cache_key("yelp", "reviews", business_id=business_id)
        cached = await self._get_cached_model(cache_key, ExternalReviewListResponse)
        if cached is not None:
            return cached

        try:
            response = await self.yelp_client.get_reviews(business_id)
        except ExternalAPIError as exc:
            logger.info("Falling back to local Yelp reviews", extra={"reason": str(exc)})
            response = await self._fallback_reviews("yelp", business_id)
        else:
            await self._set_cached_model(cache_key, response)
            return response

        await self._set_cached_model(cache_key, response, ttl=self.CACHE_TTL_SECONDS // 2)
        return response

    # ------------------------------------------------------------------
    # Google Places integration
    # ------------------------------------------------------------------
    async def search_google_places(
        self,
        *,
        query: str,
        location: str | None = None,
        limit: int = 20,
    ) -> ExternalBusinessSearchResponse:
        cache_key = self._cache_key(
            "google",
            "search",
            query=query,
            location=location,
            limit=limit,
        )
        cached = await self._get_cached_model(cache_key, ExternalBusinessSearchResponse)
        if cached is not None:
            return cached

        try:
            response = await self.google_client.search_places(
                query=query, location=location, limit=limit
            )
        except ExternalAPIError as exc:
            logger.info("Falling back to local Google Places search", extra={"reason": str(exc)})
            response = await self._fallback_business_search(
                provider="google",
                term=query,
                location=location,
                limit=limit,
            )
        else:
            await self._set_cached_model(cache_key, response)
            return response

        await self._set_cached_model(cache_key, response, ttl=self.CACHE_TTL_SECONDS // 2)
        return response

    async def get_google_place(self, place_id: str) -> ExternalBusinessDetails:
        cache_key = self._cache_key("google", "business", place_id=place_id)
        cached = await self._get_cached_model(cache_key, ExternalBusinessDetails)
        if cached is not None:
            return cached

        try:
            response = await self.google_client.get_place(place_id)
        except ExternalAPIError as exc:
            logger.info("Falling back to local Google place details", extra={"reason": str(exc)})
            response = await self._fallback_business_details("google", place_id)
        else:
            await self._set_cached_model(cache_key, response)
            return response

        await self._set_cached_model(cache_key, response, ttl=self.CACHE_TTL_SECONDS // 2)
        return response

    async def get_google_reviews(self, place_id: str) -> ExternalReviewListResponse:
        cache_key = self._cache_key("google", "reviews", place_id=place_id)
        cached = await self._get_cached_model(cache_key, ExternalReviewListResponse)
        if cached is not None:
            return cached

        try:
            response = await self.google_client.get_reviews(place_id)
        except ExternalAPIError as exc:
            logger.info("Falling back to local Google reviews", extra={"reason": str(exc)})
            response = await self._fallback_reviews("google", place_id)
        else:
            await self._set_cached_model(cache_key, response)
            return response

        await self._set_cached_model(cache_key, response, ttl=self.CACHE_TTL_SECONDS // 2)
        return response

    # ------------------------------------------------------------------
    # Rating aggregation
    # ------------------------------------------------------------------
    async def sync_external_ratings(
        self, payload: ExternalRatingSyncRequest
    ) -> ExternalRatingSyncResponse:
        updated_sources: list[ExternalRatingModel] = []
        now = datetime.now(UTC)
        dirty_kitchens: set[UUID] = set()

        for entry in payload.sources:
            normalized_rating = self._normalize_rating(entry.rating, entry.rating_scale)
            stmt: Select[KitchenExternalRating] = select(KitchenExternalRating).where(
                and_(
                    KitchenExternalRating.kitchen_id == entry.kitchen_id,
                    KitchenExternalRating.source == entry.source,
                )
            )
            existing = (await self.session.execute(stmt)).scalar_one_or_none()

            if existing is not None:
                existing.rating = entry.rating
                existing.rating_scale = entry.rating_scale
                existing.rating_count = entry.rating_count
                existing.normalized_rating = normalized_rating
                existing.url = str(entry.url) if entry.url else None
                details = existing.details or {}
                details.update(entry.metadata)
                existing.details = details
                existing.last_synced_at = now
                record = existing
            else:
                record = KitchenExternalRating(
                    kitchen_id=entry.kitchen_id,
                    source=entry.source,
                    rating=entry.rating,
                    rating_scale=entry.rating_scale,
                    rating_count=entry.rating_count,
                    normalized_rating=normalized_rating,
                    url=str(entry.url) if entry.url else None,
                    details=entry.metadata,
                    last_synced_at=now,
                )
                self.session.add(record)

            dirty_kitchens.add(record.kitchen_id)
            await self._record_history(record, captured_at=now)

            updated_sources.append(
                ExternalRatingModel(
                    source=record.source,
                    rating=record.rating,
                    rating_scale=record.rating_scale,
                    rating_count=record.rating_count,
                    normalized_rating=record.normalized_rating,
                    url=record.url,
                    synced_at=record.last_synced_at,
                    metadata=record.details or {},
                )
            )

        await self.session.commit()
        for kitchen_id in dirty_kitchens:
            await self._invalidate_cache(kitchen_id)

        return ExternalRatingSyncResponse(updated=len(updated_sources), sources=updated_sources)

    async def get_kitchen_ratings(self, kitchen_id: UUID) -> KitchenRatingResponse:
        cache_key = self._cache_key("ratings", "kitchen", kitchen_id=str(kitchen_id))
        cached = await self._get_cached_model(cache_key, KitchenRatingResponse)
        if cached is not None:
            return cached

        rating_map = await self.get_rating_map([kitchen_id])
        response = rating_map.get(
            kitchen_id,
            KitchenRatingResponse(
                kitchen_id=kitchen_id,
                internal_average=None,
                internal_count=0,
                external_sources=[],
                normalized_score=None,
                external_count=0,
            ),
        )
        await self._set_cached_model(cache_key, response)
        return response

    async def get_rating_map(
        self, kitchen_ids: Sequence[UUID]
    ) -> dict[UUID, KitchenRatingResponse]:
        if not kitchen_ids:
            return {}

        review_stmt = (
            select(
                Review.kitchen_id,
                func.avg(Review.rating).label("avg_rating"),
                func.count(Review.id).label("count"),
            )
            .where(Review.kitchen_id.in_(kitchen_ids))
            .where(Review.status == ReviewStatus.APPROVED)
            .group_by(Review.kitchen_id)
        )
        review_rows = await self.session.execute(review_stmt)
        averages: dict[UUID, tuple[float | None, int]] = {}
        for row in review_rows:
            averages[row.kitchen_id] = (
                float(row.avg_rating) if row.avg_rating is not None else None,
                int(row.count or 0),
            )

        external_stmt: Select[KitchenExternalRating] = select(KitchenExternalRating).where(
            KitchenExternalRating.kitchen_id.in_(kitchen_ids)
        )
        external_rows = await self.session.execute(external_stmt)
        buckets: dict[UUID, list[ExternalRatingModel]] = defaultdict(list)
        external_counts: dict[UUID, int] = defaultdict(int)
        for rating in external_rows.scalars():
            normalized = rating.normalized_rating
            if normalized is None:
                normalized = self._normalize_rating(rating.rating, rating.rating_scale)
                rating.normalized_rating = normalized
            model = ExternalRatingModel(
                source=rating.source,
                rating=rating.rating,
                rating_scale=rating.rating_scale,
                rating_count=rating.rating_count,
                normalized_rating=normalized,
                url=rating.url,
                synced_at=rating.last_synced_at,
                metadata=rating.details or {},
            )
            buckets[rating.kitchen_id].append(model)
            if rating.rating_count:
                external_counts[rating.kitchen_id] += int(rating.rating_count)

        results: dict[UUID, KitchenRatingResponse] = {}
        for kitchen_id in kitchen_ids:
            internal_avg, internal_count = averages.get(kitchen_id, (None, 0))
            sources = buckets.get(kitchen_id, [])
            normalized_score = self._calculate_normalized_score(
                internal_avg, internal_count, sources
            )
            response = KitchenRatingResponse(
                kitchen_id=kitchen_id,
                internal_average=internal_avg,
                internal_count=internal_count,
                external_sources=sources,
                normalized_score=normalized_score,
                external_count=external_counts.get(kitchen_id, 0),
            )
            results[kitchen_id] = response
        return results

    async def get_rating_history(self, kitchen_id: UUID) -> KitchenRatingHistoryResponse:
        cache_key = self._cache_key("ratings", "history", kitchen_id=str(kitchen_id))
        cached = await self._get_cached_model(cache_key, KitchenRatingHistoryResponse)
        if cached is not None:
            return cached

        stmt = (
            select(KitchenRatingHistory)
            .where(KitchenRatingHistory.kitchen_id == kitchen_id)
            .order_by(KitchenRatingHistory.captured_at.desc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        points = [
            RatingTrendPoint(
                source=row.source,
                rating=row.rating,
                rating_scale=row.rating_scale,
                rating_count=row.rating_count,
                normalized_rating=row.normalized_rating,
                captured_at=row.captured_at,
                metadata=row.context or {},
            )
            for row in rows
        ]
        response = KitchenRatingHistoryResponse(kitchen_id=kitchen_id, points=points)
        await self._set_cached_model(cache_key, response, ttl=self.CACHE_TTL_SECONDS // 2)
        return response

    # ------------------------------------------------------------------
    # Sentiment analysis
    # ------------------------------------------------------------------
    async def analyze_sentiment(
        self, payload: SentimentAnalysisRequest
    ) -> SentimentAnalysisResponse:
        if not payload.reviews:
            raise ValueError("At least one review is required for sentiment analysis")

        now = datetime.now(UTC)
        scores: list[float] = []
        labels: list[float] = []
        tokens: list[str] = []
        window_start = now
        window_end = now

        for review in payload.reviews:
            score = self._score_text(review.text)
            if review.rating is not None:
                score = (score + (review.rating / 5) * 0.5) / 1.5
            scores.append(score)
            labels.append(score)
            window_start = min(window_start, review.created_at or now)
            window_end = max(window_end, review.created_at or now)
            tokens.extend(self._tokenize(review.text))

        average_score = sum(scores) / len(scores)
        positive = sum(1 for value in labels if value >= 0.25)
        negative = sum(1 for value in labels if value <= -0.25)
        len(labels) - positive - negative
        positive_ratio = positive / len(labels)
        negative_ratio = negative / len(labels)
        neutral_ratio = max(0.0, 1.0 - positive_ratio - negative_ratio)

        keywords = [token for token, _ in Counter(tokens).most_common(10)]
        label = (
            "positive"
            if average_score >= 0.25
            else "negative"
            if average_score <= -0.25
            else "neutral"
        )

        response = SentimentAnalysisResponse(
            kitchen_id=payload.kitchen_id,
            source=payload.source,
            average_score=average_score,
            label=label,
            review_count=len(scores),
            positive_ratio=positive_ratio,
            neutral_ratio=neutral_ratio,
            negative_ratio=negative_ratio,
            keywords=keywords,
            generated_at=now,
        )

        entry = KitchenSentimentTrend(
            kitchen_id=payload.kitchen_id,
            source=payload.source,
            window_start=window_start,
            window_end=window_end,
            average_score=average_score,
            positive_ratio=positive_ratio,
            neutral_ratio=neutral_ratio,
            negative_ratio=negative_ratio,
            sample_size=len(scores),
            context={"keywords": keywords},
        )
        self.session.add(entry)
        await self.session.commit()

        cache_key = self._cache_key(
            "sentiment", "latest", kitchen_id=str(payload.kitchen_id), source=payload.source
        )
        await self._set_cached_model(cache_key, response, ttl=self.SENTIMENT_TTL_SECONDS)
        return response

    async def get_sentiment_trends(
        self,
        *,
        kitchen_id: UUID | None = None,
        source: str | None = None,
        limit: int = 50,
    ) -> SentimentTrendResponse:
        cache_key = self._cache_key(
            "sentiment",
            "trends",
            kitchen_id=str(kitchen_id) if kitchen_id else None,
            source=source,
            limit=limit,
        )
        cached = await self._get_cached_model(cache_key, SentimentTrendResponse)
        if cached is not None:
            return cached

        stmt = select(KitchenSentimentTrend)
        if kitchen_id is not None:
            stmt = stmt.where(KitchenSentimentTrend.kitchen_id == kitchen_id)
        if source is not None:
            stmt = stmt.where(KitchenSentimentTrend.source == source)
        stmt = stmt.order_by(KitchenSentimentTrend.window_start.desc()).limit(limit)
        rows = (await self.session.execute(stmt)).scalars().all()
        points = [
            SentimentTrendPoint(
                kitchen_id=row.kitchen_id,
                source=row.source,
                window_start=row.window_start,
                window_end=row.window_end,
                average_score=row.average_score,
                positive_ratio=row.positive_ratio,
                neutral_ratio=row.neutral_ratio,
                negative_ratio=row.negative_ratio,
                sample_size=row.sample_size,
                metadata=row.context or {},
            )
            for row in reversed(rows)
        ]
        response = SentimentTrendResponse(
            kitchen_id=kitchen_id,
            source=source,
            points=points,
            generated_at=datetime.now(UTC),
        )
        await self._set_cached_model(cache_key, response, ttl=self.SENTIMENT_TTL_SECONDS)
        return response

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _fallback_business_search(
        self,
        *,
        provider: str,
        term: str,
        location: str | None,
        limit: int,
    ) -> ExternalBusinessSearchResponse:
        stmt = select(Kitchen).where(Kitchen.published.is_(True))
        if term:
            pattern = f"%{term.lower()}%"
            stmt = stmt.where(func.lower(Kitchen.name).like(pattern))
        if location:
            pattern = f"%{location.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Kitchen.city).like(pattern),
                    func.lower(Kitchen.state).like(pattern),
                )
            )
        stmt = stmt.order_by(Kitchen.trust_score.desc().nullslast()).limit(limit)
        kitchens = (await self.session.execute(stmt)).scalars().all()
        rating_map = await self.get_rating_map([kitchen.id for kitchen in kitchens])
        businesses: list[ExternalBusiness] = []
        for kitchen in kitchens:
            ratings = rating_map.get(kitchen.id)
            if ratings is None:
                ratings = KitchenRatingResponse(
                    kitchen_id=kitchen.id,
                    internal_average=None,
                    internal_count=0,
                    external_sources=[],
                    normalized_score=None,
                    external_count=0,
                )
            source_model = self._select_external_source(ratings, provider)
            metadata = {"kitchen_id": str(kitchen.id)}
            if source_model is not None:
                metadata.update(source_model.metadata)
            businesses.append(
                ExternalBusiness(
                    id=str(metadata.get("id") or metadata.get("place_id") or kitchen.id),
                    name=kitchen.name,
                    source=provider,
                    url=source_model.url if source_model else None,
                    phone=None,
                    address=[line for line in [kitchen.city, kitchen.state] if line],
                    city=kitchen.city,
                    state=kitchen.state,
                    postal_code=None,
                    country=None,
                    latitude=None,
                    longitude=None,
                    rating=ratings.normalized_score,
                    review_count=ratings.external_count or ratings.internal_count,
                    price=None,
                    categories=[],
                    metadata=metadata,
                )
            )
        context = {"fallback": True, "total_kitchens": len(kitchens)}
        return ExternalBusinessSearchResponse(
            businesses=businesses, total=len(businesses), context=context
        )

    async def _fallback_business_details(
        self, provider: str, external_id: str
    ) -> ExternalBusinessDetails:
        rating = await self._lookup_rating_by_external_id(provider, external_id)
        if rating is None:
            raise ExternalAPIError(provider, f"No cached business found for {external_id}")
        kitchen = await self.session.get(Kitchen, rating.kitchen_id)
        if kitchen is None:
            raise ExternalAPIError(provider, f"Kitchen for {external_id} is unavailable")
        ratings = (await self.get_rating_map([kitchen.id])).get(kitchen.id)
        metadata = rating.details or {}
        business = ExternalBusiness(
            id=str(metadata.get("id") or metadata.get("place_id") or external_id),
            name=kitchen.name,
            source=provider,
            url=rating.url,
            phone=metadata.get("phone"),
            address=list(metadata.get("address", []))
            or [kitchen.city or "", kitchen.state or ""],
            city=kitchen.city,
            state=kitchen.state,
            postal_code=metadata.get("postal_code"),
            country=metadata.get("country"),
            latitude=metadata.get("latitude"),
            longitude=metadata.get("longitude"),
            rating=ratings.normalized_score if ratings else rating.normalized_rating,
            review_count=ratings.external_count if ratings else rating.rating_count,
            price=metadata.get("price"),
            categories=[],
            metadata={**metadata, "kitchen_id": str(kitchen.id)},
        )
        return ExternalBusinessDetails(
            **business.model_dump(),
            photos=metadata.get("photos", []),
            hours=metadata.get("hours", {}),
            attributes=metadata.get("attributes", {}),
        )

    async def _fallback_reviews(
        self, provider: str, external_id: str
    ) -> ExternalReviewListResponse:
        rating = await self._lookup_rating_by_external_id(provider, external_id)
        if rating is None:
            raise ExternalAPIError(provider, f"No cached reviews found for {external_id}")

        stmt = (
            select(Review)
            .where(Review.kitchen_id == rating.kitchen_id)
            .where(Review.status == ReviewStatus.APPROVED)
            .order_by(Review.created_at.desc())
            .limit(50)
        )
        reviews = (await self.session.execute(stmt)).scalars().all()
        converted = [
            ExternalBusinessReview(
                id=str(review.id),
                source=provider,
                author=review.customer.full_name if review.customer else None,
                rating=review.rating,
                text=review.comment,
                language="en",
                url=None,
                created_at=review.created_at,
                metadata={"review_id": str(review.id)},
            )
            for review in reviews
        ]
        return ExternalReviewListResponse(
            business_id=str(external_id),
            source=provider,
            reviews=converted,
            total=len(converted),
        )

    async def _lookup_rating_by_external_id(
        self, provider: str, external_id: str
    ) -> KitchenExternalRating | None:
        stmt: Select[KitchenExternalRating] = select(KitchenExternalRating).where(
            KitchenExternalRating.source == provider
        )
        for rating in (await self.session.execute(stmt)).scalars():
            details = rating.details or {}
            identifiers = {
                str(details.get("id")),
                str(details.get("alias")),
                str(details.get("business_id")),
                str(details.get("place_id")),
            }
            identifiers.add(str(rating.url))
            identifiers.add(str(rating.kitchen_id))
            if external_id in identifiers:
                return rating
        return None

    async def _record_history(
        self, rating: KitchenExternalRating, *, captured_at: datetime
    ) -> None:
        history = KitchenRatingHistory(
            kitchen_id=rating.kitchen_id,
            source=rating.source,
            rating=rating.rating,
            rating_scale=rating.rating_scale,
            rating_count=rating.rating_count,
            normalized_rating=rating.normalized_rating,
            captured_at=captured_at,
            context=rating.details or {},
        )
        self.session.add(history)

    async def _invalidate_cache(self, kitchen_id: UUID) -> None:
        cache_key = self._cache_key("ratings", "kitchen", kitchen_id=str(kitchen_id))
        await self.redis.setex(cache_key, 1, "")
        history_key = self._cache_key("ratings", "history", kitchen_id=str(kitchen_id))
        await self.redis.setex(history_key, 1, "")

    def _calculate_normalized_score(
        self,
        internal_avg: float | None,
        internal_count: int,
        external_sources: Sequence[ExternalRatingModel],
    ) -> float | None:
        total_weight = float(internal_count or 0)
        weighted_sum = (internal_avg or 0) * float(internal_count or 0)

        for source in external_sources:
            normalized = source.normalized_rating
            if normalized is None:
                normalized = self._normalize_rating(source.rating, source.rating_scale)
            count = source.rating_count or 0
            total_weight += count
            weighted_sum += normalized * count

        if total_weight == 0:
            return internal_avg
        return weighted_sum / total_weight

    def _select_external_source(
        self, ratings: KitchenRatingResponse, provider: str
    ) -> ExternalRatingModel | None:
        for source in ratings.external_sources:
            if source.source == provider:
                return source
        return ratings.external_sources[0] if ratings.external_sources else None

    def _normalize_rating(self, rating: float, scale: float) -> float:
        if scale <= 0:  # pragma: no cover - guard clause
            return rating
        normalized = rating / scale * 5
        return max(0.0, min(5.0, normalized))

    def _score_text(self, text: str) -> float:
        tokens = self._tokenize(text)
        if not tokens:
            return 0.0
        positive = sum(1 for token in tokens if token in _POSITIVE_TERMS)
        negative = sum(1 for token in tokens if token in _NEGATIVE_TERMS)
        total = positive + negative
        if total == 0:
            return 0.0
        return (positive - negative) / total

    def _tokenize(self, text: str) -> list[str]:
        raw_tokens = text.lower().split()
        normalized = [token.strip(".,!?;:()") for token in raw_tokens]
        return [token for token in normalized if token and token not in _STOPWORDS]

    def _cache_key(self, *parts: Any, **kwargs: Any) -> str:
        flattened = [str(part) for part in parts if part is not None]
        if kwargs:
            serialized = json.dumps(dict(sorted(kwargs.items())), sort_keys=True)
            flattened.append(serialized)
        return ":".join(["ratings", *flattened])

    async def _get_cached_model(self, key: str, model: type[BaseModel]) -> BaseModel | None:
        payload = await self.redis.get(key)
        if not payload:
            return None
        try:
            return model.model_validate_json(payload)
        except ValidationError:
            logger.debug("Failed to deserialize cache entry", extra={"key": key})
            return None

    async def _set_cached_model(
        self, key: str, instance: BaseModel, ttl: int | None = None
    ) -> None:
        ttl = ttl or self.CACHE_TTL_SECONDS
        await self.redis.setex(key, ttl, instance.model_dump_json())


__all__ = ["RatingIntegrationService"]
