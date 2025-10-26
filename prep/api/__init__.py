"""API router package for the Prep platform."""

from . import (
    admin_regulatory,
    auth,
    bookings,
    kitchens,
    regulatory,
    search,
)

__all__ = [
    "admin_regulatory",
    "auth",
    "bookings",
    "kitchens",
    "regulatory",
    "search",
]
from . import auth, kitchens, regulatory

__all__ = ["auth", "kitchens", "regulatory"]
