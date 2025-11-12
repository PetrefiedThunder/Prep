"""Integration helpers for third-party services."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from .docusign_client import poll_envelope, send_sublease

__all__ = ["poll_envelope", "send_sublease"]


def __getattr__(name: str) -> Any:  # pragma: no cover - dynamic import
    if name == "poll_envelope":
        from .docusign_client import poll_envelope as func

        return func
    if name == "send_sublease":
        from .docusign_client import send_sublease as func

        return func
    raise AttributeError(f"module 'integrations' has no attribute {name!r}")


from .accounting import AvalaraClient, QuickBooksConnector, XeroConnector
from .docusign_client import poll_envelope, send_sublease

__all__ = [
    "AvalaraClient",
    "QuickBooksConnector",
    "XeroConnector",
    "poll_envelope",
    "send_sublease",
]
