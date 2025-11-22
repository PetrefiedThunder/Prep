"""Integration helpers for third-party services."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from .accounting import AvalaraClient, QuickBooksConnector, XeroConnector
    from .docusign_client import DocuSignClient, DocuSignError, poll_envelope, send_sublease

__all__ = [
    "AvalaraClient",
    "QuickBooksConnector",
    "XeroConnector",
    "DocuSignClient",
    "DocuSignError",
    "poll_envelope",
    "send_sublease",
]


def __getattr__(name: str) -> Any:  # pragma: no cover - dynamic import
    if name in {"AvalaraClient", "QuickBooksConnector", "XeroConnector"}:
        from .accounting import AvalaraClient, QuickBooksConnector, XeroConnector

        return {
            "AvalaraClient": AvalaraClient,
            "QuickBooksConnector": QuickBooksConnector,
            "XeroConnector": XeroConnector,
        }[name]
    if name in {"DocuSignClient", "DocuSignError", "poll_envelope", "send_sublease"}:
        from .docusign_client import (
            DocuSignClient,
            DocuSignError,
            poll_envelope,
            send_sublease,
        )

        return {
            "DocuSignClient": DocuSignClient,
            "DocuSignError": DocuSignError,
            "poll_envelope": poll_envelope,
            "send_sublease": send_sublease,
        }[name]
    raise AttributeError(f"module 'integrations' has no attribute {name!r}")
