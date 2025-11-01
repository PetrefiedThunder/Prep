"""Domain services for the San Francisco tax service."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session

from apps.sf_regulatory_service.config import get_compliance_config
from apps.sf_regulatory_service.models import SFHostProfile, SFTaxLedger, SFTaxReport
from apps.sf_regulatory_service.services import LedgerService
from apps.sf_regulatory_service import metrics

from .schemas import TaxCalculateRequest, TaxCalculateResponse, TaxLine, TaxReportResponse

SF_CITY_NAME = "San Francisco"


def _to_float(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


class TaxService:
    """Compute San Francisco taxes for bookings."""

    def __init__(self, session: Session):
        self.session = session
        config = get_compliance_config()
        tax_config = config.get("tax", {}) if config else {}
        self.crt_rate = float(tax_config.get("crt_rate", 0.035))
        self.grt_threshold = float(tax_config.get("grt_threshold", 0))
        self.ledger_service = LedgerService(session)

    def calculate(self, request: TaxCalculateRequest) -> TaxCalculateResponse:
        if request.city != SF_CITY_NAME:
            return TaxCalculateResponse(lines=[], totalTax=0.0)

        host = self.session.get(SFHostProfile, request.host_kitchen_id)
        if host is None:
            raise ValueError("Host profile not found")

        lines: List[TaxLine] = []
        total_tax = 0.0
        booking_amount = float(request.booking_amount)
        classification = host.tax_classification

        if classification == "lease_sublease":
            amount = round(booking_amount * self.crt_rate, 2)
            line = TaxLine(
                jurisdiction="SF-CRT",
                rate=self.crt_rate,
                basis=booking_amount,
                amount=amount,
            )
            lines.append(line)
            total_tax += amount
            self.ledger_service.record_tax_line(request.booking_id, line.jurisdiction, line.basis, line.rate, line.amount)
            metrics.sf_tax_lines_total.labels(jurisdiction="SF-CRT").inc()
        else:
            advisory = "Track gross receipts for GRT threshold"
            line = TaxLine(
                jurisdiction="SF-GRT",
                rate=0.0,
                basis=booking_amount,
                amount=0.0,
                advisory=advisory,
            )
            lines.append(line)
            self.ledger_service.record_tax_line(request.booking_id, line.jurisdiction, line.basis, line.rate, line.amount)
            metrics.sf_tax_lines_total.labels(jurisdiction="SF-GRT").inc()

        return TaxCalculateResponse(
            lines=lines,
            totalTax=round(total_tax, 2),
            classification=classification,
            grtThreshold=self.grt_threshold,
        )

    def generate_report(self, period: str) -> TaxReportResponse:
        start, end = self._parse_period(period)
        ledger_entries = (
            self.session.query(SFTaxLedger)
            .filter(
                and_(
                    SFTaxLedger.created_at >= datetime.combine(start, datetime.min.time()),
                    SFTaxLedger.created_at < datetime.combine(end + timedelta(days=1), datetime.min.time()),
                )
            )
            .all()
        )
        total_tax = sum(_to_float(entry.tax_amount) for entry in ledger_entries)
        total_basis = sum(_to_float(entry.tax_basis) for entry in ledger_entries)

        report = (
            self.session.query(SFTaxReport)
            .filter(
                and_(SFTaxReport.period_start == start, SFTaxReport.period_end == end),
            )
            .one_or_none()
        )

        if report is None:
            report = SFTaxReport(
                period_start=start,
                period_end=end,
                total_tax_collected=total_tax,
                total_booking_amount=total_basis,
                file_status="prepared",
                generated_at=datetime.utcnow(),
            )
            self.session.add(report)
        else:
            report.total_tax_collected = total_tax
            report.total_booking_amount = total_basis
            report.file_status = "prepared"
            report.generated_at = datetime.utcnow()

        csv_lines = ["booking_id,jurisdiction,tax_basis,tax_rate,tax_amount"]
        for entry in ledger_entries:
            csv_lines.append(
                f"{entry.booking_id},{entry.tax_jurisdiction},{_to_float(entry.tax_basis):.2f},{_to_float(entry.tax_rate):.4f},{_to_float(entry.tax_amount):.2f}"
            )
        csv_content = "\n".join(csv_lines)

        return TaxReportResponse(
            periodStart=start,
            periodEnd=end,
            totalTaxCollected=round(total_tax, 2),
            totalBookingAmount=round(total_basis, 2),
            fileStatus=report.file_status,
            generatedAt=report.generated_at,
            csv=csv_content,
        )

    @staticmethod
    def _parse_period(period: str) -> Tuple[date, date]:
        try:
            year_str, quarter_str = period.split("-")
            if not quarter_str.startswith("Q"):
                raise ValueError
            year = int(year_str)
            quarter = int(quarter_str[1:])
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError("Period must be formatted as YYYY-Q#") from exc

        if quarter not in {1, 2, 3, 4}:  # pragma: no cover - defensive
            raise ValueError("Quarter must be between 1 and 4")

        start_month = 3 * (quarter - 1) + 1
        start = date(year, start_month, 1)
        if quarter == 4:
            end = date(year, 12, 31)
        else:
            next_start = date(year, start_month + 3, 1)
            end = next_start - date.resolution
        return start, end
