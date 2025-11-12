"""Pydantic models for the payments API."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentsConnectRequest(BaseModel):
    """Payload to initiate a Stripe Connect onboarding session."""

    user_id: UUID = Field(..., description="Identifier of the host requesting payouts")


class PaymentsConnectResponse(BaseModel):
    """Response containing Stripe Connect onboarding metadata."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "account_id": "acct_123",
                "onboarding_url": "https://connect.stripe.com/setup/s/example",
            }
        }
    )

    account_id: str = Field(..., description="Stripe Connect account identifier")
    onboarding_url: str = Field(..., description="Stripe-hosted onboarding link")
