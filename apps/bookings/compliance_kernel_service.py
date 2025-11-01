"""Adapters that integrate the municipal compliance kernel into booking flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Dict, List, Optional

from regengine.cities.compliance_kernel import (
    ComplianceEvaluation,
    ComplianceResult,
    MunicipalComplianceKernel,
)

try:  # pragma: no cover - optional dependency for runtime integration
    from prep.models.orm import Booking  # type: ignore
except Exception:  # pragma: no cover - fallback when ORM isn't available
    Booking = None  # type: ignore

from apps.sf_regulatory_service.models import SFHostProfile


@dataclass(frozen=True)
class KernelDecision:
    """Lightweight representation of the kernel decision for a booking."""

    status: str
    issues: List[str]
    evaluation: ComplianceEvaluation


class SanFranciscoBookingComplianceService:
    """Evaluate San Francisco bookings using the municipal compliance kernel."""

    def __init__(self, kernel: Optional[MunicipalComplianceKernel] = None) -> None:
        self._kernel = kernel or MunicipalComplianceKernel("san_francisco")

    def evaluate(
        self,
        *,
        profile: SFHostProfile,
        booking: Optional["Booking"] = None,
    ) -> KernelDecision:
        """Return the kernel-backed decision for the provided booking context."""

        kitchen_data = self._build_kitchen_data(profile)
        maker_data = self._build_maker_data(profile)
        booking_data = self._build_booking_data(booking)

        evaluation = self._kernel.evaluate_booking(
            kitchen_data=kitchen_data,
            maker_data=maker_data,
            booking_data=booking_data,
        )
        status = self._map_status(evaluation.result)
        issues = self._collect_issues(evaluation)
        return KernelDecision(status=status, issues=issues, evaluation=evaluation)

    @staticmethod
    def _map_status(result: ComplianceResult) -> str:
        if result is ComplianceResult.DENY:
            return "blocked"
        if result is ComplianceResult.CONDITIONS:
            return "flagged"
        return "passed"

    @staticmethod
    def _collect_issues(evaluation: ComplianceEvaluation) -> List[str]:
        issues: List[str] = [violation.message for violation in evaluation.violations]
        issues.extend(f"Condition: {condition}" for condition in evaluation.conditions)
        issues.extend(f"Warning: {warning.message}" for warning in evaluation.warnings)
        return issues

    @staticmethod
    def _build_kitchen_data(profile: SFHostProfile) -> Dict[str, object]:
        permits: List[Dict[str, object]] = [
            _permit_record("shared_kitchen", profile.business_registration_expires),
            _permit_record("health_permit", profile.health_permit_expires),
            _permit_record("ventilation", profile.business_registration_expires),
        ]

        if profile.fire_suppression_certificate:
            fire_expires = profile.business_registration_expires
            if profile.fire_last_inspection:
                fire_expires = profile.fire_last_inspection + timedelta(days=365)
            permits.append(
                _permit_record(
                    "fire",
                    fire_expires,
                )
            )

        kitchen_data: Dict[str, object] = {
            "permits": permits,
            "zoning": {
                "district": profile.zoning_use_district,
                "neighborhood_notice_doc_id": profile.business_registration_certificate or None,
            },
            "ada_accessible": profile.facility_type != "mobile_food_commissary",
        }

        if profile.grease_last_service:
            kitchen_data["grease"] = {
                "last_service_at": _coerce_to_iso(profile.grease_last_service)
            }
        else:
            kitchen_data["grease"] = {}
        return kitchen_data

    @staticmethod
    def _build_maker_data(profile: SFHostProfile) -> Dict[str, object]:
        insurance_payload = {
            "general_liability_cents": 150_000_000,
            "aggregate_cents": 250_000_000,
            "additional_insured_text": "City and County of San Francisco",
        }

        if profile.lease_gross_receipts_ytd:
            projected_liability = int(float(profile.lease_gross_receipts_ytd) * 100)
            insurance_payload["general_liability_cents"] = max(
                insurance_payload["general_liability_cents"], projected_liability
            )

        return {
            "insurance": insurance_payload,
            "requires_ada_access": profile.facility_type == "commissary_non_cooking",
        }

    @staticmethod
    def _build_booking_data(booking: Optional["Booking"]) -> Dict[str, object]:
        if booking is not None and hasattr(booking, "start_time") and hasattr(booking, "end_time"):
            start = _ensure_datetime(booking.start_time)
            end = _ensure_datetime(booking.end_time)
        else:
            start = _default_booking_start()
            end = start + timedelta(hours=4)

        duration = max((end - start).total_seconds() / 3600, 0.0)
        return {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "hours": duration,
            "product_type": "shared_kitchen",
        }


def _permit_record(kind: str, expires: date | datetime | None) -> Dict[str, object]:
    record: Dict[str, object] = {"kind": kind, "status": "active"}
    expires_iso = _coerce_to_iso(expires)
    if expires_iso:
        record["expires_at"] = expires_iso
    return record


def _coerce_to_iso(value: date | datetime | None) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.combine(value, time.min)
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt.isoformat()


def _ensure_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _default_booking_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(hour=10, minute=0, second=0, microsecond=0)


__all__ = [
    "KernelDecision",
    "SanFranciscoBookingComplianceService",
]
