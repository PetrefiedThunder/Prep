"""Pydantic schemas for delivery orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import AnyUrl, BaseModel, Field

from prep.models.orm import DeliveryProvider, DeliveryStatus


class DeliveryStop(BaseModel):
    """Structured contact and address information for a delivery stop."""

    name: str = Field(..., description="Contact name at the stop")
    phone: str | None = Field(default=None, description="Contact phone number")
    address: str = Field(..., description="Street address")
    city: str | None = Field(default=None, description="City of the stop")
    state: str | None = Field(default=None, description="State or region")
    postal_code: str | None = Field(default=None, description="Postal or ZIP code")
    instructions: str | None = Field(
        default=None, description="Special instructions for the courier"
    )


class DeliveryCreateRequest(BaseModel):
    """Request payload to create a third-party delivery."""

    external_order_id: str = Field(..., description="Merchant-facing order identifier")
    provider: DeliveryProvider = Field(..., description="Delivery network provider")
    booking_id: UUID | None = Field(default=None, description="Related booking identifier")
    pickup: DeliveryStop
    dropoff: DeliveryStop
    ready_by: datetime | None = Field(default=None, description="Pickup ready timestamp")
    dropoff_deadline: datetime | None = Field(
        default=None, description="Latest acceptable dropoff timestamp"
    )
    tip: Decimal | None = Field(default=None, description="Tip amount to include with the delivery")
    items: list[str] = Field(default_factory=list, description="Line items being delivered")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary metadata forwarded to the provider"
    )


class CourierDetails(BaseModel):
    """Details about the courier fulfilling the delivery."""

    name: str | None = Field(default=None)
    phone: str | None = Field(default=None)


class DeliveryProof(BaseModel):
    """Proof of handoff captured at dropoff."""

    photo_url: AnyUrl | None = None
    signature: str | None = None


class DeliveryResource(BaseModel):
    """API representation of a delivery order."""

    id: UUID
    external_order_id: str
    provider: DeliveryProvider
    status: DeliveryStatus
    provider_delivery_id: str | None = None
    tracking_url: AnyUrl | None = None
    eta: datetime | None = None
    courier: CourierDetails | None = None
    proof: DeliveryProof | None = None


class DeliveryCreateResponse(BaseModel):
    """Response returned after creating a delivery."""

    delivery: DeliveryResource


class DeliveryStatusUpdate(BaseModel):
    """Webhook payload representing a delivery status change."""

    provider: DeliveryProvider
    external_order_id: str | None = Field(default=None)
    provider_delivery_id: str | None = Field(default=None)
    status: str = Field(..., description="Provider-specific status string")
    occurred_at: datetime | None = Field(default=None)
    eta: datetime | None = Field(default=None)
    courier_name: str | None = Field(default=None)
    courier_phone: str | None = Field(default=None)
    proof_photo_url: AnyUrl | None = Field(default=None)
    proof_signature: str | None = Field(default=None)
    tracking_url: AnyUrl | None = Field(default=None)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class OrderStatus(BaseModel):
    """Aggregated status representation for the unified orders endpoint."""

    id: UUID
    external_order_id: str
    provider: DeliveryProvider
    status: DeliveryStatus
    provider_status: str
    last_updated_at: datetime
    eta: datetime | None = None
    tracking_url: AnyUrl | None = None
    courier: CourierDetails | None = None
    proof: DeliveryProof | None = None


class OrdersResponse(BaseModel):
    """Response payload for the unified orders endpoint."""

    orders: list[OrderStatus]
    connectors: dict[str, str]
    reconciliation_accuracy: float = Field(
        default=0.0,
        description="Observed variance between provider and internal status tracking",
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "DeliveryCreateRequest",
    "DeliveryCreateResponse",
    "DeliveryStatusUpdate",
    "DeliveryResource",
    "DeliveryProof",
    "OrdersResponse",
    "OrderStatus",
    "DeliveryStop",
]
