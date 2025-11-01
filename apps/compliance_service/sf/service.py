"""Domain service implementing San Francisco specific compliance logic."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Iterable, Sequence
from uuid import UUID

from .models import (
    BookingFlowRecord,
    BookingValidationRequest,
    CityETLRunRecord,
    FacilityType,
    FireComplianceRecord,
    HealthPermitRecord,
    HostComplianceFieldStatus,
    HostComplianceStatus,
    HostKitchenRecord,
    MetricsSnapshot,
    TaxBreakdown,
    TaxCalculationRequest,
    TaxClassification,
    TaxReportRecord,
    WasteComplianceRecord,
    ZoningVerificationRecord,
)

_APPROVED_COOKING_ZONES: frozenset[str] = frozenset(
    {
        "C-2",
        "C-3",
        "M-1",
        "M-2",
        "PDR-1-D",
        "PDR-1-G",
        "PDR-2",
        "UMU",
    }
)

_GREASE_SERVICE_INTERVAL_DAYS = 365
_FIRE_SUPPRESSION_INTERVAL_DAYS = 365
_SMALL_BUSINESS_THRESHOLD = 2_190_000
_COMMERCIAL_RENTS_TAX_RATE = 0.035


class SFComplianceService:
    """Coordinator that stores records and evaluates SF compliance logic."""

    def __init__(self, *, approved_zones: Iterable[str] | None = None) -> None:
        self._approved_zones: frozenset[str] = (
            frozenset(z.upper() for z in approved_zones)
            if approved_zones
            else _APPROVED_COOKING_ZONES
        )
        self._hosts: dict[UUID, HostKitchenRecord] = {}
        self._zoning_records: dict[str, ZoningVerificationRecord] = {}
        self._tax_reports: dict[str, TaxReportRecord] = {}
        self._health_permits: dict[str, HealthPermitRecord] = {}
        self._fire_records: dict[UUID, FireComplianceRecord] = {}
        self._waste_records: dict[UUID, WasteComplianceRecord] = {}
        self._etl_runs: list[CityETLRunRecord] = []
        self._metrics = defaultdict(float)
        self._lock = asyncio.Lock()

    async def upsert_host(self, record: HostKitchenRecord) -> HostComplianceStatus:
        async with self._lock:
            self._hosts[record.id] = record
            status = self._evaluate_host(record)
            self._metrics["sf_last_compliance_status"] = status.overall_status == "compliant"
            return status

    async def get_host_status(self, host_id: UUID) -> HostComplianceStatus:
        record = self._hosts.get(host_id)
        if not record:
            raise KeyError(str(host_id))
        return self._evaluate_host(record)

    def _evaluate_host(self, record: HostKitchenRecord) -> HostComplianceStatus:
        today = date.today()
        checklist: list[HostComplianceFieldStatus] = []
        issues: list[str] = []

        def add_issue(field: str, status: str, message: str) -> None:
            checklist.append(
                HostComplianceFieldStatus(field=field, status=status, message=message)
            )
            issues.append(message)

        def add_ok(field: str, message: str | None = None) -> None:
            checklist.append(HostComplianceFieldStatus(field=field, status="ok", message=message))

        if record.registration_expiry_date <= today:
            add_issue(
                "sf_business_registration_certificate",
                "expired",
                "Business registration certificate is expired.",
            )
        else:
            add_ok("sf_business_registration_certificate")

        if record.facility_type == FacilityType.COOKING_KITCHEN:
            if not record.sf_health_permit_number:
                add_issue(
                    "sf_health_permit_number",
                    "missing",
                    "Cooking kitchens must provide an SF health permit number.",
                )
            elif not record.health_permit_expiry_date or record.health_permit_expiry_date <= today:
                add_issue(
                    "health_permit_expiry_date",
                    "expired",
                    "Health permit must have a future expiry date.",
                )
            else:
                add_ok("sf_health_permit_number")
        else:
            add_ok("sf_health_permit_number")

        zone = record.zoning_use_district.upper()
        if zone not in self._approved_zones:
            add_issue(
                "zoning_use_district",
                "invalid",
                "Zoning district is not approved for kitchen operations.",
            )
        else:
            add_ok("zoning_use_district")

        if record.facility_type == FacilityType.COOKING_KITCHEN:
            if not record.fire_suppression_certificate:
                add_issue(
                    "fire_suppression_certificate",
                    "missing",
                    "Cooking kitchens require a fire suppression certificate.",
                )
            elif not record.suppression_inspection_last_date or (
                today - record.suppression_inspection_last_date
            ) > timedelta(days=_FIRE_SUPPRESSION_INTERVAL_DAYS):
                add_issue(
                    "suppression_inspection_last_date",
                    "expired",
                    "Fire suppression inspection is older than one year.",
                )
            else:
                add_ok("fire_suppression_certificate")
        else:
            add_ok("fire_suppression_certificate")

        if record.facility_type in (
            FacilityType.COOKING_KITCHEN,
            FacilityType.MOBILE_FOOD_COMMISSARY,
        ):
            if not record.grease_trap_certificate:
                add_issue(
                    "grease_trap_certificate",
                    "missing",
                    "Grease trap certificate is required for this facility type.",
                )
            elif not record.grease_service_last_date or (
                today - record.grease_service_last_date
            ) > timedelta(days=_GREASE_SERVICE_INTERVAL_DAYS):
                add_issue(
                    "grease_service_last_date",
                    "expired",
                    "Grease trap service record is older than one year.",
                )
            else:
                add_ok("grease_trap_certificate")
        else:
            add_ok("grease_trap_certificate")

        add_ok("tax_classification")
        if record.tax_classification == TaxClassification.LEASE_SUBLEASE:
            if record.lease_gross_receipts_ytd is None:
                add_issue(
                    "lease_gross_receipts_ytd",
                    "missing",
                    "Lease/sublease hosts must report YTD gross receipts for tax calculations.",
                )
            else:
                add_ok("lease_gross_receipts_ytd")
        else:
            add_ok("lease_gross_receipts_ytd")

        if not issues:
            overall_status = "compliant"
        elif any(item.status in {"missing", "invalid"} for item in checklist if item.status != "ok"):
            overall_status = "blocked"
        else:
            overall_status = "needs_attention"

        return HostComplianceStatus(
            host_id=record.id,
            overall_status=overall_status,  # type: ignore[arg-type]
            checklist=checklist,
            outstanding_issues=issues,
        )

    async def record_zoning_check(
        self, record: ZoningVerificationRecord
    ) -> ZoningVerificationRecord:
        async with self._lock:
            key = record.address.lower()
            self._zoning_records[key] = record
            if not record.kitchen_use_allowed:
                self._metrics["sf_zoning_checks_failures"] += 1
            return record

    async def perform_zoning_check(
        self, *,
        host_id: UUID,
        address: str,
        zoning_use_district: str | None,
        business_type: str,
    ) -> ZoningVerificationRecord:
        normalized_zone = zoning_use_district.upper() if zoning_use_district else "UNKNOWN"
        allowed = normalized_zone in self._approved_zones
        manual_review = normalized_zone == "UNKNOWN"
        message = None
        if manual_review:
            message = "Zoning lookup unavailable; manual review required."
        elif not allowed:
            message = "Use district is not approved for kitchen operations."
        record = ZoningVerificationRecord(
            hostKitchenId=host_id,
            address=address,
            zoning_use_district=normalized_zone,
            kitchen_use_allowed=allowed,
            manual_review_required=manual_review,
            verification_date=datetime.now(tz=UTC),
            message=message,
        )
        return await self.record_zoning_check(record)

    async def calculate_tax(self, request: TaxCalculationRequest) -> TaxBreakdown:
        exemptions: list[str] = []
        tax_rate = 0.0
        tax_amount = 0.0
        notes = None

        if request.tax_classification == TaxClassification.LEASE_SUBLEASE:
            tax_rate = _COMMERCIAL_RENTS_TAX_RATE
            tax_amount = round(request.booking_amount * tax_rate, 2)
            self._metrics["sf_tax_collections_total"] += tax_amount
        else:
            host = self._hosts.get(request.hostKitchenId) if request.hostKitchenId else None
            receipts = host.lease_gross_receipts_ytd if host else None
            if receipts is not None and receipts < _SMALL_BUSINESS_THRESHOLD:
                exemptions.append("gross_receipts_small_business_exemption")
                notes = "Host under SF gross receipts threshold; no tax due."
            else:
                tax_rate = 0.0
                tax_amount = 0.0
                notes = "Service providers currently require manual tax assessment."

        return TaxBreakdown(
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            exemptions_applied=tuple(exemptions),
            notes=notes,
        )

    async def store_tax_report(self, report: TaxReportRecord) -> TaxReportRecord:
        async with self._lock:
            key = f"{report.jurisdiction}:{report.period_start.isoformat()}:{report.period_end.isoformat()}"
            self._tax_reports[key] = report
            return report

    async def get_tax_report(self, *, period_start: date, period_end: date, jurisdiction: str) -> TaxReportRecord:
        key = f"{jurisdiction}:{period_start.isoformat()}:{period_end.isoformat()}"
        report = self._tax_reports.get(key)
        if not report:
            raise KeyError(key)
        return report

    async def upsert_health_permit(self, record: HealthPermitRecord) -> HealthPermitRecord:
        async with self._lock:
            self._health_permits[record.permit_number] = record
            self._metrics["sf_permit_validations_total"] += 1
            return record

    async def get_health_permit(self, permit_number: str) -> HealthPermitRecord:
        record = self._health_permits.get(permit_number)
        if not record:
            raise KeyError(permit_number)
        return record

    async def upsert_fire_record(self, record: FireComplianceRecord) -> FireComplianceRecord:
        async with self._lock:
            self._fire_records[record.hostKitchenId] = record
            return record

    async def get_fire_record(self, host_id: UUID) -> FireComplianceRecord:
        record = self._fire_records.get(host_id)
        if not record:
            raise KeyError(str(host_id))
        return record

    async def upsert_waste_record(self, record: WasteComplianceRecord) -> WasteComplianceRecord:
        async with self._lock:
            self._waste_records[record.hostKitchenId] = record
            return record

    async def get_waste_record(self, host_id: UUID) -> WasteComplianceRecord:
        record = self._waste_records.get(host_id)
        if not record:
            raise KeyError(str(host_id))
        return record

    async def validate_booking(self, request: BookingValidationRequest) -> BookingFlowRecord:
        try:
            host_status = await self.get_host_status(request.hostKitchenId)
        except KeyError:
            return BookingFlowRecord(
                bookingId=request.bookingId,
                hostKitchenId=request.hostKitchenId,
                renterId=request.renterId,
                prebooking_compliance_status="blocked",
                compliance_issues=["Host does not exist in SF compliance registry."],
            )

        issues = host_status.outstanding_issues
        if host_status.overall_status == "compliant":
            status = "passed"
        elif host_status.overall_status == "needs_attention":
            status = "flagged"
        else:
            status = "blocked"
            self._metrics["sf_compliance_blocked_bookings"] += 1

        return BookingFlowRecord(
            bookingId=request.bookingId,
            hostKitchenId=request.hostKitchenId,
            renterId=request.renterId,
            prebooking_compliance_status=status,  # type: ignore[arg-type]
            compliance_issues=list(issues),
        )

    async def record_etl_run(self, record: CityETLRunRecord) -> CityETLRunRecord:
        async with self._lock:
            self._etl_runs.insert(0, record)
            self._etl_runs = self._etl_runs[:50]
            return record

    async def recent_etl_runs(self, limit: int = 10) -> Sequence[CityETLRunRecord]:
        return tuple(self._etl_runs[:limit])

    async def metrics(self) -> MetricsSnapshot:
        return MetricsSnapshot(
            sf_permit_validations_total=int(self._metrics.get("sf_permit_validations_total", 0)),
            sf_zoning_checks_failures=int(self._metrics.get("sf_zoning_checks_failures", 0)),
            sf_tax_collections_total=float(self._metrics.get("sf_tax_collections_total", 0.0)),
            sf_compliance_blocked_bookings=int(
                self._metrics.get("sf_compliance_blocked_bookings", 0)
            ),
            sf_api_response_time_seconds=None,
        )


service = SFComplianceService()
