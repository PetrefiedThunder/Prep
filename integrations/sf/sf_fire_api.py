"""Integration shim for San Francisco Fire Department certificate verification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class FireCertificate:
    certificate: str
    last_inspection_date: date
    system_type: str


class SanFranciscoFireAPI:
    """Mockable client for fire suppression verification."""

    def verify(self, certificate: str, last_inspection_date: date, system_type: str) -> bool:
        if not certificate:
            return False
        if certificate.startswith("TEMP"):
            return False
        return (date.today() - last_inspection_date) <= timedelta(days=365)
