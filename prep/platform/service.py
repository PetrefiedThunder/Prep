"""Service layer implementing core Prep platform workflows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from prep.cache import RedisProtocol
from prep.models.orm import Booking, Kitchen, Review, User, UserRole, ComplianceDocument
from prep.platform import schemas
from prep.platform.security import create_access_token, hash_password, serialize_session, verify_password
from prep.settings import Settings

logger = logging.getLogger("prep.platform.service")


class PlatformError(Exception):
    """Base exception raised for recoverable platform service errors."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class PlatformService:
    """Orchestrates CRUD operations for the platform domain."""

    def __init__(self, session: AsyncSession, cache: RedisProtocol, settings: Settings) -> None:
        self._session = session
        self._cache = cache
        self._settings = settings

    async def register_user(self, payload: schemas.UserRegistrationRequest) -> User:
        logger.info("Registering new user", extra={"email": payload.email})
        stmt: Select[tuple[User]] = select(User).where(func.lower(User.email) == payload.email.lower())
        result = await self._session.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise PlatformError("Email address already registered", status_code=409)

        hashed = hash_password(payload.password)
        user = User(
            email=payload.email.lower(),
            full_name=payload.full_name,
            hashed_password=hashed,
            role=payload.role,
            is_active=True,
        )
        self._session.add(user)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            logger.exception("Failed to register user", extra={"email": payload.email})
            raise PlatformError("Unable to register user", status_code=500) from exc

        await self._session.refresh(user)
        return user

    async def authenticate_user(
        self, payload: schemas.UserLoginRequest
    ) -> tuple[User, str, datetime]:
        stmt = select(User).where(func.lower(User.email) == payload.email.lower())
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise PlatformError("Invalid credentials", status_code=401)

        if not verify_password(payload.password, user.hashed_password):
            raise PlatformError("Invalid credentials", status_code=401)

        user.last_login_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(user)

        token, expires_at = create_access_token(user, self._settings)
        await self._cache.setex(
            f"session:{token}",
            self._settings.session_ttl_seconds,
            serialize_session(user, expires_at),
        )
        return user, token, expires_at

    async def create_kitchen(self, payload: schemas.KitchenCreateRequest) -> Kitchen:
        host = await self._session.get(User, payload.host_id)
        if host is None:
            raise PlatformError("Host not found", status_code=404)
        if host.role not in (UserRole.HOST, UserRole.ADMIN):
            raise PlatformError("Host account required to create kitchen", status_code=403)

        kitchen = Kitchen(
            name=payload.name,
            description=payload.description,
            host_id=payload.host_id,
            city=payload.city,
            state=payload.state,
            hourly_rate=payload.hourly_rate,
            trust_score=payload.trust_score,
            moderation_status=payload.moderation_status or "pending",
            certification_status=payload.certification_status or "pending_review",
            published=payload.published,
        )
        self._session.add(kitchen)
        await self._session.commit()
        await self._session.refresh(kitchen)
        logger.info("Created kitchen", extra={"kitchen_id": str(kitchen.id)})
        return kitchen

    async def update_kitchen(self, kitchen_id: UUID, payload: schemas.KitchenUpdateRequest) -> Kitchen:
        kitchen = await self._session.get(Kitchen, kitchen_id)
        if kitchen is None:
            raise PlatformError("Kitchen not found", status_code=404)

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(kitchen, key, value)

        await self._session.commit()
        await self._session.refresh(kitchen)
        logger.info("Updated kitchen", extra={"kitchen_id": str(kitchen.id)})
        return kitchen

    async def create_booking(self, payload: schemas.BookingCreateRequest) -> Booking:
        if payload.start_time >= payload.end_time:
            raise PlatformError("Booking end time must be after start time")

        kitchen = await self._session.get(Kitchen, payload.kitchen_id)
        if kitchen is None:
            raise PlatformError("Kitchen not found", status_code=404)

        host = await self._session.get(User, payload.host_id)
        customer = await self._session.get(User, payload.customer_id)
        if host is None or customer is None:
            raise PlatformError("Host or customer not found", status_code=404)

        booking = Booking(
            host_id=payload.host_id,
            customer_id=payload.customer_id,
            kitchen_id=payload.kitchen_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            status=payload.status,
            total_amount=payload.total_amount,
            platform_fee=payload.platform_fee,
            host_payout_amount=payload.host_payout_amount,
            payment_method=payload.payment_method,
            source=payload.source,
        )
        self._session.add(booking)
        await self._session.commit()
        await self._session.refresh(booking)
        logger.info("Created booking", extra={"booking_id": str(booking.id)})
        return booking

    async def update_booking_status(
        self, booking_id: UUID, payload: schemas.BookingStatusUpdateRequest
    ) -> Booking:
        booking = await self._session.get(Booking, booking_id)
        if booking is None:
            raise PlatformError("Booking not found", status_code=404)

        booking.status = payload.status
        booking.cancellation_reason = payload.cancellation_reason
        await self._session.commit()
        await self._session.refresh(booking)
        logger.info(
            "Updated booking status",
            extra={"booking_id": str(booking.id), "status": booking.status.value},
        )
        return booking

    async def create_review(self, payload: schemas.ReviewCreateRequest) -> Review:
        booking = await self._session.get(Booking, payload.booking_id)
        if booking is None:
            raise PlatformError("Booking not found", status_code=404)
        if booking.customer_id != payload.customer_id:
            raise PlatformError("Customer mismatch for booking", status_code=403)

        review = Review(
            booking_id=payload.booking_id,
            kitchen_id=payload.kitchen_id,
            host_id=payload.host_id,
            customer_id=payload.customer_id,
            rating=payload.rating,
            comment=payload.comment,
            equipment_rating=payload.equipment_rating or 0,
            cleanliness_rating=payload.cleanliness_rating or 0,
            communication_rating=payload.communication_rating or 0,
            value_rating=payload.value_rating or 0,
        )
        self._session.add(review)
        await self._session.commit()
        await self._session.refresh(review)
        logger.info("Created review", extra={"review_id": str(review.id)})
        return review

    async def list_reviews_for_kitchen(self, kitchen_id: UUID) -> list[Review]:
        stmt = (
            select(Review)
            .where(Review.kitchen_id == kitchen_id)
            .order_by(Review.created_at.desc())
        )
        result = await self._session.execute(stmt)
        reviews = list(result.scalars().all())
        logger.debug(
            "Fetched reviews",
            extra={"kitchen_id": str(kitchen_id), "count": len(reviews)},
        )
        return reviews

    async def create_compliance_document(
        self, payload: schemas.ComplianceDocumentCreateRequest
    ) -> ComplianceDocument:
        kitchen = await self._session.get(Kitchen, payload.kitchen_id)
        if kitchen is None:
            raise PlatformError("Kitchen not found", status_code=404)

        document = ComplianceDocument(
            kitchen_id=payload.kitchen_id,
            uploader_id=payload.uploader_id,
            document_type=payload.document_type,
            document_url=payload.document_url,
            verification_status=payload.verification_status,
            notes=payload.notes,
        )
        self._session.add(document)
        await self._session.commit()
        await self._session.refresh(document)
        logger.info(
            "Created compliance document",
            extra={"document_id": str(document.id), "kitchen_id": str(payload.kitchen_id)},
        )
        return document
*** End Patch
