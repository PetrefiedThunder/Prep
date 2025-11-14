"""Command line helpers for ingesting city regulatory data."""

from __future__ import annotations

import argparse
import json
import logging
import os
from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, replace

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.city_regulatory_service.jurisdictions.common.fees import FeeSchedule
from apps.city_regulatory_service.src.models import (
    CityFeeSchedule,
    CityJurisdiction,
)
from libs.safe_import import safe_import

try:  # pragma: no cover - defensive fallback for optional dependencies
    from apps.city_regulatory_service.src.etl import CITY_ADAPTERS, CityETLOrchestrator
except Exception:  # pragma: no cover - import may fail in slim test environments
    CITY_ADAPTERS: Mapping[str, object] = {}

    class CityETLOrchestrator:  # type: ignore[override]
        def __init__(self, _: Session) -> None:
            raise RuntimeError("City ETL orchestration is unavailable in this environment")


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CitySpec:
    """Configuration describing a supported ingestion target."""

    slug: str
    display_name: str
    state: str
    fee_module: str | None = None
    supports_requirements: bool = False


def _slugify(name: str) -> str:
    return "_".join(part for part in name.strip().lower().replace("-", " ").split() if part)


_FEE_MODULES: Sequence[tuple[str, str, str]] = (
    ("San Francisco", "CA", "data.ingestors.sf_dph"),
    ("Oakland", "CA", "data.ingestors.oakland_dph"),
    ("Berkeley", "CA", "data.ingestors.berkeley_dph"),
    ("San Jose", "CA", "data.ingestors.san_jose_dph"),
    ("Palo Alto", "CA", "data.ingestors.palo_alto_dph"),
    ("Joshua Tree", "CA", "data.ingestors.joshua_tree_dph"),
)


def _build_city_specs() -> dict[str, CitySpec]:
    specs: dict[str, CitySpec] = {}

    for display_name, adapter in CITY_ADAPTERS.items():
        slug = _slugify(display_name)
        state = getattr(adapter, "STATE", "").upper()
        specs[slug] = CitySpec(
            slug=slug,
            display_name=display_name,
            state=state,
            supports_requirements=True,
        )

    for display_name, state, module_path in _FEE_MODULES:
        slug = _slugify(display_name)
        state_upper = state.upper()
        existing = specs.get(slug)
        if existing:
            specs[slug] = replace(
                existing, fee_module=module_path, state=state_upper or existing.state
            )
        else:
            specs[slug] = CitySpec(
                slug=slug,
                display_name=display_name,
                state=state_upper,
                fee_module=module_path,
                supports_requirements=False,
            )

    return specs


CITY_SPECS: dict[str, CitySpec] = _build_city_specs()


def _load_fee_schedule(module_path: str) -> FeeSchedule:
    module = safe_import(module_path)
    if not hasattr(module, "make_fee_schedule"):
        raise AttributeError(f"fee ingestor '{module_path}' does not define make_fee_schedule()")
    schedule = module.make_fee_schedule()
    if not isinstance(schedule, FeeSchedule):
        raise TypeError(f"module '{module_path}' returned unexpected type {type(schedule)!r}")
    return schedule


def _ensure_jurisdiction(session: Session, spec: CitySpec) -> CityJurisdiction:
    stmt = select(CityJurisdiction).where(
        CityJurisdiction.city == spec.display_name,
        CityJurisdiction.state == spec.state,
    )
    jurisdiction = session.execute(stmt).scalar_one_or_none()
    if jurisdiction:
        return jurisdiction

    jurisdiction = CityJurisdiction(
        city=spec.display_name,
        state=spec.state,
        data_source="city-cli",
    )
    session.add(jurisdiction)
    session.flush()
    return jurisdiction


def _persist_fee_schedule(
    session: Session, jurisdiction: CityJurisdiction, schedule: FeeSchedule
) -> CityFeeSchedule:
    stmt = select(CityFeeSchedule).where(CityFeeSchedule.jurisdiction_id == jurisdiction.id)
    record = session.execute(stmt).scalar_one_or_none()
    payload = {
        "paperwork": list(schedule.paperwork),
        "fees": [item.dict() for item in schedule.fees],
    }
    if record:
        record.paperwork = payload["paperwork"]
        record.fees = payload["fees"]
        record.jurisdiction_slug = schedule.jurisdiction
    else:
        record = CityFeeSchedule(
            jurisdiction_id=jurisdiction.id,
            jurisdiction_slug=schedule.jurisdiction,
            paperwork=payload["paperwork"],
            fees=payload["fees"],
            data_source="city-cli",
        )
        session.add(record)
    session.flush()
    return record


def run_ingestion(
    cities: Iterable[str] | None,
    *,
    session_factory: Callable[[], Session] | None = None,
    orchestrator_cls: type[CityETLOrchestrator] = CityETLOrchestrator,
    city_specs: Mapping[str, CitySpec] = CITY_SPECS,
) -> MutableMapping[str, dict[str, object]]:
    """Run ingestion for the provided cities returning a structured report."""

    if session_factory is None:
        from prep.models.db import (
            SessionLocal as _SessionLocal,  # pragma: no cover - optional import
        )

        session_factory = _SessionLocal

    selected_slugs = {_slugify(city) for city in cities} if cities else set(city_specs.keys())

    results: MutableMapping[str, dict[str, object]] = {}
    session = session_factory()
    try:
        orchestrator = orchestrator_cls(session)
        for slug in sorted(selected_slugs):
            spec = city_specs.get(slug)
            if not spec:
                logger.warning("Unsupported city requested: %s", slug)
                results[slug] = {
                    "city": slug,
                    "errors": [f"unknown city '{slug}'"],
                }
                continue

            city_result: dict[str, object] = {
                "city": spec.display_name,
                "state": spec.state,
                "errors": [],
            }

            jurisdiction = _ensure_jurisdiction(session, spec)

            if spec.supports_requirements:
                try:
                    stats = orchestrator.run_etl_for_city(spec.display_name)
                    city_result["requirements"] = stats
                except Exception as exc:  # pragma: no cover - defensive
                    session.rollback()
                    logger.exception("Requirement ingestion failed for %s", spec.display_name)
                    city_result.setdefault("requirements", {})
                    city_result["errors"].append(f"requirements: {exc}")
            else:
                city_result["requirements"] = None

            if spec.fee_module:
                try:
                    schedule = _load_fee_schedule(spec.fee_module)
                    record = _persist_fee_schedule(session, jurisdiction, schedule)
                    city_result["fees"] = {
                        "fee_count": len(record.fees or ()),
                        "paperwork_count": len(record.paperwork or ()),
                        "jurisdiction": record.jurisdiction_slug,
                    }
                except Exception as exc:  # pragma: no cover - defensive
                    session.rollback()
                    logger.exception("Fee ingestion failed for %s", spec.display_name)
                    city_result.setdefault("fees", None)
                    city_result["errors"].append(f"fees: {exc}")
            else:
                city_result["fees"] = None

            results[slug] = city_result

        session.commit()
    finally:
        session.close()

    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest city regulatory data")
    parser.add_argument(
        "cities", nargs="*", help="Specific cities to ingest (defaults to all supported)"
    )
    parser.add_argument(
        "--database-url",
        dest="database_url",
        help="Override the SQLAlchemy database URL",
    )
    parser.add_argument(
        "--list",
        dest="list_cities",
        action="store_true",
        help="List supported cities and exit",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    if args.list_cities:
        for spec in sorted(CITY_SPECS.values(), key=lambda item: item.display_name):
            capabilities = []
            if spec.supports_requirements:
                capabilities.append("requirements")
            if spec.fee_module:
                capabilities.append("fees")
            joined = ", ".join(capabilities) if capabilities else "none"
            print(f"{spec.display_name} ({spec.state}) - {joined}")
        return 0

    session_factory: Callable[[], Session] | None = None
    try:
        from prep.models.db import (  # pragma: no cover - optional import
            SessionLocal as _SessionLocal,
            init_db as _init_db,
        )
    except Exception:  # pragma: no cover - optional dependency missing
        _SessionLocal = None
        _init_db = None
    else:
        session_factory = _SessionLocal
        _init_db()

    results = run_ingestion(args.cities, session_factory=session_factory)
    print(json.dumps(results, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover - manual execution
    raise SystemExit(main())
