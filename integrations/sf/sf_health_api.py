"""Integration shim for the San Francisco Department of Public Health."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional


@dataclass
class HealthPermitRecord:
    permit_number: str
    facility_type: str
    status: str
    expiry_date: date
    verification_method: str


class SanFranciscoHealthAPI:
    """Mockable client for SF health permit lookups."""

    def lookup_permit(self, permit_number: str, facility_type: str, address: str) -> Optional[HealthPermitRecord]:
        permit_number = permit_number.strip()
        if not permit_number:
            return None
        if permit_number.startswith("X"):
            return HealthPermitRecord(
                permit_number=permit_number,
                facility_type=facility_type,
                status="revoked",
                expiry_date=date.today() - timedelta(days=1),
                verification_method="manual_review",
            )
        return HealthPermitRecord(
            permit_number=permit_number,
            facility_type=facility_type,
            status="valid",
            expiry_date=date.today() + timedelta(days=365),
            verification_method="api",
        )
