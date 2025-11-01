"""ORM exports for Prep models."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .db import SessionLocal, engine, get_db_url
from .guid import GUID
from .orm import (
    Base,
    APIUsageEvent,
    Booking,
    BookingStatus,
    COIDocument,
    Integration,
    InventoryItem,
    InventoryLot,
    InventoryTransfer,
    InventoryTransferStatus,
    Kitchen,
    LedgerEntry,
    POSIntegration,
    POSIntegrationStatus,
    POSOrder,
    POSTransaction,
    RecurringBookingTemplate,
    RevenueType,
    SanitationLog,
    StripeWebhookEvent,
    SubscriptionStatus,
    Supplier,
    TaxRecord,
    FeeSchedule,
    RegRequirement,
    User,
    UserRole,
)

if TYPE_CHECKING:  # pragma: no cover - only for static analysis
    from prep.regulatory.models import PolicyDecision as _PolicyDecision

__all__ = [
    "Base",
    "Booking",
    "BookingStatus",
    "COIDocument",
    "Integration",
    "APIUsageEvent",
    "InventoryItem",
    "InventoryLot",
    "InventoryTransfer",
    "InventoryTransferStatus",
    "Kitchen",
    "LedgerEntry",
    "POSIntegration",
    "POSIntegrationStatus",
    "POSOrder",
    "POSTransaction",
    "RecurringBookingTemplate",
    "RevenueType",
    "SanitationLog",
    "StripeWebhookEvent",
    "SubscriptionStatus",
    "Supplier",
    "TaxRecord",
    "FeeSchedule",
    "RegRequirement",
    "User",
    "UserRole",
    "engine",
    "SessionLocal",
    "get_db_url",
    "GUID",
    "PolicyDecision",
]


def __getattr__(name: str) -> Any:
    if name == "PolicyDecision":
        module = import_module("prep.regulatory.models")
        return getattr(module, "PolicyDecision")
    raise AttributeError(name)
