"""Service layer implementing core Prep platform workflows."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

import stripe
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from prep.cache import RedisProtocol
from prep.models.orm import (
    Booking,
    BusinessPermit,
    BusinessProfile,
    ComplianceDocument,
    DocumentProcessingStatus,
    DocumentUpload,
    Kitchen,
    PaymentRecord,
    PaymentStatus,
    PermitStatus,
    Review,
    User,
    UserRole,
)
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

    async def create_payment_intent(
        self, payload: schemas.PaymentIntentCreateRequest
    ) -> str:
        if not self._settings.stripe_api_key:
            raise PlatformError("Stripe API key not configured", status_code=500)

        booking = await self._session.get(Booking, payload.booking_id)
        if booking is None:
            raise PlatformError("Booking not found", status_code=404)

        stripe.api_key = self._settings.stripe_api_key
        try:
            intent = await asyncio.to_thread(
                stripe.PaymentIntent.create,
                amount=payload.amount,
                currency=payload.currency,
                metadata={"booking_id": str(payload.booking_id)},
                automatic_payment_methods={"enabled": True},
            )
        except stripe.error.StripeError as exc:  # type: ignore[attr-defined]
            logger.exception(
                "Failed to create Stripe payment intent",
                extra={"booking_id": str(payload.booking_id)},
            )
            raise PlatformError("Unable to create payment intent", status_code=502) from exc

        client_secret = getattr(intent, "client_secret", None)
        if client_secret is None and isinstance(intent, dict):
            client_secret = intent.get("client_secret")

        if not client_secret:
            raise PlatformError("Payment intent missing client secret", status_code=502)

        intent_id = getattr(intent, "id", None)
        if intent_id is None and isinstance(intent, dict):
            intent_id = intent.get("id")

        if not intent_id:
            raise PlatformError("Payment intent missing identifier", status_code=502)

        booking.stripe_payment_intent_id = intent_id
        await self._session.commit()
        await self._session.refresh(booking)

        logger.info(
            "Created payment intent",
            extra={
                "booking_id": str(payload.booking_id),
                "payment_intent_id": intent_id,
            },
        )
        return client_secret

    async def create_document_upload(
        self, payload: schemas.DocumentUploadRequest
    ) -> DocumentUpload:
        business = await self._session.get(BusinessProfile, payload.business_id)
        if business is None:
            raise PlatformError("Business not found", status_code=404)

        if payload.permit_id is not None:
            permit = await self._session.get(BusinessPermit, payload.permit_id)
            if permit is None or permit.business_id != business.id:
                raise PlatformError("Permit not found", status_code=404)

        upload = DocumentUpload(
            business_id=payload.business_id,
            uploader_id=payload.uploader_id,
            permit_id=payload.permit_id,
            file_name=payload.file_name,
            file_url=str(payload.file_url),
            content_type=payload.content_type,
            storage_bucket=payload.storage_bucket,
            requirement_key=payload.requirement_key,
            ocr_status=(
                DocumentProcessingStatus.PROCESSING
                if payload.trigger_ocr
                else DocumentProcessingStatus.RECEIVED
            ),
        )

        self._session.add(upload)

        if payload.requirement_key:
            requirements = business.requirements or {}
            if not isinstance(requirements, dict):
                requirements = {"items": []}
            items = requirements.get("items")
            if not isinstance(items, list):
                items = []

            now_iso = datetime.now(UTC).isoformat()
            updated = False
            for item in items:
                if isinstance(item, dict) and item.get("key") == payload.requirement_key:
                    item["status"] = "submitted"
                    item["completed_at"] = now_iso
                    updated = True
                    break

            if not updated:
                items.append(
                    {
                        "key": payload.requirement_key,
                        "name": payload.requirement_key.replace("_", " ").title(),
                        "status": "submitted",
                        "completed_at": now_iso,
                    }
                )

            requirements["items"] = items
            business.requirements = requirements

        await self._session.commit()
        await self._session.refresh(upload)
        return upload

    async def get_document_upload(self, document_id: UUID) -> DocumentUpload:
        document = await self._session.get(DocumentUpload, document_id)
        if document is None:
            raise PlatformError("Document not found", status_code=404)
        return document

    async def get_permit(self, permit_id: UUID) -> BusinessPermit:
        permit = await self._session.get(BusinessPermit, permit_id)
        if permit is None:
            raise PlatformError("Permit not found", status_code=404)
        return permit

    async def get_business_readiness(
        self, business_id: UUID
    ) -> schemas.BusinessReadinessResponse:
        business = await self._session.get(BusinessProfile, business_id)
        if business is None:
            raise PlatformError("Business not found", status_code=404)

        requirements_payload = business.requirements or {}
        if isinstance(requirements_payload, list):
            raw_items = requirements_payload
        elif isinstance(requirements_payload, dict):
            raw_items = requirements_payload.get("items", []) or []
        else:
            raw_items = []

        requirements: list[schemas.ReadinessRequirement] = []
        completed = 0
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status", "pending"))
            completed_at_raw = item.get("completed_at")
            completed_at: datetime | None = None
            if completed_at_raw:
                try:
                    completed_at = datetime.fromisoformat(str(completed_at_raw))
                except ValueError:
                    completed_at = None
            requirement = schemas.ReadinessRequirement(
                name=str(item.get("name") or item.get("key") or "Requirement"),
                description=item.get("description"),
                status=status,
                completed_at=completed_at,
            )
            requirements.append(requirement)
            if status.lower() in {"complete", "completed", "approved", "submitted"}:
                completed += 1

        total_requirements = len(requirements) or 1
        readiness_score = round(completed / total_requirements, 2)
        permit_ids = [permit.id for permit in business.permits]
        next_actions = [
            str(item.get("next_action"))
            for item in raw_items
            if isinstance(item, dict) and item.get("next_action")
        ]

        return schemas.BusinessReadinessResponse(
            business_id=business.id,
            readiness_score=readiness_score,
            requirements=requirements,
            next_actions=next_actions,
            permit_ids=permit_ids,
            last_updated=business.updated_at or datetime.now(UTC),
        )

    async def create_checkout(
        self, payload: schemas.CheckoutRequest
    ) -> tuple[PaymentRecord, str | None]:
        if payload.initiate_refund and payload.payment_id is None:
            raise PlatformError("payment_id is required to initiate a refund")

        business = await self._session.get(BusinessProfile, payload.business_id)
        if business is None:
            raise PlatformError("Business not found", status_code=404)

        if payload.booking_id is not None:
            booking = await self._session.get(Booking, payload.booking_id)
            if booking is None:
                raise PlatformError("Booking not found", status_code=404)

        if payload.initiate_refund:
            record = await self._session.get(PaymentRecord, payload.payment_id)
            if record is None:
                raise PlatformError("Payment record not found", status_code=404)
            record.status = PaymentStatus.REFUND_PENDING
            refund_amount = (
                sum(item.amount_cents for item in payload.line_items)
                if payload.line_items
                else record.amount_cents
            )
            record.refunded_amount_cents = refund_amount
            await self._session.commit()
            await self._session.refresh(record)
            return record, None

        if not payload.line_items:
            raise PlatformError("At least one line item is required")

        total_amount = sum(item.amount_cents for item in payload.line_items)
        if total_amount <= 0:
            raise PlatformError("Checkout amount must be greater than zero")

        currency = payload.currency.lower()

        provider_payment_id: str | None = None
        client_secret: str | None = None
        status = PaymentStatus.SUCCEEDED
        provider = "internal"

        if self._settings.stripe_api_key:
            stripe.api_key = self._settings.stripe_api_key
            try:
                intent = await asyncio.to_thread(
                    stripe.PaymentIntent.create,
                    amount=total_amount,
                    currency=currency,
                    metadata={
                        "business_id": str(payload.business_id),
                        "booking_id": str(payload.booking_id)
                        if payload.booking_id
                        else None,
                    },
                    automatic_payment_methods={"enabled": True},
                )
            except stripe.error.StripeError as exc:  # type: ignore[attr-defined]
                logger.exception(
                    "Failed to create checkout payment intent",
                    extra={"business_id": str(payload.business_id)},
                )
                raise PlatformError("Unable to initiate checkout", status_code=502) from exc

            provider_payment_id = getattr(intent, "id", None)
            if provider_payment_id is None and isinstance(intent, dict):
                provider_payment_id = intent.get("id")
            client_secret = getattr(intent, "client_secret", None)
            if client_secret is None and isinstance(intent, dict):
                client_secret = intent.get("client_secret")
            status = PaymentStatus.PENDING
            provider = "stripe"
        else:
            provider_payment_id = f"simulated_{uuid4()}"

        record = PaymentRecord(
            business_id=payload.business_id,
            booking_id=payload.booking_id,
            provider_payment_id=provider_payment_id,
            provider=provider,
            status=status,
            amount_cents=total_amount,
            currency=currency,
            line_items=[item.model_dump() for item in payload.line_items],
            receipt_url=f"https://receipts.prep.local/{provider_payment_id or 'preview'}",
        )

        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record, client_secret

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
