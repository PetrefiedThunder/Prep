"""Backward-compatible shim importing the city fee router."""

from __future__ import annotations

from api.routes.city_fees import router

__all__ = ["router"]

