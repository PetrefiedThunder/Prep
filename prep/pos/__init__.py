"""POS integration utilities for Prep."""

from __future__ import annotations

from typing import Any

from .oracle_simphony import FranchiseSyncService, OracleSimphonyClient

__all__ = [
    "OracleSimphonyClient",
    "FranchiseSyncService",
    "POSAnalyticsService",
    "POSIntegrationRepository",
    "SquarePOSConnector",
    "SquarePOSOAuthToken",
    "ToastWebhookProcessor",
]


def __getattr__(name: str) -> Any:  # pragma: no cover - thin import wrapper
    if name == "POSAnalyticsService":
        from .analytics import POSAnalyticsService as attr

        return attr
    if name == "POSIntegrationRepository":
        from .repository import POSIntegrationRepository as attr

        return attr
    if name == "SquarePOSConnector":
        from .square import SquarePOSConnector as attr

        return attr
    if name == "SquarePOSOAuthToken":
        from .square import SquarePOSOAuthToken as attr

        return attr
    if name == "ToastWebhookProcessor":
        from .toast import ToastWebhookProcessor as attr

        return attr
    raise AttributeError(name)
