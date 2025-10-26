"""Service layer encapsulating Stripe Connect onboarding."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

import stripe
from stripe.error import StripeError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from prep.models.orm import User, UserRole
from prep.settings import Settings

logger = logging.getLogger("prep.payments.service")


class PaymentsError(Exception):
    """Raised for recoverable errors in the payments domain."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


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

        secret_key = self._settings.stripe_secret_key
        if not secret_key:
            raise PaymentsError("Stripe secret key is not configured", status_code=500)

        stripe.api_key = secret_key

        created_new_account = False
        account_id = user.stripe_account_id
        try:
            if account_id is None:
                account = await asyncio.to_thread(stripe.Account.create, type="custom")
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
            )
        except StripeError as exc:  # pragma: no cover - network errors handled uniformly
            logger.exception(
                "Stripe error while provisioning connect onboarding",
                extra={"user_id": str(user_id)},
            )
            if created_new_account:
                await self._session.rollback()
                user.stripe_account_id = None
            raise PaymentsError("Failed to initialize Stripe Connect onboarding", status_code=502) from exc

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
