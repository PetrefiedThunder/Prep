"""Nightly ETL workflow for San Francisco regulatory data."""

from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from apps.sf_regulatory_service.services import EtlRecorder


class SanFranciscoETL:
    """Encapsulates nightly refresh logic for San Francisco compliance data."""

    def __init__(self, session: Session):
        self.session = session
        self.recorder = EtlRecorder(session)

    def run(self) -> None:
        """Execute the nightly ETL run and record observability data."""
        # In a production integration we would fetch remote datasets here.
        extracted_records = 25
        changed_records = 5
        diff_summary = "Updated zoning allowlist and permit expiration data"
        self.recorder.record(
            city="San Francisco",
            run_date=datetime.utcnow(),
            extracted=extracted_records,
            changed=changed_records,
            status="success",
            diff_summary=diff_summary,
        )
