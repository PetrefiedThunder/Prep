"""Background job implementations for the Prep platform."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - only for static analysis
    from .expiry_check import ExpirySummary, run_expiry_check, run_expiry_check_async
    from .pricing_hourly_refresh import (
        DefaultPricingStrategy,
        PricingRefreshSummary,
        SCHEDULE_CRON,
        beat_schedule_entry,
        run_pricing_refresh,
        run_pricing_refresh_async,
    )


__all__ = [
    "DefaultPricingStrategy",
    "ExpirySummary",
    "PricingRefreshSummary",
    "SCHEDULE_CRON",
    "beat_schedule_entry",
    "run_expiry_check",
    "run_expiry_check_async",
    "run_pricing_refresh",
    "run_pricing_refresh_async",
]


def __getattr__(name: str) -> Any:
    if name in {"ExpirySummary", "run_expiry_check", "run_expiry_check_async"}:
        module = import_module("jobs.expiry_check")
        return getattr(module, name)
    if name in {
        "DefaultPricingStrategy",
        "PricingRefreshSummary",
        "SCHEDULE_CRON",
        "beat_schedule_entry",
        "run_pricing_refresh",
        "run_pricing_refresh_async",
    }:
        module = import_module("jobs.pricing_hourly_refresh")
        return getattr(module, name)
    raise AttributeError(f"module 'jobs' has no attribute {name!r}")


__all__ = list(sorted(set(__all__)))
