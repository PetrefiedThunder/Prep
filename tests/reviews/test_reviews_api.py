from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, AsyncGenerator
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from fnmatch import fnmatch

from prep.cache import RedisProtocol
from prep.models.orm import (
    Base,
    Booking,
    BookingStatus,
    Kitchen,
    ReviewStatus,
    User,
)
from prep.reviews.notifications import ReviewNotifier, ReviewNotificationTransport
from prep.reviews.schemas import (
    HostResponseUpdate,
    ReviewFlagRequest,
    ReviewModerationRequest,
    ReviewPhotoCreate,
    ReviewSubmissionRequest,
    ReviewVoteRequest,
)
from prep.reviews.service import ReviewService


class InMemoryRedis(RedisProtocol):
    """Simple Redis replacement for tests."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> Any:
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: Any) -> None:
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


class CaptureTransport(ReviewNotificationTransport):
    """Collects notifications for assertions."""

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def send(
        self,
        *,
        recipient_id: UUID,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.messages.append(
            {
                "recipient_id": recipient_id,
                "title": title,
                "body": body,
                "data": data or {},
            }
        )


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
async def transport() -> CaptureTransport:
    return CaptureTransport()


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


async def _create_user(session: AsyncSession, *, email: str, is_admin: bool = False) -> User:
    user = User(
        email=email,
        full_name=email.split("@")[0],
        is_admin=is_admin,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _create_kitchen(session: AsyncSession, host: User) -> Kitchen:
    kitchen = Kitchen(
        id=uuid4(),
        name="City Kitchen",
        description="Great space",
        host_id=host.id,
        city="Austin",
        state="TX",
        hourly_rate=120,
        trust_score=4.5,
        published=True,
    )
    session.add(kitchen)
    await session.flush()
    return kitchen


async def _create_booking(session: AsyncSession, host: User, customer: User, kitchen: Kitchen) -> Booking:
    booking = Booking(
        id=uuid4(),
        host_id=host.id,
        customer_id=customer.id,
        kitchen_id=kitchen.id,
        status=BookingStatus.COMPLETED,
        start_time=datetime.now(UTC) - timedelta(days=2),
        end_time=datetime.now(UTC) - timedelta(days=2) + timedelta(hours=4),
        total_amount=500,
        platform_fee=50,
        host_payout_amount=450,
    )
    session.add(booking)
    await session.flush()
    return booking


@pytest.mark.anyio
async def test_review_service_lifecycle(
    session_factory: async_sessionmaker[AsyncSession],
    redis: InMemoryRedis,
    transport: CaptureTransport,
) -> None:
    notifier = ReviewNotifier(transport)
    async with session_factory() as session:
        service = ReviewService(session, redis, notifier)

        host = await _create_user(session, email="host@example.com", is_admin=True)
        customer = await _create_user(session, email="guest@example.com")
        admin = await _create_user(session, email="admin@example.com", is_admin=True)
        voter = await _create_user(session, email="reader@example.com")
        kitchen = await _create_kitchen(session, host)
        booking = await _create_booking(session, host, customer, kitchen)
        await session.commit()

        submission = ReviewSubmissionRequest(
            booking_id=booking.id,
            kitchen_id=kitchen.id,
            overall_rating=4.5,
            comment="Wonderful prep space with everything we needed.",
            ratings={
                "equipment": 5,
                "cleanliness": 4,
                "communication": 5,
                "value": 4,
            },
        )
        review = await service.submit_review(customer, submission)
        assert review.rating == 4.5
        assert review.status == ReviewStatus.APPROVED

        photo = await service.add_photo(customer, review.id, ReviewPhotoCreate(url="https://cdn.example.com/photo.jpg", caption="Kitchen"))
        assert photo.url.endswith("photo.jpg")

        updated_review = await service.host_response(
            host,
            review.id,
            HostResponseUpdate(response="Thanks for cooking with us!"),
        )
        assert updated_review.host_response == "Thanks for cooking with us!"

        voted = await service.vote_review(voter, review.id, ReviewVoteRequest(helpful=True))
        assert voted.helpful_count == 1

        flag = await service.flag_review(voter, review.id, ReviewFlagRequest(reason="language", notes="Potential guideline issue"))
        assert flag.status.value == "open"

        moderation = await service.moderate_review(
            admin,
            review.id,
            ReviewModerationRequest(action="reject", notes="Contains off-platform links"),
        )
        assert moderation.status == ReviewStatus.REJECTED

        listings = await service.list_kitchen_reviews(kitchen.id, requester=customer)
        assert listings.aggregate.total_reviews == 0

        await service.delete_review(review.id)
        listings_after_delete = await service.list_kitchen_reviews(kitchen.id, requester=customer)
        assert listings_after_delete.aggregate.total_reviews == 0

    titles = [msg["title"] for msg in transport.messages]
    assert "New kitchen review received" in titles
    assert "Review moderation update" in titles
