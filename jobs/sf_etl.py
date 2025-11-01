"""Nightly ETL entrypoint for San Francisco compliance refresh."""

from __future__ import annotations

from contextlib import closing

from sqlalchemy.orm import Session

from apps.sf_regulatory_service.database import SessionLocal, init_db
from integrations.sf import SanFranciscoETL


def run_sf_etl() -> None:
    """Run the nightly San Francisco ETL workflow."""
    init_db()
    with closing(SessionLocal()) as session:  # type: ignore[arg-type]
        etl = SanFranciscoETL(session)
        etl.run()


if __name__ == "__main__":  # pragma: no cover
    run_sf_etl()
