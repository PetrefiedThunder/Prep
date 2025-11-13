"""Background job implementations for the Prep platform."""

from __future__ import annotations

from typing import Any

__all__ = ["ExpirySummary", "run_expiry_check", "run_expiry_check_async"]


def __getattr__(name: str) -> Any:  # pragma: no cover - thin import shim
    if name not in __all__:
        raise AttributeError(name)
    from .expiry_check import ExpirySummary, run_expiry_check, run_expiry_check_async

    exports = {
        "ExpirySummary": ExpirySummary,
        "run_expiry_check": run_expiry_check,
        "run_expiry_check_async": run_expiry_check_async,
    }
    return exports[name]


def __dir__() -> list[str]:  # pragma: no cover - delegated to stdlib introspection
    return sorted(__all__)


from typing import TYPE_CHECKING

from libs.safe_import import safe_import_attr

if TYPE_CHECKING:  # pragma: no cover - only for static analysis
    from .expiry_check import ExpirySummary, run_expiry_check, run_expiry_check_async
    from .pricing_hourly_refresh import (
        SCHEDULE_CRON,
        DefaultPricingStrategy,
        PricingRefreshSummary,
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
        attr = safe_import_attr("jobs.expiry_check", name)
        if attr is None:
            raise AttributeError(f"module 'jobs' has no attribute {name!r}")
        return attr
    if name in {
        "DefaultPricingStrategy",
        "PricingRefreshSummary",
        "SCHEDULE_CRON",
        "beat_schedule_entry",
        "run_pricing_refresh",
        "run_pricing_refresh_async",
    }:
        attr = safe_import_attr("jobs.pricing_hourly_refresh", name)
        if attr is None:
            raise AttributeError(f"module 'jobs' has no attribute {name!r}")
        return attr
    raise AttributeError(f"module 'jobs' has no attribute {name!r}")


__all__ = sorted(set(__all__))
from .expiry_check import ExpirySummary, run_expiry_check, run_expiry_check_async
from .reconciliation_engine import (
    ReconciliationEntry,
    ReconciliationReport,
    run_pos_reconciliation,
)

__all__ = [
    "ExpirySummary",
    "ReconciliationEntry",
    "ReconciliationReport",
    "run_expiry_check",
    "run_expiry_check_async",
    "run_pos_reconciliation",
]
