"""Tests for the rating integration service."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from fnmatch import fnmatch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.cache import RedisProtocol
from prep.models.orm import Base, Kitchen, Review, ReviewStatus, User
from prep.ratings.schemas import (
    ExternalRatingSyncItem,
    ExternalRatingSyncRequest,
    SentimentAnalysisRequest,
    SentimentReviewInput,
)
from prep.ratings.service import RatingIntegrationService


class InMemoryRedis(RedisProtocol):
    """Simplified Redis implementation for unit tests."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        if ttl <= 0 or value == "":
            self.store.pop(key, None)
        else:
            self.store[key] = value

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self.store:
                self.store.pop(key, None)
                removed += 1
        return removed

    async def keys(self, pattern: str) -> list[str]:
        return [key for key in self.store if fnmatch(key, pattern)]


@pytest.fixture()
async def session_factory() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest.fixture()
async def redis() -> InMemoryRedis:
    return InMemoryRedis()


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


async def _create_user(session: AsyncSession, email: str) -> User:
    user = User(email=email, full_name=email.split("@")[0], is_active=True)
    session.add(user)
    await session.flush()
    return user


async def _create_kitchen(session: AsyncSession, host: User, *, city: str, state: str) -> Kitchen:
    kitchen = Kitchen(
        id=uuid4(),
        name="Central Kitchen",
        description="",
        host_id=host.id,
        city=city,
        state=state,
        hourly_rate=100,
        trust_score=4.2,
        moderation_status="approved",
        published=True,
    )
    session.add(kitchen)
    await session.flush()
    return kitchen


async def _create_review(
    session: AsyncSession,
    *,
    kitchen: Kitchen,
    host: User,
    customer: User,
    rating: float,
    comment: str,
) -> Review:
    review = Review(
        id=uuid4(),
        booking_id=uuid4(),
        kitchen_id=kitchen.id,
        host_id=host.id,
        customer_id=customer.id,
        rating=rating,
        equipment_rating=rating,
        cleanliness_rating=rating,
        communication_rating=rating,
        value_rating=rating,
        comment=comment,
        status=ReviewStatus.APPROVED,
    )
    session.add(review)
    await session.flush()
    return review


@pytest.mark.anyio
async def test_rating_sync_history_and_fallback(
    session_factory: async_sessionmaker[AsyncSession],
    redis: InMemoryRedis,
) -> None:
    async with session_factory() as session:
        service = RatingIntegrationService(session, redis)

        host = await _create_user(session, "host@example.com")
        customer = await _create_user(session, "guest@example.com")
        kitchen = await _create_kitchen(session, host, city="Austin", state="TX")
        await _create_review(
            session,
            kitchen=kitchen,
            host=host,
            customer=customer,
            rating=4.0,
            comment="Great clean kitchen with friendly staff",
        )
        await session.commit()

        request = ExternalRatingSyncRequest(
            sources=[
                ExternalRatingSyncItem(
                    kitchen_id=kitchen.id,
                    source="yelp",
                    rating=4.5,
                    rating_scale=5,
                    rating_count=120,
                    metadata={
                        "id": "yelp-123",
                        "address": ["123 Main St", "Austin, TX"],
                        "phone": "123-456-7890",
                    },
                )
            ]
        )
        response = await service.sync_external_ratings(request)
        assert response.updated == 1

        aggregated = await service.get_kitchen_ratings(kitchen.id)
        assert aggregated.internal_count == 1
        assert aggregated.external_sources
        assert aggregated.external_sources[0].source == "yelp"

        history = await service.get_rating_history(kitchen.id)
        assert history.points
        assert history.points[0].source == "yelp"

        search = await service.search_yelp_businesses(term="Central", location="Austin")
        assert search.businesses
        business = search.businesses[0]
        assert business.source == "yelp"
        assert business.metadata.get("kitchen_id") == str(kitchen.id)

        details = await service.get_yelp_business("yelp-123")
        assert details.metadata.get("kitchen_id") == str(kitchen.id)

        reviews = await service.get_yelp_reviews("yelp-123")
        assert reviews.reviews
        assert reviews.reviews[0].source == "yelp"


@pytest.mark.anyio
async def test_sentiment_analysis_trends(
    session_factory: async_sessionmaker[AsyncSession],
    redis: InMemoryRedis,
) -> None:
    async with session_factory() as session:
        service = RatingIntegrationService(session, redis)

        host = await _create_user(session, "owner@example.com")
        kitchen = await _create_kitchen(session, host, city="Dallas", state="TX")
        await session.commit()

        payload = SentimentAnalysisRequest(
            kitchen_id=kitchen.id,
            source="yelp",
            reviews=[
                SentimentReviewInput(text="Amazing spotless kitchen and friendly host", rating=5),
                SentimentReviewInput(text="Bad experience with slow support", rating=2),
            ],
        )
        response = await service.analyze_sentiment(payload)
        assert response.review_count == 2
        assert response.label in {"positive", "negative", "neutral"}

        trends = await service.get_sentiment_trends(kitchen_id=kitchen.id, source="yelp")
        assert trends.points
        assert trends.points[-1].sample_size == 2
