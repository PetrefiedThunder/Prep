"""Service layer implementing core Prep platform workflows."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import stripe
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from prep.auth.providers import IdentityProfile
from prep.cache import RedisProtocol
from prep.models.orm import (
    APIKey,
    Booking,
    ComplianceDocument,
    IdentityProvider,
    IdentityProviderType,
    Kitchen,
    RefreshToken,
    Review,
    User,
    UserIdentity,
    UserRole,
)
from prep.platform import schemas
from prep.platform.security import (
    create_access_token,
    generate_api_key,
    generate_refresh_token,
    create_refresh_token,
    generate_api_key_secret,
    hash_api_key_secret,
    hash_password,
    hash_token,
    serialize_session,
    verify_password,
)
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
            rbac_roles=self._default_rbac_roles(payload.role),
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
    ) -> tuple[User, str, str, datetime]:
        self,
        payload: schemas.UserLoginRequest,
        *,
        device_fingerprint: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, datetime, str, datetime]:
        stmt = select(User).where(func.lower(User.email) == payload.email.lower())
        result = await self._session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise PlatformError("Invalid credentials", status_code=401)

        if not verify_password(payload.password, user.hashed_password):
            raise PlatformError("Invalid credentials", status_code=401)

        user.last_login_at = datetime.now(UTC)
        refresh_token, _ = await self._create_refresh_token(user, commit=False)

        token, expires_at = create_access_token(user, self._settings)
        refresh_token, refresh_expires = create_refresh_token(self._settings)
        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=refresh_expires,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._session.add(refresh_record)
        await self._session.commit()
        await self._session.refresh(user)

        await self._cache.setex(
            f"session:{token}",
            self._settings.session_ttl_seconds,
            serialize_session(user, expires_at),
        )
        return user, token, refresh_token, expires_at

    async def refresh_access_token(
        self, refresh_token: str
    ) -> tuple[User, str, str, datetime]:
        token_hash = hash_token(refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self._session.execute(stmt)
        stored_token = result.scalar_one_or_none()
        if stored_token is None:
            raise PlatformError("Refresh token is invalid", status_code=401)

        now = datetime.now(UTC)
        if stored_token.revoked_at is not None or stored_token.expires_at < now:
            stored_token.revoked_at = stored_token.revoked_at or now
            await self._session.commit()
            raise PlatformError("Refresh token expired", status_code=401)

        user = await self._session.get(User, stored_token.user_id)
        if user is None or not user.is_active:
            raise PlatformError("Account is not active", status_code=403)

        stored_token.revoked_at = now
        new_refresh_token, _ = await self._create_refresh_token(user, commit=False)

        token, expires_at = create_access_token(user, self._settings)
        await self._cache.setex(
            f"session:{token}",
            self._settings.session_ttl_seconds,
            serialize_session(user, expires_at),
        )

        await self._session.commit()
        await self._session.refresh(user)

        return user, token, new_refresh_token, expires_at
        return user, token, expires_at, refresh_token, refresh_expires

    async def refresh_access_token(
        self,
        refresh_token: str,
        *,
        device_fingerprint: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, datetime, str, datetime]:
        token_hash = hash_token(refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None or record.revoked_at is not None:
            raise PlatformError("Invalid refresh token", status_code=401)

        if record.expires_at <= datetime.now(UTC):
            raise PlatformError("Refresh token expired", status_code=401)

        user = await self._session.get(User, record.user_id)
        if user is None or not user.is_active:
            raise PlatformError("User not found", status_code=401)

        access_token, access_expires = create_access_token(user, self._settings)
        new_refresh_token, new_refresh_expires = create_refresh_token(self._settings)

        record.token_hash = hash_token(new_refresh_token)
        record.expires_at = new_refresh_expires
        record.rotated_at = datetime.now(UTC)
        if device_fingerprint:
            record.device_fingerprint = device_fingerprint
        if ip_address:
            record.ip_address = ip_address
        if user_agent:
            record.user_agent = user_agent

        await self._session.commit()
        await self._session.refresh(user)

        await self._cache.setex(
            f"session:{access_token}",
            self._settings.session_ttl_seconds,
            serialize_session(user, access_expires),
        )

        return user, access_token, access_expires, new_refresh_token, new_refresh_expires

    async def issue_api_key(
        self, user_id: UUID, payload: schemas.APIKeyIssueRequest
    ) -> tuple[APIKey, str]:
        user = await self._session.get(User, user_id)
        if user is None:
            raise PlatformError("User not found", status_code=404)

        prefix, secret = generate_api_key_secret()
        hashed_secret = hash_api_key_secret(secret)
        expires_at: datetime | None = None
        if payload.expires_in_days is not None:
            expires_at = datetime.now(UTC) + timedelta(days=payload.expires_in_days)

        api_key = APIKey(
            user_id=user.id,
            name=payload.name,
            prefix=prefix,
            hashed_secret=hashed_secret,
            expires_at=expires_at,
            is_active=True,
        )

        self._session.add(api_key)
        await self._session.commit()
        await self._session.refresh(api_key)
        return api_key, secret

    async def rotate_api_key(
        self,
        api_key_id: UUID,
        *,
        actor_id: UUID,
        expires_in_days: int | None = None,
    ) -> tuple[APIKey, str]:
        api_key = await self._session.get(APIKey, api_key_id)
        if api_key is None or not api_key.is_active:
            raise PlatformError("API key not found", status_code=404)

        if api_key.user_id != actor_id:
            raise PlatformError("Cannot rotate key for another user", status_code=403)

        prefix, secret = generate_api_key_secret()
        api_key.prefix = prefix
        api_key.hashed_secret = hash_api_key_secret(secret)
        api_key.rotated_at = datetime.now(UTC)
        if expires_in_days is not None:
            api_key.expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        await self._session.commit()
        await self._session.refresh(api_key)
        return api_key, secret

    async def revoke_api_key(self, api_key_id: UUID, *, actor_id: UUID) -> APIKey:
        api_key = await self._session.get(APIKey, api_key_id)
        if api_key is None:
            raise PlatformError("API key not found", status_code=404)

        if api_key.user_id != actor_id:
            raise PlatformError("Cannot revoke key for another user", status_code=403)

        api_key.is_active = False
        api_key.revoked_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(api_key)
        return api_key

    async def link_identity_provider(
        self,
        user: User,
        *,
        provider_slug: str,
        provider_name: str,
        provider_type: IdentityProviderType,
        issuer: str,
        subject: str,
        email: str | None,
        full_name: str | None,
        attributes: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UserIdentity:
        stmt = select(IdentityProvider).where(IdentityProvider.slug == provider_slug)
        result = await self._session.execute(stmt)
        provider = result.scalar_one_or_none()
        if provider is None:
            provider = IdentityProvider(
                name=provider_name,
                slug=provider_slug,
                provider_type=provider_type,
                issuer=issuer,
                metadata_url=metadata.get("metadata_url") if metadata else None,
                jwks_url=metadata.get("jwks_url") if metadata else None,
                sso_url=metadata.get("sso_url") if metadata else None,
                acs_url=metadata.get("acs_url") if metadata else None,
                settings=metadata or {},
            )
            self._session.add(provider)
            await self._session.flush()

        stmt = select(UserIdentity).where(
            UserIdentity.provider_id == provider.id,
            UserIdentity.subject == subject,
        )
        result = await self._session.execute(stmt)
        identity = result.scalar_one_or_none()
        if identity is None:
            identity = UserIdentity(
                user_id=user.id,
                provider_id=provider.id,
                subject=subject,
                email=email,
                full_name=full_name,
                attributes=attributes or {},
                last_login_at=datetime.now(UTC),
            )
            self._session.add(identity)
        else:
            identity.user_id = user.id
            identity.email = email
            identity.full_name = full_name
            identity.attributes = attributes or {}
            identity.last_login_at = datetime.now(UTC)

        await self._session.commit()
        await self._session.refresh(identity)
        return identity

    async def create_kitchen(self, payload: schemas.KitchenCreateRequest) -> Kitchen:
        host = await self._session.get(User, payload.host_id)
        if host is None:
            raise PlatformError("Host not found", status_code=404)
        if host.role not in (
            UserRole.HOST,
            UserRole.ADMIN,
            UserRole.KITCHEN_MANAGER,
            UserRole.OPERATOR_ADMIN,
        ):
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

    async def create_api_key(
        self, user_id: UUID, payload: schemas.APIKeyCreateRequest
    ) -> tuple[APIKey, str]:
        user = await self._session.get(User, user_id)
        if user is None:
            raise PlatformError("User not found", status_code=404)

        raw_key, prefix, hashed = generate_api_key()
        api_key = APIKey(
            user_id=user_id,
            name=payload.name,
            key_prefix=prefix,
            hashed_key=hashed,
            expires_at=payload.expires_at,
            is_active=True,
        )
        self._session.add(api_key)

        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            logger.exception(
                "Failed to create API key", extra={"user_id": str(user_id)}
            )
            raise PlatformError("Unable to issue API key", status_code=500) from exc

        await self._session.refresh(api_key)
        return api_key, raw_key

    async def rotate_api_key(self, user_id: UUID, key_id: UUID) -> tuple[APIKey, str]:
        api_key = await self._session.get(APIKey, key_id)
        if api_key is None or api_key.user_id != user_id:
            raise PlatformError("API key not found", status_code=404)

        if not api_key.is_active:
            raise PlatformError("API key is inactive", status_code=400)

        raw_key, prefix, hashed = generate_api_key()
        api_key.key_prefix = prefix
        api_key.hashed_key = hashed
        api_key.rotated_at = datetime.now(UTC)

        await self._session.commit()
        await self._session.refresh(api_key)
        return api_key, raw_key

    async def upsert_identity_link(
        self, user_id: UUID, provider_slug: str, profile: IdentityProfile
    ) -> UserIdentity:
        provider_stmt = select(IdentityProvider).where(
            func.lower(IdentityProvider.slug) == provider_slug.lower()
        )
        provider_result = await self._session.execute(provider_stmt)
        provider = provider_result.scalar_one_or_none()
        if provider is None or not provider.is_active:
            raise PlatformError("Identity provider not found", status_code=404)

        stmt = select(UserIdentity).where(
            UserIdentity.user_id == user_id,
            UserIdentity.provider_id == provider.id,
        )
        result = await self._session.execute(stmt)
        identity = result.scalar_one_or_none()
        now = datetime.now(UTC)
        if identity is None:
            identity = UserIdentity(
                user_id=user_id,
                provider_id=provider.id,
                subject=profile.subject,
                email=profile.email,
                raw_attributes=profile.claims,
                last_sign_in_at=now,
            )
            self._session.add(identity)
        else:
            identity.subject = profile.subject
            identity.email = profile.email
            identity.raw_attributes = profile.claims
            identity.last_sign_in_at = now

        await self._session.commit()
        await self._session.refresh(identity)
        return identity

    async def _create_refresh_token(
        self, user: User, *, commit: bool = True
    ) -> tuple[str, RefreshToken]:
        raw = generate_refresh_token()
        refresh = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(UTC)
            + timedelta(days=self._settings.refresh_token_ttl_days),
        )
        self._session.add(refresh)
        if commit:
            await self._session.commit()
            await self._session.refresh(refresh)
        else:
            await self._session.flush()
        return raw, refresh

    def _default_rbac_roles(self, role: UserRole) -> list[str]:
        if role is UserRole.ADMIN:
            return ["operator_admin", "support_analyst", "city_reviewer"]
        if role is UserRole.HOST:
            return ["kitchen_manager"]
        return ["food_business_admin"]
