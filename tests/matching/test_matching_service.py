from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from fnmatch import fnmatch
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.cache import RedisProtocol
from prep.matching.schemas import (
    ExternalRatingSyncItem,
    ExternalRatingSyncRequest,
    KitchenMatchRequest,
    PreferenceSettings,
)
from prep.matching.service import MatchingService
from prep.models.orm import (
    Base,
    Booking,
    BookingStatus,
    Kitchen,
    KitchenMatchingProfile,
    Review,
    ReviewStatus,
    User,
)


class InMemoryRedis(RedisProtocol):
    """Simple Redis substitute for tests."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> Any:
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: Any) -> None:
        if ttl <= 0:
            self.store.pop(key, None)
        elif value == "":
            # emulate immediate expiration by removing the key
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


async def _create_kitchen(
    session: AsyncSession,
    host: User,
    *,
    name: str,
    city: str,
    state: str,
    hourly_rate: float,
    trust_score: float,
) -> Kitchen:
    kitchen = Kitchen(
        id=uuid4(),
        name=name,
        description="",
        host_id=host.id,
        city=city,
        state=state,
        hourly_rate=hourly_rate,
        trust_score=trust_score,
        moderation_status="approved",
        published=True,
    )
    session.add(kitchen)
    await session.flush()
    return kitchen


async def _attach_profile(
    session: AsyncSession,
    kitchen: Kitchen,
    *,
    equipment: list[str],
    cuisines: list[str],
    certifications: list[str],
    availability: list[str],
) -> KitchenMatchingProfile:
    profile = KitchenMatchingProfile(
        kitchen_id=kitchen.id,
        equipment=equipment,
        cuisines=cuisines,
        certifications=certifications,
        availability=availability,
    )
    session.add(profile)
    await session.flush()
    return profile


async def _create_booking(
    session: AsyncSession,
    *,
    host: User,
    customer: User,
    kitchen: Kitchen,
    start: datetime,
) -> Booking:
    booking = Booking(
        id=uuid4(),
        host_id=host.id,
        customer_id=customer.id,
        kitchen_id=kitchen.id,
        status=BookingStatus.COMPLETED,
        start_time=start,
        end_time=start + timedelta(hours=4),
        total_amount=400,
        platform_fee=40,
        host_payout_amount=360,
    )
    session.add(booking)
    await session.flush()
    return booking


async def _leave_review(
    session: AsyncSession,
    *,
    booking: Booking,
    rating: float,
    customer: User,
) -> Review:
    review = Review(
        id=uuid4(),
        booking_id=booking.id,
        kitchen_id=booking.kitchen_id,
        host_id=booking.host_id,
        customer_id=customer.id,
        rating=rating,
        equipment_rating=rating,
        cleanliness_rating=rating,
        communication_rating=rating,
        value_rating=rating,
        comment="",
        status=ReviewStatus.APPROVED,
    )
    session.add(review)
    await session.flush()
    return review


@pytest.mark.anyio
async def test_matching_flow(
    session_factory: async_sessionmaker[AsyncSession], redis: InMemoryRedis
) -> None:
    async with session_factory() as session:
        service = MatchingService(session, redis)

        seeker = await _create_user(session, "chef@example.com")
        host = await _create_user(session, "host@example.com")
        alt_host = await _create_user(session, "alt@example.com")

        preferred = await _create_kitchen(
            session,
            host,
            name="East Austin Prep",
            city="Austin",
            state="TX",
            hourly_rate=95,
            trust_score=4.6,
        )
        await _attach_profile(
            session,
            preferred,
            equipment=["Range", "Freezer", "Mixer"],
            cuisines=["Italian", "Pastry"],
            certifications=["food_handler", "level_2"],
            availability=["weekday_morning", "weekend"],
        )

        backup = await _create_kitchen(
            session,
            alt_host,
            name="West Austin Prep",
            city="Austin",
            state="TX",
            hourly_rate=140,
            trust_score=4.1,
        )
        await _attach_profile(
            session,
            backup,
            equipment=["Range", "Blender"],
            cuisines=["Mexican"],
            certifications=["food_handler"],
            availability=["weekend"],
        )

        # booking and review history boost popularity and ratings
        start = datetime.now(UTC) - timedelta(days=7)
        booking = await _create_booking(
            session, host=host, customer=seeker, kitchen=preferred, start=start
        )
        await _leave_review(session, booking=booking, rating=4.8, customer=seeker)
        await session.commit()

        prefs = await service.set_preferences(
            seeker,
            PreferenceSettings(
                equipment=["Range", "Freezer"],
                cuisines=["Italian"],
                certifications=["food_handler"],
                preferred_cities=["Austin"],
                availability=["weekday_morning"],
                max_price=120,
            ),
        )
        assert "range" in prefs.equipment

        matches = await service.match_kitchens(seeker, KitchenMatchRequest(limit=5))
        assert matches.matches, "Expected at least one recommendation"
        assert matches.matches[0].kitchen_id == preferred.id
        assert matches.matches[0].confidence <= 1
        assert redis.store, "Match results should be cached"

        cached = await service.get_recommendations(seeker.id)
        assert cached.matches[0].kitchen_id == preferred.id


@pytest.mark.anyio
async def test_external_rating_sync(
    session_factory: async_sessionmaker[AsyncSession], redis: InMemoryRedis
) -> None:
    async with session_factory() as session:
        service = MatchingService(session, redis)

        host = await _create_user(session, "host2@example.com")
        kitchen = await _create_kitchen(
            session,
            host,
            name="Downtown Kitchen",
            city="Dallas",
            state="TX",
            hourly_rate=110,
            trust_score=4.2,
        )
        await session.commit()

        request = ExternalRatingSyncRequest(
            sources=[
                ExternalRatingSyncItem(
                    kitchen_id=kitchen.id,
                    source="yelp",
                    rating=4.4,
                    rating_scale=5,
                    rating_count=120,
                )
            ]
        )
        response = await service.sync_external_ratings(request)
        assert response.updated == 1

        ratings = await service.get_kitchen_ratings(kitchen.id)
        assert ratings.external_sources
        assert ratings.external_sources[0].normalized_rating == pytest.approx(4.4, rel=1e-3)

        # Ensure ratings are reused within matching calculations
        seeker = await _create_user(session, "seeker@example.com")
        prefs = PreferenceSettings(preferred_cities=["Dallas"])
        await service.set_preferences(seeker, prefs)
        matches = await service.match_kitchens(seeker, KitchenMatchRequest(limit=1))
        assert matches.matches
        assert matches.matches[0].external_rating == pytest.approx(4.4, rel=1e-3)
