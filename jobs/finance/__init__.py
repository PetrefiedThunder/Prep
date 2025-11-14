"""Finance job scheduling utilities and metadata."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

__all__ = [
    "NIGHTLY_CRON",
    "FinanceJobSchedule",
    "ensure_nightly_schedule",
]

logger = logging.getLogger(__name__)

NIGHTLY_CRON = "0 2 * * *"


@dataclass(frozen=True, slots=True)
class FinanceJobSchedule:
    """Metadata describing a finance job schedule."""

    name: str
    description: str
    cron: str = NIGHTLY_CRON

    @classmethod
    def with_default_cron(
        cls, *, name: str, description: str, cron: str | None = None
    ) -> FinanceJobSchedule:
        """Create a schedule ensuring a nightly cron is present."""

        resolved_cron = ensure_nightly_schedule(cron, job_name=name)
        return cls(name=name, description=description, cron=resolved_cron)


def ensure_nightly_schedule(cron: str | None, *, job_name: str) -> str:
    """Return a cron string, defaulting to the nightly cadence when missing."""

    if cron:
        return cron

    logger.info(
        "Missing cron schedule for finance job; defaulting to nightly cadence.",
        extra={"job_name": job_name, "cron": NIGHTLY_CRON},
    )
    return NIGHTLY_CRON
