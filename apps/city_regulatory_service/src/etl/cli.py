"""Command line interface for running city regulatory ETL jobs."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from sqlalchemy.orm import Session

from apps.city_regulatory_service.src.etl import CITY_ADAPTERS, CityETLOrchestrator

logger = logging.getLogger(__name__)


def _canonicalize_city(city: str, adapters: Mapping[str, type]) -> tuple[str, str | None]:
    """Return the canonical adapter key for ``city`` if available."""

    normalized = city.strip()
    if not normalized:
        return city, None

    lookup = {key.lower(): key for key in adapters.keys()}
    return city, lookup.get(normalized.lower())


def _ensure_unique(sequence: Sequence[str]) -> list[str]:
    """Return ``sequence`` preserving order while removing duplicates."""

    seen: set[str] = set()
    unique: list[str] = []
    for item in sequence:
        if item not in seen:
            unique.append(item)
            seen.add(item)
    return unique


def _default_session_factory() -> Callable[[], Session]:
    from prep.models.db import SessionLocal  # imported lazily for easier testing

    return SessionLocal


def _initialise_schema() -> None:
    from prep.models.db import init_db  # imported lazily to avoid global side effects

    init_db()


def run_ingestion(
    *,
    cities: Sequence[str] | None = None,
    session_factory: Callable[[], Session] | None = None,
    orchestrator_cls: type[CityETLOrchestrator] = CityETLOrchestrator,
    adapters: Mapping[str, type] = CITY_ADAPTERS,
) -> dict[str, dict[str, Any]]:
    """Execute the ETL process for the requested cities.

    Args:
        cities: Optional iterable of city names to ingest. When omitted, all
            available adapters are executed.
        session_factory: Callable that returns a SQLAlchemy session. This is
            injectable for tests so they can provide an in-memory database.
        orchestrator_cls: Class used to orchestrate ETL runs. Dependency
            injection makes it simpler to verify behaviour in tests.
        adapters: Mapping of canonical city names to adapter classes. Tests can
            provide a pared down registry to avoid relying on real adapters.

    Returns:
        Mapping of city name to ETL statistics or error metadata.
    """

    requested_cities = _ensure_unique(list(cities)) if cities else list(adapters.keys())

    results: dict[str, dict[str, Any]] = {}
    factory = session_factory or _default_session_factory()
    session = factory()
    try:
        orchestrator = orchestrator_cls(session)

        for requested in requested_cities:
            original, canonical = _canonicalize_city(requested, adapters)
            if canonical is None:
                logger.warning("City '%s' is not supported; skipping", original)
                results[original] = {
                    "status": "skipped",
                    "reason": "unsupported_city",
                }
                continue

            try:
                stats = orchestrator.run_etl_for_city(canonical)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("ETL run failed for %s", canonical)
                results[canonical] = {"status": "failed", "error": str(exc)}
            else:
                results[canonical] = {"status": "completed", **stats}
    finally:
        session.close()

    return results


def _build_parser() -> argparse.ArgumentParser:
    """Create the argument parser used by :func:`main`."""

    parser = argparse.ArgumentParser(
        description="Run Prep city regulatory ETL jobs",
    )
    parser.add_argument(
        "--city",
        dest="cities",
        action="append",
        help=(
            "City name to ingest. Provide multiple --city flags to run more "
            "than one city. Defaults to all supported cities when omitted."
        ),
    )
    parser.add_argument(
        "--list-cities",
        action="store_true",
        help="List supported cities and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of human-friendly logs",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point used by ``python -m ...etl.cli``."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_cities:
        for city in CITY_ADAPTERS.keys():
            print(city)
        return 0

    _initialise_schema()
    results = run_ingestion(cities=args.cities)

    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        for city, data in results.items():
            status = data.get("status", "unknown")
            print(f"{city}: {status}")
            if status == "completed":
                processed = data.get("processed", 0)
                inserted = data.get("inserted", 0)
                updated = data.get("updated", 0)
                print(f"  processed={processed} inserted={inserted} updated={updated}")
                if data.get("errors"):
                    print(f"  errors: {data['errors']}")
            elif status == "skipped":
                print(f"  reason: {data.get('reason', 'unspecified')}")
            else:
                print(f"  error: {data.get('error', 'unknown error')}")

    has_failures = any(entry.get("status") in {"failed"} for entry in results.values())
    return 1 if has_failures else 0


if __name__ == "__main__":  # pragma: no cover - CLI hook
    raise SystemExit(main())
