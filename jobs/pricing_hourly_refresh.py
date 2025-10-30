"""Hourly pricing refresh job and scheduler metadata."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Callable, Iterable, Protocol

try:  # pragma: no cover - optional dependency import guard
    from sqlalchemy import select  # type: ignore
    from sqlalchemy.orm import Session  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - allow running without SQLAlchemy installed
    select = None  # type: ignore
    Session = Any  # type: ignore

from prep.monitoring.observability import EnterpriseObservability
from prep.models.db import SessionLocal
from prep.models.orm import Kitchen
from prep.pricing import store_pricing_status

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]


class PricingStrategy(Protocol):
    """Protocol describing the pricing refresh strategy."""

    def build_payload(self, kitchen: Kitchen, *, refreshed_at: datetime) -> dict[str, Any] | None:
        ...


@dataclass(slots=True)
class PricingRefreshSummary:
    """Summary of an hourly pricing refresh run."""

    processed: int
    updated: int
    skipped: int
    failures: int
    refreshed_at: datetime
    errors: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "processed": self.processed,
            "updated": self.updated,
            "skipped": self.skipped,
            "failures": self.failures,
            "refreshed_at": self.refreshed_at.isoformat(),
            "errors": list(self.errors),
        }


class DefaultPricingStrategy:
    """Naive pricing strategy that enriches pricing metadata."""

    adjustment_factor: Decimal = Decimal("0.08")
    weekend_premium: Decimal = Decimal("0.12")

    def build_payload(self, kitchen: Kitchen, *, refreshed_at: datetime) -> dict[str, Any] | None:
        hourly_rate = getattr(kitchen, "hourly_rate", None)
        if hourly_rate is None:
            return None

        base = Decimal(hourly_rate)
        recommended = (base * (Decimal("1.0") + self.adjustment_factor)).quantize(Decimal("0.01"))
        weekend = (base * (Decimal("1.0") + self.weekend_premium)).quantize(Decimal("0.01"))

        return {
            "base_rate": str(base),
            "recommended_rate": str(recommended),
            "weekend_rate": str(weekend),
            "trust_score": getattr(kitchen, "trust_score", None),
            "last_refreshed_at": refreshed_at.isoformat(),
        }


def _load_refresh_candidates(session: Session) -> Iterable[Kitchen]:
    if select is None:  # pragma: no cover - guard when SQLAlchemy is not installed
        raise RuntimeError("SQLAlchemy is required to load pricing refresh candidates")

    stmt = select(Kitchen).where(Kitchen.published.is_(True))
    result = session.execute(stmt)
    return result.scalars().all()


def _persist_updates(session: Session, kitchens: Iterable[Kitchen]) -> None:
    for kitchen in kitchens:
        session.add(kitchen)
    session.commit()


def run_pricing_refresh(
    *,
    session_factory: SessionFactory = SessionLocal,
    strategy: PricingStrategy | None = None,
    observability: EnterpriseObservability | None = None,
) -> PricingRefreshSummary:
    """Rebuild pricing metadata for published kitchens."""

    if session_factory is None:
        raise RuntimeError("A session_factory must be provided when SQLAlchemy is unavailable")

    refreshed_at = datetime.now(UTC)
    strategy = strategy or DefaultPricingStrategy()
    observability = observability or EnterpriseObservability()

    start_time = time.perf_counter()
    errors: list[str] = []
    processed = updated = skipped = failures = 0

    session = session_factory()
    try:
        kitchens = list(_load_refresh_candidates(session))
        processed = len(kitchens)
        updated_models: list[Kitchen] = []

        for kitchen in kitchens:
            try:
                payload = strategy.build_payload(kitchen, refreshed_at=refreshed_at)
            except Exception as exc:  # pragma: no cover - strategy-specific failure
                failures += 1
                error_message = f"kitchen={getattr(kitchen, 'id', 'unknown')}: {exc}"
                logger.exception("Failed to build pricing payload", extra={"kitchen_id": getattr(kitchen, "id", None)})
                errors.append(error_message)
                continue

            if payload is None:
                skipped += 1
                continue

            pricing = dict(getattr(kitchen, "pricing", {}) or {})
            pricing.update(payload)
            kitchen.pricing = pricing
            updated_models.append(kitchen)
            updated += 1

        if updated_models:
            _persist_updates(session, updated_models)
    except Exception as exc:
        session.rollback()
        failures += 1
        errors.append(str(exc))
        logger.exception("Pricing refresh failed")
        raise
    finally:
        session.close()

    duration = time.perf_counter() - start_time
    success = failures == 0
    summary = PricingRefreshSummary(
        processed=processed,
        updated=updated,
        skipped=skipped,
        failures=failures,
        refreshed_at=refreshed_at,
        errors=errors,
    )

    observability.metrics.set_gauge(
        "jobs.pricing_hourly_refresh.last_run_timestamp", refreshed_at.timestamp()
    )
    observability.record_job_result(
        "pricing_hourly_refresh",
        success=success,
        duration_seconds=duration,
        metadata={
            "processed": processed,
            "updated": updated,
            "skipped": skipped,
            "failures": failures,
        },
    )

    status_payload = summary.as_dict()
    status_payload.update({"duration_seconds": duration, "status": "success" if success else "failed"})
    asyncio.run(store_pricing_status(status_payload))

    logger.info("Pricing refresh completed", extra=summary.as_dict())
    return summary


async def run_pricing_refresh_async(
    *,
    session_factory: SessionFactory = SessionLocal,
    strategy: PricingStrategy | None = None,
    observability: EnterpriseObservability | None = None,
) -> PricingRefreshSummary:
    """Async wrapper around :func:`run_pricing_refresh` for scheduler integration."""

    return await asyncio.to_thread(
        run_pricing_refresh,
        session_factory=session_factory,
        strategy=strategy,
        observability=observability,
    )


# Scheduler metadata for integration with Celery beat or Airflow
SCHEDULE_CRON = "0 * * * *"  # top of every hour


def beat_schedule_entry() -> dict[str, Any]:
    """Return a Celery beat-style schedule entry for the job."""

    return {
        "task": "jobs.pricing_hourly_refresh.run_pricing_refresh_async",
        "schedule": {"type": "crontab", "minute": "0", "hour": "*"},
        "options": {"queue": "pricing"},
    }


__all__ = [
    "DefaultPricingStrategy",
    "PricingRefreshSummary",
    "beat_schedule_entry",
    "run_pricing_refresh",
    "run_pricing_refresh_async",
    "SCHEDULE_CRON",
]
