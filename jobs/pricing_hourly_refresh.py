"""Hourly job that refreshes ML-powered pricing recommendations."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

try:  # pragma: no cover - optional dependency in minimal test environments
    from sqlalchemy import select  # type: ignore
    from sqlalchemy.orm import Session  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - allow running without SQLAlchemy installed
    select = None  # type: ignore
    Session = Any  # type: ignore

try:  # pragma: no cover - optional in unit tests
    from prep.models.db import SessionLocal  # type: ignore
    from prep.models.orm import Kitchen  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    SessionLocal = None  # type: ignore
    Kitchen = Any  # type: ignore

from apps.pricing import UtilizationMetrics, build_default_engine

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]


@dataclass(slots=True)
class PricingRefreshSummary:
    """Summary emitted after a pricing refresh run."""

    total_kitchens: int
    updated: int
    timestamp: datetime

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_kitchens": self.total_kitchens,
            "updated": self.updated,
            "timestamp": self.timestamp.isoformat(),
        }


def _load_kitchens(session: Session) -> Iterable[Kitchen]:
    if select is None or Kitchen is Any:  # pragma: no cover - SQLAlchemy not installed
        raise RuntimeError("SQLAlchemy is required to refresh pricing")
    stmt = select(Kitchen)
    return session.execute(stmt).scalars()


def _build_metrics(kitchen: Kitchen) -> UtilizationMetrics:
    pricing_payload = kitchen.pricing or {}
    try:
        utilization = float(pricing_payload.get("utilization_rate", 1.0))
    except (TypeError, ValueError):
        utilization = 1.0
    try:
        active = int(pricing_payload.get("active_bookings", 0))
    except (TypeError, ValueError):
        active = 0
    try:
        cancellation = float(pricing_payload.get("cancellation_rate", 0.0))
    except (TypeError, ValueError):
        cancellation = 0.0
    return UtilizationMetrics(
        utilization_rate=utilization,
        active_bookings=active,
        cancellation_rate=cancellation,
    )


def refresh_pricing(
    *,
    session_factory: SessionFactory | None = SessionLocal,
    now: datetime | None = None,
) -> PricingRefreshSummary:
    """Refresh pricing recommendations across all kitchens.

    The job runs once per hour and writes the applied discount and refresh timestamp
    back to ``Kitchen.pricing`` to ensure downstream components (checkpoint C3) can
    continue using the existing payload structure.
    """

    if session_factory is None:
        raise RuntimeError("A session factory is required to refresh pricing")

    engine = build_default_engine()
    session = session_factory()
    updated = 0
    timestamp = now or datetime.now(timezone.utc)
    kitchens: list[Kitchen] = []

    try:
        kitchens = list(_load_kitchens(session))
        for kitchen in kitchens:
            metrics = _build_metrics(kitchen)
            decision = engine.evaluate(metrics)
            if decision.discount <= 0:
                continue

            pricing_payload = dict(kitchen.pricing or {})
            pricing_payload["discount_percent"] = decision.discount
            pricing_payload["pricing_rules"] = decision.applied_rules
            pricing_payload["last_refreshed_at"] = timestamp.isoformat()
            kitchen.pricing = pricing_payload
            updated += 1

        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Hourly pricing refresh failed")
        raise
    finally:
        session.close()

    summary = PricingRefreshSummary(
        total_kitchens=len(kitchens),
        updated=updated,
        timestamp=timestamp,
    )
    logger.info("Pricing refresh complete", extra=summary.as_dict())
    return summary


__all__ = ["PricingRefreshSummary", "refresh_pricing"]
