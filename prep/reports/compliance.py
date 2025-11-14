"""Utilities for generating compliance manifest reports."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from prep.database.connection import AsyncSessionLocal
from prep.models import Booking, COIDocument, Kitchen, SanitationLog

DEFAULT_REPORT_PATH = Path("reports/compliance.pdf")


async def generate_compliance_manifest(output_path: Path | None = None) -> Path:
    """Generate a PDF manifest summarizing compliance activity."""

    if output_path is None:
        output_path = DEFAULT_REPORT_PATH

    output_path.parent.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as session:
        kitchens = (
            (
                await session.execute(
                    select(Kitchen)
                    .options(selectinload(Kitchen.sanitation_logs))
                    .order_by(Kitchen.name.asc())
                )
            )
            .scalars()
            .all()
        )
        deliveries = (
            (
                await session.execute(
                    select(Booking)
                    .where(Booking.start_time >= datetime.now(UTC) - timedelta(days=30))
                    .order_by(Booking.start_time.desc())
                )
            )
            .scalars()
            .all()
        )
        certificates = (
            (await session.execute(select(COIDocument).order_by(COIDocument.created_at.desc())))
            .scalars()
            .all()
        )

    pdf = _build_manifest_pdf(kitchens, deliveries, certificates)
    pdf.output(str(output_path))
    return output_path


def _build_manifest_pdf(
    kitchens: Iterable[Kitchen],
    deliveries: Iterable[Booking],
    certificates: Iterable[COIDocument],
) -> FPDF:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Prep Compliance Manifest", ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 8, f"Generated at: {datetime.now(UTC).isoformat()}Z")
    pdf.ln(2)

    _render_kitchen_section(pdf, kitchens)
    _render_deliveries_section(pdf, deliveries)
    _render_certificate_section(pdf, certificates)

    return pdf


def _render_kitchen_section(pdf: FPDF, kitchens: Iterable[Kitchen]) -> None:
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Delivery Kitchens", ln=True)
    pdf.set_font("Helvetica", "", 10)

    for kitchen in kitchens:
        header = (
            f"{kitchen.name} — {kitchen.city or 'Unknown City'}, {kitchen.state or 'Unknown State'}"
        )
        pdf.multi_cell(0, 6, header)
        pdf.multi_cell(
            0,
            5,
            f"  Delivery only: {'Yes' if kitchen.delivery_only else 'No'} | Permits: {', '.join(kitchen.permit_types or []) or 'n/a'}",
        )
        last_log = _latest_sanitation_log(kitchen.sanitation_logs)
        if last_log:
            pdf.multi_cell(
                0,
                5,
                f"  Sanitation: {last_log.logged_at.isoformat()} ({last_log.status})",
            )
        else:
            pdf.multi_cell(0, 5, "  Sanitation: No logs on file")
        pdf.ln(2)


def _render_deliveries_section(pdf: FPDF, deliveries: Iterable[Booking]) -> None:
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Recent Deliveries", ln=True)
    pdf.set_font("Helvetica", "", 10)

    deliveries = list(deliveries)
    if not deliveries:
        pdf.multi_cell(0, 6, "No deliveries recorded in the last 30 days.")
        pdf.ln(2)
        return

    for booking in deliveries[:25]:
        window = f"{booking.start_time.isoformat()} → {booking.end_time.isoformat()}"
        pdf.multi_cell(
            0,
            5,
            f"Kitchen {booking.kitchen_id} | Customer {booking.customer_id} | {window}",
        )
    pdf.ln(2)


def _render_certificate_section(pdf: FPDF, certificates: Iterable[COIDocument]) -> None:
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Insurance Certificates", ln=True)
    pdf.set_font("Helvetica", "", 10)

    certificates = list(certificates)
    if not certificates:
        pdf.multi_cell(0, 6, "No insurance certificates generated yet.")
        pdf.ln(2)
        return

    for certificate in certificates[:25]:
        expiry = certificate.expiry_date.isoformat() if certificate.expiry_date else "n/a"
        pdf.multi_cell(
            0,
            5,
            f"Policy {certificate.policy_number or 'n/a'} | Insured {certificate.insured_name or 'n/a'} | Expires {expiry}",
        )
    pdf.ln(2)


def _latest_sanitation_log(logs: Iterable[SanitationLog]) -> SanitationLog | None:
    latest: SanitationLog | None = None
    for log in logs:
        if latest is None or (log.logged_at and log.logged_at > latest.logged_at):
            latest = log
    return latest


__all__ = ["generate_compliance_manifest"]
