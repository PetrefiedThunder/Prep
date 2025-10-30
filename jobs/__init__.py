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
