"""API router package for the Prep platform."""

from . import (
    admin_regulatory,
    auth,
    bookings,
    deliveries,
    kitchens,
    orders,
    regulatory,
    search,
)

__all__ = [
    "admin_regulatory",
    "auth",
    "bookings",
    "deliveries",
    "kitchens",
    "orders",
    "regulatory",
    "search",
]
