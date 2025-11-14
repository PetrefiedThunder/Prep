"""Integration shim for San Francisco Planning Department zoning lookups."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ZoningLookupResult:
    zoning_use_district: str | None
    kitchen_use_allowed: bool
    manual_review_required: bool
    message: str


class SanFranciscoPlanningAPI:
    """Mockable zoning lookup client."""

    ALLOWED_DISTRICTS = {"NC-3", "NC-2", "NCT", "PDR", "CMUO"}

    def resolve(self, address: str) -> ZoningLookupResult:
        address = address.lower().strip()
        if "unknown" in address or not address:
            return ZoningLookupResult(
                zoning_use_district=None,
                kitchen_use_allowed=True,
                manual_review_required=True,
                message="Manual zoning review required",
            )
        if "industrial" in address:
            return ZoningLookupResult(
                zoning_use_district="PDR",
                kitchen_use_allowed=True,
                manual_review_required=False,
                message="Production district",
            )
        return ZoningLookupResult(
            zoning_use_district="NC-2",
            kitchen_use_allowed=True,
            manual_review_required=False,
            message="Neighborhood commercial",
        )
