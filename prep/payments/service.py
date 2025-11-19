"""Service layer encapsulating Stripe Connect onboarding."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import stripe
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from stripe.error import SignatureVerificationError, StripeError

from prep.models.orm import (
    APIUsageEvent,
    Booking,
    StripeWebhookEvent,
    SubscriptionStatus,
    User,
    UserRole,
)
from prep.settings import Settings

logger = logging.getLogger("prep.payments.service")


class PaymentsError(Exception):
    """Raised for recoverable errors in the payments domain."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        code: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code or "payments_error"
        self.metadata = dict(metadata) if metadata else None


class PaymentsService:
    """Coordinates Stripe Connect onboarding workflows."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    async def create_connect_account(self, *, user_id: UUID) -> tuple[str, str]:
        """Provision a Stripe Connect account and onboarding link for a host."""

        user = await self._session.get(User, user_id)
        if user is None:
            raise PaymentsError("User not found", status_code=404)
        if user.role not in {UserRole.HOST, UserRole.ADMIN}:
            raise PaymentsError("Only host accounts can connect payouts", status_code=403)

        self._ensure_trial_for_pilot(user)

        secret_key = self._settings.stripe_secret_key
        if not secret_key:
            raise PaymentsError("Stripe secret key is not configured", status_code=500)

        created_new_account = False
        account_id = user.stripe_account_id
        try:
            if account_id is None:
                account = await asyncio.to_thread(
                    stripe.Account.create, type="custom", api_key=secret_key
                )
                account_id = getattr(account, "id", None)
                if not account_id:
                    raise PaymentsError("Stripe did not return an account id", status_code=502)
                user.stripe_account_id = account_id
                created_new_account = True

            account_link = await asyncio.to_thread(
                stripe.AccountLink.create,
                account=account_id,
                refresh_url=str(self._settings.stripe_connect_refresh_url),
                return_url=str(self._settings.stripe_connect_return_url),
                type="account_onboarding",
                api_key=secret_key,
            )
        except StripeError as exc:  # pragma: no cover - network errors handled uniformly
            logger.exception(
                "Stripe error while provisioning connect onboarding",
                extra={"user_id": str(user_id)},
            )
            if created_new_account:
                await self._session.rollback()
                user.stripe_account_id = None
            raise PaymentsError(
                "Failed to initialize Stripe Connect onboarding", status_code=502
            ) from exc

        if created_new_account:
            try:
                await self._session.commit()
            except SQLAlchemyError as exc:  # pragma: no cover - commit failures are exceptional
                await self._session.rollback()
                logger.exception(
                    "Database error while saving Stripe account id", extra={"user_id": str(user_id)}
                )
                raise PaymentsError("Failed to persist Stripe account", status_code=500) from exc
        else:
            await self._session.flush()

        onboarding_url = getattr(account_link, "url", None)
        if onboarding_url is None and hasattr(account_link, "get"):
            onboarding_url = account_link.get("url")
        if not onboarding_url:
            raise PaymentsError("Stripe did not return an onboarding link", status_code=502)

        return account_id, onboarding_url

    async def process_webhook(self, payload: bytes, signature: str | None) -> None:
        """Validate and handle incoming Stripe webhook events."""

        if not signature:
            raise PaymentsError("Missing Stripe signature", status_code=400)

        webhook_secret = self._settings.stripe_webhook_secret
        if not webhook_secret:
            raise PaymentsError("Stripe webhook secret is not configured", status_code=500)

        try:
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
        except ValueError as exc:
            raise PaymentsError("Invalid webhook payload", status_code=400) from exc
        except SignatureVerificationError as exc:
            raise PaymentsError("Invalid Stripe signature", status_code=400) from exc

        event_id = _get_attribute(event, "id")
        if not event_id:
            raise PaymentsError("Event is missing an id", status_code=400)

        existing = await self._session.scalar(
            select(StripeWebhookEvent).where(StripeWebhookEvent.event_id == event_id)
        )
        if existing:
            return

        self._session.add(StripeWebhookEvent(event_id=event_id))

        event_type = _get_attribute(event, "type")
        if event_type == "payment_intent.succeeded":
            await self._handle_payment_intent_succeeded(event)
        elif event_type in {
            "checkout.session.completed",
            "customer.subscription.created",
            "customer.subscription.updated",
        }:
            await self._handle_subscription_event(event)

        try:
            await self._session.commit()
        except SQLAlchemyError as exc:  # pragma: no cover - commit failures are exceptional
            await self._session.rollback()
            logger.exception(
                "Database error while processing Stripe webhook", extra={"event_id": event_id}
            )
            raise PaymentsError("Failed to persist webhook event", status_code=500) from exc

    async def _handle_payment_intent_succeeded(self, event: Any) -> None:
        """Mark the associated booking as paid when a payment intent succeeds."""

        data_object = _get_data_object(event)
        if data_object is None:
            logger.warning(
                "Received payment_intent.succeeded without data object",
                extra={"event_id": _get_attribute(event, "id")},
            )
            return

        payment_intent_id = _get_attribute(data_object, "id") or _get_attribute(
            data_object, "payment_intent"
        )
        if not payment_intent_id:
            logger.warning(
                "Payment intent event missing identifier",
                extra={"event_id": _get_attribute(event, "id")},
            )
            return

        booking = await self._session.scalar(
            select(Booking).where(Booking.payment_intent_id == payment_intent_id)
        )
        if booking is None:
            logger.warning(
                "No booking found for payment intent",
                extra={"payment_intent_id": payment_intent_id},
            )
            return

        if not booking.paid:
            booking.paid = True

    def _ensure_trial_for_pilot(self, user: User) -> None:
        """Assign or extend the pilot trial period for eligible users."""

        if not user.is_pilot_user:
            return

        if user.subscription_status == SubscriptionStatus.INACTIVE:
            user.subscription_status = SubscriptionStatus.TRIAL

        trial_start = user.trial_started_at or datetime.now(UTC)
        desired_end = trial_start + timedelta(days=60)

        user.trial_started_at = trial_start
        if user.trial_ends_at is None or user.trial_ends_at < desired_end:
            user.trial_ends_at = desired_end

    async def _handle_subscription_event(self, event: Any) -> None:
        """Mark pilot subscriptions as active and log conversion analytics."""

        user_id = _extract_user_id(event)
        if user_id is None:
            logger.debug(
                "Received subscription event without user metadata",
                extra={"event_id": _get_attribute(event, "id")},
            )
            return

        user = await self._session.get(User, user_id)
        if user is None:
            logger.warning(
                "Subscription event referenced unknown user", extra={"user_id": str(user_id)}
            )
            return

        event_type = _get_attribute(event, "type") or "subscription.unknown"
        stripe_event_id = _get_attribute(event, "id")

        if user.subscription_status != SubscriptionStatus.ACTIVE:
            user.subscription_status = SubscriptionStatus.ACTIVE
            if user.trial_ends_at is None or user.trial_ends_at < datetime.now(UTC):
                user.trial_ends_at = datetime.now(UTC)

            metadata = {
                "stripe_event_id": stripe_event_id,
                "stripe_event_type": event_type,
                "pilot_user": bool(user.is_pilot_user),
            }
            self._session.add(
                APIUsageEvent(
                    user_id=user.id,
                    event_type="pilot_conversion" if user.is_pilot_user else "subscription_update",
                    metadata=metadata,
                )
            )


def _get_attribute(obj: Any, attribute: str) -> Any:
    """Fetch an attribute or dictionary key from Stripe payload objects."""

    if hasattr(obj, attribute):
        return getattr(obj, attribute)
    if isinstance(obj, dict):
        return obj.get(attribute)
    return None


def _get_data_object(event: Any) -> Any:
    """Extract the nested data.object payload from a Stripe event."""

    data = _get_attribute(event, "data")
    if data is None:
        return None
    if isinstance(data, dict):
        return data.get("object")
    return getattr(data, "object", None)


def _extract_user_id(event: Any) -> UUID | None:
    data_object = _get_data_object(event)
    if data_object is None:
        return None

    metadata = _get_attribute(data_object, "metadata")
    if metadata:
        if isinstance(metadata, dict):
            candidate = metadata.get("user_id") or metadata.get("userId")
        else:
            candidate = getattr(metadata, "user_id", None) or getattr(metadata, "userId", None)
        user_id = _coerce_uuid(candidate)
        if user_id:
            return user_id

    client_reference = _get_attribute(data_object, "client_reference_id")
    return _coerce_uuid(client_reference)


def _coerce_uuid(value: Any) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None
