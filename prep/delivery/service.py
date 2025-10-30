"""Domain service coordinating third-party delivery integrations."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Iterable

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from prep.models.orm import (
    DeliveryComplianceEvent,
    DeliveryOrder,
    DeliveryProvider,
    DeliveryStatus,
    DeliveryStatusEvent,
)
from prep.settings import Settings

from .clients import (
    DoorDashDriveClient,
    DeliveryIntegrationError,
    DeliveryIntegrationResult,
    UberDirectClient,
)
from .schemas import (
    CourierDetails,
    DeliveryCreateRequest,
    DeliveryCreateResponse,
    DeliveryProof,
    DeliveryResource,
    DeliveryStatusUpdate,
    DeliveryStop,
    OrderStatus,
    OrdersResponse,
)

logger = logging.getLogger("prep.delivery.service")


class DeliveryServiceError(Exception):
    """Raised when delivery orchestration fails."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class DeliveryService:
    """Coordinates delivery integrations and persistence."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._doordash = DoorDashDriveClient(settings)
        self._uber = UberDirectClient(settings)

    async def create_delivery(self, payload: DeliveryCreateRequest) -> DeliveryCreateResponse:
        """Create a delivery with the requested provider and persist state."""

        logger.info(
            "Creating delivery", extra={"order_id": payload.external_order_id, "provider": payload.provider.value}
        )

        await self._ensure_unique_order(payload.external_order_id)

        try:
            integration_result = await self._dispatch_create(payload)
        except DeliveryIntegrationError as exc:
            raise DeliveryServiceError(str(exc), status_code=exc.status_code) from exc

        delivery = DeliveryOrder(
            booking_id=payload.booking_id,
            external_order_id=payload.external_order_id,
            provider=payload.provider,
            provider_delivery_id=integration_result.provider_delivery_id,
            status=integration_result.status,
            pickup_address=_format_address(payload.pickup),
            dropoff_address=_format_address(payload.dropoff),
            dropoff_contact={
                "name": payload.dropoff.name,
                "phone": payload.dropoff.phone,
                "metadata": payload.metadata,
            },
            eta=integration_result.eta,
            tracking_url=integration_result.tracking_url,
            courier_name=integration_result.courier_name,
            courier_phone=integration_result.courier_phone,
            last_status_at=datetime.now(UTC),
        )
        self._session.add(delivery)
        self._session.add(
            DeliveryStatusEvent(
                delivery=delivery,
                status=integration_result.status,
                provider_status=integration_result.raw.get("status", integration_result.status.value)
                if integration_result.raw
                else integration_result.status.value,
                occurred_at=datetime.now(UTC),
                raw_payload=integration_result.raw or {},
            )
        )

        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            logger.exception("Duplicate delivery detected", extra={"order_id": payload.external_order_id})
            raise DeliveryServiceError("Delivery already exists", status_code=409) from exc
        except SQLAlchemyError as exc:  # pragma: no cover - commit failures are exceptional
            await self._session.rollback()
            logger.exception("Database error while creating delivery", extra={"order_id": payload.external_order_id})
            raise DeliveryServiceError("Failed to persist delivery", status_code=500) from exc

        logger.info(
            "Delivery created",
            extra={
                "order_id": payload.external_order_id,
                "provider": payload.provider.value,
                "provider_delivery_id": integration_result.provider_delivery_id,
            },
        )

        await self._session.refresh(delivery)
        resource = _serialize_delivery(delivery)
        return DeliveryCreateResponse(delivery=resource)

    async def ingest_status_update(self, update: DeliveryStatusUpdate) -> None:
        """Persist status updates received from provider webhooks."""

        logger.info(
            "Received status update",
            extra={"provider": update.provider.value, "status": update.status, "external_order_id": update.external_order_id},
        )

        delivery = await self._find_delivery(update)
        if delivery is None:
            raise DeliveryServiceError("Delivery not found", status_code=404)

        normalized_status = self._normalize_status(update.provider, update.status)
        occurred_at = update.occurred_at or datetime.now(UTC)

        delivery.status = normalized_status
        delivery.last_status_at = occurred_at
        delivery.eta = update.eta or delivery.eta
        delivery.tracking_url = update.tracking_url or delivery.tracking_url
        if update.provider_delivery_id and not delivery.provider_delivery_id:
            delivery.provider_delivery_id = update.provider_delivery_id
        if update.courier_name:
            delivery.courier_name = update.courier_name
        if update.courier_phone:
            delivery.courier_phone = update.courier_phone
        if update.proof_photo_url:
            delivery.proof_photo_url = str(update.proof_photo_url)
        if update.proof_signature:
            delivery.proof_signature = update.proof_signature

        event = DeliveryStatusEvent(
            delivery=delivery,
            status=normalized_status,
            provider_status=update.status,
            occurred_at=occurred_at,
            raw_payload=dict(update.raw_payload),
        )
        self._session.add(event)

        if normalized_status == DeliveryStatus.DELIVERED:
            compliance_event = DeliveryComplianceEvent(
                delivery=delivery,
                courier_identity=update.courier_name or "unknown",
                verification_type="handoff",
                verification_reference=update.proof_signature,
                occurred_at=occurred_at,
                metadata={
                    "courier_phone": update.courier_phone,
                    "proof_photo_url": str(update.proof_photo_url) if update.proof_photo_url else None,
                    "provider_status": update.status,
                },
            )
            self._session.add(compliance_event)

        try:
            await self._session.commit()
        except SQLAlchemyError as exc:  # pragma: no cover - commit failures are exceptional
            await self._session.rollback()
            logger.exception(
                "Database error while saving status update",
                extra={"provider": update.provider.value, "status": update.status},
            )
            raise DeliveryServiceError("Failed to persist status update", status_code=500) from exc

        logger.info(
            "Delivery status updated",
            extra={
                "order_id": delivery.external_order_id,
                "provider": delivery.provider.value,
                "status": normalized_status.value,
            },
        )

    async def list_orders(self) -> OrdersResponse:
        """Return a unified view of all delivery orders."""

        deliveries = await self._load_deliveries()
        orders = [_serialize_order_status(delivery) for delivery in deliveries]
        accuracy = _calculate_reconciliation_accuracy(deliveries)
        connectors = {
            DeliveryProvider.DOORDASH.value: "authenticated" if self._connector_ready(self._doordash) else "unconfigured",
            DeliveryProvider.UBER.value: "authenticated" if self._connector_ready(self._uber) else "unconfigured",
        }
        return OrdersResponse(orders=orders, connectors=connectors, reconciliation_accuracy=accuracy)

    async def _ensure_unique_order(self, external_order_id: str) -> None:
        stmt: Select[DeliveryOrder] = select(DeliveryOrder).where(DeliveryOrder.external_order_id == external_order_id)
        existing = await self._session.scalar(stmt)
        if existing:
            raise DeliveryServiceError("Delivery already exists", status_code=409)

    async def _dispatch_create(self, payload: DeliveryCreateRequest) -> DeliveryIntegrationResult:
        if payload.provider == DeliveryProvider.DOORDASH:
            self._assert_credentials(self._doordash.is_configured, "DoorDash Drive")
            request_payload = _build_doordash_payload(payload)
            return await self._doordash.create_delivery(request_payload)
        if payload.provider == DeliveryProvider.UBER:
            self._assert_credentials(self._uber.is_configured, "Uber Direct")
            request_payload = _build_uber_payload(payload)
            return await self._uber.create_delivery(request_payload)
        raise DeliveryServiceError("Unsupported delivery provider", status_code=400)

    async def _find_delivery(self, update: DeliveryStatusUpdate) -> DeliveryOrder | None:
        conditions = []
        if update.external_order_id:
            conditions.append(DeliveryOrder.external_order_id == update.external_order_id)
        if update.provider_delivery_id:
            conditions.append(DeliveryOrder.provider_delivery_id == update.provider_delivery_id)
        if not conditions:
            return None
        stmt = (
            select(DeliveryOrder)
            .where(DeliveryOrder.provider == update.provider, *conditions)
            .options(
                selectinload(DeliveryOrder.status_events),
                selectinload(DeliveryOrder.compliance_events),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def _normalize_status(self, provider: DeliveryProvider, status: str) -> DeliveryStatus:
        if provider == DeliveryProvider.DOORDASH:
            return _map_doordash_status(status)
        if provider == DeliveryProvider.UBER:
            return _map_uber_status(status)
        return DeliveryStatus.CREATED

    async def _load_deliveries(self) -> Iterable[DeliveryOrder]:
        stmt = (
            select(DeliveryOrder)
            .options(selectinload(DeliveryOrder.status_events), selectinload(DeliveryOrder.compliance_events))
            .order_by(DeliveryOrder.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    def _connector_ready(self, client: DoorDashDriveClient | UberDirectClient) -> bool:
        return True if self._settings.use_fixtures else client.is_configured

    def _assert_credentials(self, configured: bool, provider: str) -> None:
        if not configured and not self._settings.use_fixtures:
            raise DeliveryServiceError(f"{provider} credentials are not configured", status_code=500)

    def verify_doordash_signature(self, payload: bytes, signature: str | None) -> None:
        """Verify the authenticity of a DoorDash webhook payload."""

        try:
            self._doordash.verify_webhook(payload, signature)
        except DeliveryIntegrationError as exc:
            raise DeliveryServiceError(str(exc), status_code=exc.status_code) from exc


def _serialize_delivery(delivery: DeliveryOrder) -> DeliveryResource:
    return DeliveryResource(
        id=delivery.id,
        external_order_id=delivery.external_order_id,
        provider=delivery.provider,
        status=delivery.status,
        provider_delivery_id=delivery.provider_delivery_id,
        tracking_url=delivery.tracking_url,
        eta=delivery.eta,
        courier=CourierDetails(name=delivery.courier_name, phone=delivery.courier_phone),
        proof=DeliveryProof(
            photo_url=delivery.proof_photo_url,
            signature=delivery.proof_signature,
        )
        if delivery.proof_photo_url or delivery.proof_signature
        else None,
    )


def _serialize_order_status(delivery: DeliveryOrder) -> OrderStatus:
    latest_event = delivery.status_events[-1] if delivery.status_events else None
    provider_status = latest_event.provider_status if latest_event else delivery.status.value
    occurred_at = latest_event.occurred_at if latest_event else delivery.updated_at
    return OrderStatus(
        id=delivery.id,
        external_order_id=delivery.external_order_id,
        provider=delivery.provider,
        status=delivery.status,
        provider_status=provider_status,
        last_updated_at=occurred_at,
        eta=delivery.eta,
        tracking_url=delivery.tracking_url,
        courier=CourierDetails(name=delivery.courier_name, phone=delivery.courier_phone),
        proof=DeliveryProof(
            photo_url=delivery.proof_photo_url,
            signature=delivery.proof_signature,
        )
        if delivery.proof_photo_url or delivery.proof_signature
        else None,
    )


def _format_address(stop: DeliveryStop) -> str:
    components = [stop.address]
    if stop.city:
        components.append(stop.city)
    if stop.state:
        components.append(stop.state)
    if stop.postal_code:
        components.append(stop.postal_code)
    return ", ".join(filter(None, components))


def _calculate_reconciliation_accuracy(deliveries: Iterable[DeliveryOrder]) -> float:
    deliveries = list(deliveries)
    if not deliveries:
        return 0.0
    mismatched = 0
    total_events = 0
    for delivery in deliveries:
        if not delivery.status_events:
            continue
        total_events += 1
        latest = delivery.status_events[-1]
        if latest.status != delivery.status:
            mismatched += 1
    if total_events == 0:
        return 0.0
    return mismatched / total_events


def _map_doordash_status(status: str) -> DeliveryStatus:
    mapping = {
        "created": DeliveryStatus.CREATED,
        "pending": DeliveryStatus.CREATED,
        "confirmed": DeliveryStatus.DISPATCHED,
        "enroute_pickup": DeliveryStatus.DISPATCHED,
        "pickup": DeliveryStatus.DISPATCHED,
        "picked_up": DeliveryStatus.IN_TRANSIT,
        "enroute_dropoff": DeliveryStatus.IN_TRANSIT,
        "delivered": DeliveryStatus.DELIVERED,
        "cancelled": DeliveryStatus.CANCELLED,
        "returned": DeliveryStatus.RETURNED,
        "failed": DeliveryStatus.FAILED,
    }
    return mapping.get(status.lower(), DeliveryStatus.CREATED)


def _map_uber_status(status: str) -> DeliveryStatus:
    mapping = {
        "processing": DeliveryStatus.CREATED,
        "accepted": DeliveryStatus.DISPATCHED,
        "courier_en_route_to_pickup": DeliveryStatus.DISPATCHED,
        "courier_arrived_at_pickup": DeliveryStatus.DISPATCHED,
        "picked_up": DeliveryStatus.IN_TRANSIT,
        "en_route_to_dropoff": DeliveryStatus.IN_TRANSIT,
        "delivered": DeliveryStatus.DELIVERED,
        "return_in_progress": DeliveryStatus.RETURNED,
        "cancelled": DeliveryStatus.CANCELLED,
        "delivery_failed": DeliveryStatus.FAILED,
    }
    return mapping.get(status.lower(), DeliveryStatus.CREATED)


def _build_doordash_payload(payload: DeliveryCreateRequest) -> dict:
    body = {
        "external_delivery_id": payload.external_order_id,
        "pickup_address": payload.pickup.address,
        "pickup_business_name": payload.pickup.name,
        "pickup_phone_number": payload.pickup.phone,
        "dropoff_address": payload.dropoff.address,
        "dropoff_business_name": payload.dropoff.name,
        "dropoff_phone_number": payload.dropoff.phone,
        "order_value": str(payload.tip or 0),
        "items": [{"name": item} for item in payload.items],
    }
    if payload.ready_by:
        body["pickup_time"] = payload.ready_by.isoformat()
    if payload.dropoff_deadline:
        body["dropoff_deadline"] = payload.dropoff_deadline.isoformat()
    body.update(payload.metadata)
    return body


def _build_uber_payload(payload: DeliveryCreateRequest) -> dict:
    body = {
        "external_delivery_id": payload.external_order_id,
        "pickup": {
            "name": payload.pickup.name,
            "address": payload.pickup.address,
            "contact": {"phone_number": payload.pickup.phone},
        },
        "dropoff": {
            "name": payload.dropoff.name,
            "address": payload.dropoff.address,
            "contact": {"phone_number": payload.dropoff.phone},
        },
        "tip": str(payload.tip or 0),
        "items": [{"name": item} for item in payload.items],
    }
    if payload.ready_by:
        body["pickup_ready"] = payload.ready_by.isoformat()
    if payload.dropoff_deadline:
        body["dropoff_deadline"] = payload.dropoff_deadline.isoformat()
    if payload.metadata:
        body["metadata"] = payload.metadata
    return body


__all__ = ["DeliveryService", "DeliveryServiceError"]
