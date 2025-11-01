"""Threaded orchestrator that schedules city ETL integrations."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional, Protocol

from sqlalchemy.orm import Session

from apps.sf_regulatory_service.database import SessionLocal
from apps.sf_regulatory_service.services import EtlRecorder
from integrations.sf import SanFranciscoETL

from . import metrics

logger = logging.getLogger(__name__)

_EtlFactory = Callable[[Session], "SupportsRun"]


class SupportsRun(Protocol):
    """Minimal protocol for ETL implementations used by the orchestrator."""

    def run(self) -> None:
        """Execute the ETL workflow."""


@dataclass(frozen=True)
class OrchestratedRun:
    """Metadata captured for each orchestrated ETL execution."""

    city: str
    status: str
    started_at: datetime
    finished_at: datetime
    error: Optional[str] = None


class CityEtlOrchestrator:
    """Schedule ETL runs for supported cities and expose runtime metrics."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session] = SessionLocal,
        etl_factory: _EtlFactory = SanFranciscoETL,
        city_name: str = "San Francisco",
        interval_seconds: int = 3600,
    ) -> None:
        self._session_factory = session_factory
        self._etl_factory = etl_factory
        self._city_name = city_name
        self._interval_seconds = interval_seconds
        self._run_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_run: Optional[OrchestratedRun] = None
        self._last_success_at: Optional[datetime] = None

    @property
    def city(self) -> str:
        """Return the canonical city name handled by this orchestrator."""

        return self._city_name

    @property
    def interval_seconds(self) -> int:
        """Return the configured cadence for scheduled runs."""

        return self._interval_seconds

    @property
    def last_run(self) -> Optional[OrchestratedRun]:
        """Return metadata about the most recent run."""

        return self._last_run

    @property
    def last_success_at(self) -> Optional[datetime]:
        """Return when the last successful run finished, if known."""

        return self._last_success_at

    def start(self) -> None:
        """Start the background scheduler thread."""

        if self._thread and self._thread.is_alive():  # pragma: no cover - defensive
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="city-etl-orchestrator", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the background scheduler to stop."""

        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None

    def _run_loop(self) -> None:  # pragma: no cover - relies on time based scheduling
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except RuntimeError:
                logger.warning("ETL run skipped because another execution is still in progress")
            except Exception:  # pragma: no cover - logged for observability
                logger.exception("Unexpected error while running the city ETL orchestrator")
            finally:
                self._stop_event.wait(self._interval_seconds)

    def run_once(self) -> OrchestratedRun:
        """Execute the ETL workflow immediately."""

        acquired = self._run_lock.acquire(blocking=False)
        if not acquired:
            raise RuntimeError("An ETL run is already in progress")

        try:
            started_at = datetime.utcnow()
            status = "success"
            error: Optional[str] = None

            session = self._session_factory()
            try:
                etl = self._etl_factory(session)
                etl.run()
                session.commit()
            except Exception as exc:  # pragma: no cover - exceptions captured for metrics
                session.rollback()
                status = "failure"
                error = str(exc)
                logger.exception("San Francisco ETL run failed")
                self._record_failure(error)
            finally:
                session.close()

            finished_at = datetime.utcnow()
            run = OrchestratedRun(
                city=self._city_name,
                status=status,
                started_at=started_at,
                finished_at=finished_at,
                error=error,
            )

            metrics.city_etl_runs_total.labels(city=self._city_name, status=status).inc()
            metrics.city_etl_last_run_timestamp.labels(city=self._city_name).set(finished_at.timestamp())
            metrics.city_etl_run_duration_seconds.labels(city=self._city_name).observe(
                max(0.0, (finished_at - started_at).total_seconds())
            )

            if status == "success":
                self._last_success_at = finished_at
                metrics.city_etl_last_success_timestamp.labels(city=self._city_name).set(
                    finished_at.timestamp()
                )

            metrics.update_freshness_gauge(self._city_name, self._last_success_at)
            self._last_run = run
            return run
        finally:
            self._run_lock.release()

    def _record_failure(self, message: str) -> None:
        """Persist a failure record so it surfaces in observability tables."""

        failure_session = self._session_factory()
        try:
            recorder = EtlRecorder(failure_session)
            recorder.record(
                city=self._city_name,
                run_date=datetime.utcnow(),
                extracted=0,
                changed=0,
                status="failure",
                diff_summary=message,
            )
            failure_session.commit()
        except Exception:  # pragma: no cover - defensive logging
            failure_session.rollback()
            logger.exception("Failed to persist ETL failure record")
        finally:
            failure_session.close()
