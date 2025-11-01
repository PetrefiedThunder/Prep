"""Service layer implementing core Prep platform workflows."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4

import stripe
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from prep.cache import RedisProtocol
from prep.models.orm import (
    Booking,
    BusinessProfile,
    BusinessReadinessSnapshot,
    CheckoutPayment,
    CheckoutPaymentStatus,
    ComplianceDocument,
    DocumentOCRStatus,
    DocumentUpload,
    DocumentUploadStatus,
    Kitchen,
    Permit,
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

    async def _get_business_profile(self, business_id: UUID) -> BusinessProfile:
        business = await self._session.get(BusinessProfile, business_id)
        if business is None:
            raise PlatformError("Business not found", status_code=404)
        return business

    async def _evaluate_business_readiness(
        self, business: BusinessProfile
    ) -> schemas.BusinessReadinessResponse:
        now = datetime.now(UTC)
        doc_stmt = select(DocumentUpload).where(DocumentUpload.business_id == business.id)
        permit_stmt = select(Permit).where(Permit.business_id == business.id)
        docs_result = await self._session.execute(doc_stmt)
        permits_result = await self._session.execute(permit_stmt)
        documents = list(docs_result.scalars().all())
        permits = list(permits_result.scalars().all())

        requirements = [
            {
                "slug": "business_license",
                "title": "Business license on file",
                "description": "An active business license is required before you can host bookings.",
                "document_types": {"business_license", "license_certificate"},
                "permit_types": {"business_license"},
                "action": "Upload or connect your city or county business license.",
            },
            {
                "slug": "health_permit",
                "title": "Health permit active",
                "description": "Local health department permits must be current for food service operations.",
                "document_types": {"health_permit", "inspection_report"},
                "permit_types": {"health_permit", "public_health"},
                "action": "Submit a current health permit or schedule an inspection.",
            },
            {
                "slug": "fire_certificate",
                "title": "Fire and safety documentation",
                "description": "Fire inspection certificates ensure compliant kitchen operations.",
                "document_types": {"fire_certificate", "sprinkler_inspection"},
                "permit_types": {"fire_certificate", "fire_department"},
                "action": "Provide a valid fire inspection certificate or request a review.",
            },
        ]

        checklist: list[schemas.BusinessReadinessChecklistItem] = []
        gating_requirements: list[str] = []
        outstanding_actions: list[str] = []
        completed = 0

        for requirement in requirements:
            relevant_docs = [
                doc
                for doc in documents
                if doc.document_type in requirement["document_types"]
            ]
            relevant_permits = [
                permit
                for permit in permits
                if permit.permit_type in requirement["permit_types"]
            ]

            doc_verified = any(doc.status == DocumentUploadStatus.VERIFIED for doc in relevant_docs)
            doc_in_review = any(
                doc.status in {DocumentUploadStatus.PROCESSING, DocumentUploadStatus.STORED}
                for doc in relevant_docs
            )
            permit_active = any(permit.status == PermitStatus.ACTIVE for permit in relevant_permits)
            permit_pending = any(permit.status == PermitStatus.PENDING for permit in relevant_permits)

            if permit_active or doc_verified:
                status = "complete"
                completed += 1
                completed_at_candidates = [
                    getattr(doc, "updated_at", None) for doc in relevant_docs
                ] + [getattr(permit, "updated_at", None) for permit in relevant_permits]
                completed_at = max(
                    [ts for ts in completed_at_candidates if ts is not None],
                    default=None,
                )
            elif doc_in_review or permit_pending:
                status = "in_review"
                completed_at = None
                gating_requirements.append(requirement["title"])
                outstanding_actions.append(requirement["action"])
            else:
                status = "missing"
                completed_at = None
                gating_requirements.append(requirement["title"])
                outstanding_actions.append(requirement["action"])

            checklist.append(
                schemas.BusinessReadinessChecklistItem(
                    slug=requirement["slug"],
                    title=requirement["title"],
                    description=requirement["description"],
                    status=status,
                    completed_at=completed_at,
                )
            )

        score = completed / max(len(requirements), 1)
        if score >= 0.85:
            stage = "ready"
        elif score >= 0.5:
            stage = "in_progress"
        else:
            stage = "not_ready"

        business.readiness_score = score
        business.readiness_stage = stage
        business.readiness_summary = {
            "last_evaluated_at": now.isoformat(),
            "completed_requirements": completed,
            "total_requirements": len(requirements),
        }

        snapshot = BusinessReadinessSnapshot(
            business_id=business.id,
            overall_score=score,
            stage=stage,
            checklist=[item.model_dump() for item in checklist],
            gating_requirements=gating_requirements,
            outstanding_actions=outstanding_actions,
        )
        self._session.add(snapshot)

        response = schemas.BusinessReadinessResponse(
            business_id=business.id,
            business_name=business.legal_name,
            readiness_score=score,
            readiness_stage=stage,
            checklist=checklist,
            gating_requirements=gating_requirements,
            outstanding_actions=outstanding_actions,
            last_evaluated_at=now,
        )
        return response

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

    async def create_document_upload(
        self, payload: schemas.DocumentUploadCreateRequest
    ) -> DocumentUpload:
        business = await self._get_business_profile(payload.business_id)

        upload = DocumentUpload(
            business_id=payload.business_id,
            uploader_id=payload.uploader_id,
            document_type=payload.document_type,
            filename=payload.filename,
            content_type=payload.content_type,
            storage_bucket=payload.storage_bucket,
            storage_key=payload.storage_key,
            status=payload.status or DocumentUploadStatus.PROCESSING,
            ocr_status=payload.ocr_status or DocumentOCRStatus.PENDING,
            notes=payload.notes,
            ocr_metadata=payload.metadata or {},
        )
        self._session.add(upload)
        await self._session.commit()
        await self._session.refresh(upload)

        logger.info(
            "Stored onboarding document",
            extra={
                "business_id": str(business.id),
                "document_id": str(upload.id),
                "document_type": payload.document_type,
            },
        )

        # Simulate asynchronous OCR trigger by caching a job token when Redis is available.
        job_key = f"ocr:document:{upload.id}"
        try:
            await self._cache.setex(job_key, 900, "pending")
        except Exception:  # pragma: no cover - cache failures should not break flow
            logger.debug("Unable to enqueue OCR job", extra={"document_id": str(upload.id)})

        return upload

    async def get_permit(self, permit_id: UUID) -> Permit:
        permit = await self._session.get(Permit, permit_id)
        if permit is None:
            raise PlatformError("Permit not found", status_code=404)
        return permit

    async def get_business_readiness(
        self, business_id: UUID
    ) -> schemas.BusinessReadinessResponse:
        business = await self._get_business_profile(business_id)
        readiness = await self._evaluate_business_readiness(business)
        await self._session.commit()
        return readiness

    async def create_checkout_payment(
        self, payload: schemas.CheckoutPaymentCreateRequest
    ) -> CheckoutPayment:
        if payload.action == "refund":
            if payload.existing_payment_id is None:
                raise PlatformError("Payment to refund is required", status_code=400)
            payment = await self._session.get(CheckoutPayment, payload.existing_payment_id)
            if payment is None:
                raise PlatformError("Checkout payment not found", status_code=404)
            if payment.status not in {
                CheckoutPaymentStatus.SUCCEEDED,
                CheckoutPaymentStatus.REQUIRES_ACTION,
            }:
                raise PlatformError(
                    "Only settled payments can be refunded", status_code=409
                )

            payment.status = CheckoutPaymentStatus.REFUND_REQUESTED
            payment.refund_reason = payload.refund_reason
            payment.refund_requested_at = datetime.now(UTC)
            await self._session.commit()
            await self._session.refresh(payment)
            logger.info(
                "Refund requested",
                extra={"payment_id": str(payment.id), "reason": payload.refund_reason},
            )
            return payment

        if not payload.line_items:
            raise PlatformError("At least one line item is required", status_code=400)

        total_minor_units = sum(item.amount * item.quantity for item in payload.line_items)
        if total_minor_units <= 0:
            raise PlatformError("Checkout total must be greater than zero", status_code=400)

        total_amount = (
            Decimal(total_minor_units) / Decimal(100)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        business: BusinessProfile | None = None
        if payload.business_id is not None:
            business = await self._get_business_profile(payload.business_id)
            if payload.requirements_gate:
                readiness = await self.get_business_readiness(payload.business_id)
                if readiness.readiness_score < payload.minimum_readiness_score:
                    raise PlatformError(
                        "Business readiness requirements not satisfied", status_code=412
                    )
                await self._session.refresh(business)

        provider_reference = None
        payment_provider = "offline"
        if self._settings.stripe_api_key:
            payment_provider = "stripe"
            provider_reference = f"chk_{uuid4().hex}"
        else:
            provider_reference = f"manual_{uuid4().hex}"

        receipt_url = None
        if self._settings.app_base_url:
            base_url = str(self._settings.app_base_url).rstrip("/")
            receipt_url = f"{base_url}/receipts/{provider_reference}"

        payment = CheckoutPayment(
            business_id=payload.business_id,
            booking_id=payload.booking_id,
            status=CheckoutPaymentStatus.PENDING,
            currency=payload.currency,
            total_amount=total_amount,
            line_items=[item.model_dump() for item in payload.line_items],
            payment_provider=payment_provider,
            provider_reference=provider_reference,
            metadata=payload.metadata or {},
            receipt_url=receipt_url,
        )
        self._session.add(payment)
        await self._session.commit()
        await self._session.refresh(payment)

        logger.info(
            "Created checkout payment",
            extra={
                "payment_id": str(payment.id),
                "business_id": str(payload.business_id) if payload.business_id else None,
                "amount": float(total_amount),
                "business_stage": business.readiness_stage if business else None,
            },
        )

        return payment
*** End Patch
