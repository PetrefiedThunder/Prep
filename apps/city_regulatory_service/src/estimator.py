"""Helpers for assembling regulatory requirement bundles and estimating costs."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

try:
    from prep.regulatory.models import CityAgency, CityJurisdiction, CityRequirement
except Exception:  # pragma: no cover - fallback for minimal test environments
    import uuid

    from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String
    from sqlalchemy.orm import declarative_base

    _FallbackBase = declarative_base()

    class CityJurisdiction(_FallbackBase):  # type: ignore[redefinition]
        __tablename__ = "city_jurisdictions"

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        city = Column(String, nullable=False)
        state = Column(String(2), nullable=False)
        county = Column(String, nullable=True)

    class CityAgency(_FallbackBase):  # type: ignore[redefinition]
        __tablename__ = "city_agencies"

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        jurisdiction_id = Column(String, ForeignKey("city_jurisdictions.id"), nullable=False)
        name = Column(String, nullable=False)
        agency_type = Column(String, nullable=True)

    class CityRequirement(_FallbackBase):  # type: ignore[redefinition]
        __tablename__ = "city_requirements"

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        jurisdiction_id = Column(String, ForeignKey("city_jurisdictions.id"), nullable=False)
        agency_id = Column(String, ForeignKey("city_agencies.id"))
        requirement_id = Column(String, nullable=False)
        requirement_label = Column(String, nullable=False)
        requirement_type = Column(String, nullable=False)
        applies_to = Column(JSON, default=list)
        required_documents = Column(JSON, default=list)
        submission_channel = Column(String)
        application_url = Column(String)
        inspection_required = Column(Boolean, default=False)
        renewal_frequency = Column(String)
        fee_amount = Column(String)
        fee_schedule = Column(String)
        fee_details = Column(JSON, default=dict)
        rules = Column(JSON, default=dict)
        enforcement_mechanism = Column(String)
        penalties = Column(JSON, default=dict)
        source_url = Column(String)
        last_updated = Column(DateTime, default=datetime.utcnow)
        is_active = Column(Boolean, default=True)

from .models.requirements import (
    FeeItem,
    FeeSchedule,
    Jurisdiction,
    RequirementRecord,
    RequirementsBundle,
)

logger = logging.getLogger(__name__)

_CURRENCY_CLEANER = re.compile(r"[^0-9.\-]")

_CADENCE_KEYWORDS: Mapping[str, str] = {
    "monthly": "monthly",
    "per month": "monthly",
    "quarterly": "quarterly",
    "per quarter": "quarterly",
    "semi-annual": "semi_annual",
    "semiannual": "semi_annual",
    "biannual": "semi_annual",
    "annual": "annual",
    "annually": "annual",
    "per year": "annual",
    "per annum": "annual",
}

_INCREMENTAL_KEYWORDS: Mapping[str, str] = {
    "per inspection": "per_inspection",
    "per reinspection": "per_reinspection",
    "per application": "per_application",
    "per permit": "per_permit",
    "per visit": "per_inspection",
}


def _parse_fee_amount_to_cents(value: object) -> int | None:
    if value in (None, "", "unknown"):
        return None

    if isinstance(value, (int, float)):
        amount = float(value)
    else:
        text = str(value).strip()
        if not text:
            return None
        cleaned = _CURRENCY_CLEANER.sub("", text)
        if not cleaned or cleaned in {"-", "-.", ".-"}:
            return None
        try:
            amount = float(cleaned)
        except ValueError:
            logger.debug("Unable to parse fee amount '%s'", text)
            return None

    cents = int(round(amount * 100))
    return cents if cents >= 0 else None


def _infer_fee_metadata(schedule: str | None, renewal: str | None) -> tuple[str, str | None, bool, str | None]:
    text_parts = [schedule or "", renewal or ""]
    joined = " ".join(part.lower() for part in text_parts)

    incremental = False
    unit: str | None = None
    for phrase, unit_candidate in _INCREMENTAL_KEYWORDS.items():
        if phrase in joined:
            incremental = True
            unit = unit_candidate
            break

    cadence: str | None = None
    for phrase, canonical in _CADENCE_KEYWORDS.items():
        if phrase in joined:
            cadence = canonical
            break

    if cadence:
        kind = "recurring"
    elif renewal and renewal.lower() not in {"", "unknown", "one_time"}:
        kind = "recurring"
        cadence = _CADENCE_KEYWORDS.get(renewal.lower())
    elif schedule and "renewal" in schedule.lower():
        kind = "recurring"
    else:
        kind = "one_time"

    if incremental:
        kind = "recurring"

    return kind, cadence, incremental, unit


def _build_requirement_record(
    requirement: CityRequirement,
    agency: CityAgency | None,
) -> RequirementRecord:
    applies_to_raw = [str(item) for item in (requirement.applies_to or []) if item]
    applies_to = tuple(dict.fromkeys(applies_to_raw)) if applies_to_raw else ("all",)
    if not applies_to:
        applies_to = ("all",)

    required_documents_raw = [
        str(item) for item in (requirement.required_documents or []) if item
    ]
    required_documents = tuple(dict.fromkeys(required_documents_raw))

    fee_amount_cents = _parse_fee_amount_to_cents(requirement.fee_amount)

    return RequirementRecord(
        id=requirement.requirement_id or str(requirement.id),
        label=requirement.requirement_label,
        requirement_type=requirement.requirement_type,
        applies_to=applies_to,
        required_documents=required_documents,
        submission_channel=requirement.submission_channel,
        application_url=requirement.application_url,
        inspection_required=bool(requirement.inspection_required),
        renewal_frequency=requirement.renewal_frequency,
        fee_schedule=requirement.fee_schedule,
        fee_amount_cents=fee_amount_cents,
        agency_name=getattr(agency, "name", None),
        agency_type=getattr(agency, "agency_type", None),
        source_url=requirement.source_url,
    )


def _build_fee_item(record: RequirementRecord) -> FeeItem | None:
    if record.fee_amount_cents is None:
        return None

    kind, cadence, incremental, unit = _infer_fee_metadata(
        record.fee_schedule, record.renewal_frequency
    )

    notes = record.fee_schedule if record.fee_schedule else None
    try:
        return FeeItem(
            name=record.label,
            amount_cents=record.fee_amount_cents,
            kind=kind,
            cadence=cadence,
            unit=unit,
            incremental=incremental,
            notes=notes,
            requirement_id=record.id,
        )
    except ValueError as exc:  # pragma: no cover - defensive, validated elsewhere
        logger.debug("Skipping fee item for %s due to %s", record.id, exc)
        return None


def load_bundle(session: Session, *, city: str, state: str) -> RequirementsBundle:
    """Load a requirements bundle for the given jurisdiction."""

    stmt: Select[CityJurisdiction] = select(CityJurisdiction).where(
        func.lower(CityJurisdiction.city) == city.strip().lower(),
        CityJurisdiction.state == state.strip().upper(),
    )
    jurisdiction_obj = session.execute(stmt).scalar_one_or_none()
    if jurisdiction_obj is None:
        raise LookupError(f"Jurisdiction '{city}, {state}' not found")

    req_stmt = (
        select(CityRequirement, CityAgency)
        .outerjoin(CityAgency, CityRequirement.agency_id == CityAgency.id)
        .where(CityRequirement.jurisdiction_id == jurisdiction_obj.id)
        .where(CityRequirement.is_active.is_(True))
        .order_by(CityRequirement.requirement_label.asc())
    )

    rows = session.execute(req_stmt).all()

    records: list[RequirementRecord] = []
    paperwork: set[str] = set()
    fee_items: list[FeeItem] = []

    for requirement, agency in rows:
        record = _build_requirement_record(requirement, agency)
        records.append(record)

        paperwork.update(doc for doc in record.required_documents if doc)
        fee_item = _build_fee_item(record)
        if fee_item:
            fee_items.append(fee_item)

    jurisdiction = Jurisdiction(
        id=str(jurisdiction_obj.id),
        city=jurisdiction_obj.city,
        state=jurisdiction_obj.state,
        county=jurisdiction_obj.county,
        country_code="US",
    )

    schedule = FeeSchedule(
        jurisdiction=f"{jurisdiction.city}, {jurisdiction.state}",
        paperwork=tuple(sorted(paperwork)),
        fees=tuple(fee_items),
    )

    return RequirementsBundle(
        jurisdiction=jurisdiction,
        requirements=tuple(records),
        fee_schedule=schedule,
    )


@dataclass(slots=True)
class RequirementCostBreakdown:
    """Per-requirement cost totals used in :class:`CostEstimate`."""

    requirement_id: str
    one_time_cents: int = 0
    recurring_annualized_cents: int = 0
    incremental_fee_count: int = 0

    @property
    def total_annualized_cents(self) -> int:
        return self.one_time_cents + self.recurring_annualized_cents

    def add_fee_item(self, fee: FeeItem) -> None:
        if fee.kind == "one_time":
            self.one_time_cents += fee.amount_cents
        elif fee.kind == "recurring" and not fee.incremental:
            self.recurring_annualized_cents += fee.annualized_amount_cents()
        else:
            self.incremental_fee_count += 1


@dataclass(slots=True)
class CostEstimate:
    """Aggregated fee totals for a requirements bundle."""

    jurisdiction: str
    generated_at: datetime
    total_one_time_cents: int
    total_recurring_annualized_cents: int
    incremental_fee_count: int
    requirement_count: int
    fee_item_count: int
    per_requirement: dict[str, RequirementCostBreakdown] = field(default_factory=dict)

    @property
    def total_annualized_cents(self) -> int:
        return self.total_one_time_cents + self.total_recurring_annualized_cents

    def to_dict(self) -> dict[str, object]:
        return {
            "jurisdiction": self.jurisdiction,
            "generated_at": self.generated_at.isoformat(),
            "totals": {
                "one_time_cents": self.total_one_time_cents,
                "recurring_annualized_cents": self.total_recurring_annualized_cents,
                "incremental_fee_count": self.incremental_fee_count,
                "total_annualized_cents": self.total_annualized_cents,
            },
            "requirement_count": self.requirement_count,
            "fee_item_count": self.fee_item_count,
            "per_requirement": {
                req_id: {
                    "one_time_cents": breakdown.one_time_cents,
                    "recurring_annualized_cents": breakdown.recurring_annualized_cents,
                    "incremental_fee_count": breakdown.incremental_fee_count,
                    "total_annualized_cents": breakdown.total_annualized_cents,
                }
                for req_id, breakdown in self.per_requirement.items()
            },
        }


def estimate_costs(bundle: RequirementsBundle) -> CostEstimate:
    """Estimate total costs for a requirements bundle."""

    per_requirement: dict[str, RequirementCostBreakdown] = {}
    for record in bundle.requirements:
        per_requirement[record.id] = RequirementCostBreakdown(requirement_id=record.id)

    for fee in bundle.fee_schedule.fees:
        target_id = fee.requirement_id or "__unassigned__"
        breakdown = per_requirement.setdefault(target_id, RequirementCostBreakdown(requirement_id=target_id))
        breakdown.add_fee_item(fee)

    total_one_time = bundle.fee_schedule.total_one_time_cents
    total_recurring = bundle.fee_schedule.total_recurring_annualized_cents
    incremental_count = bundle.fee_schedule.incremental_fee_count

    return CostEstimate(
        jurisdiction=bundle.fee_schedule.jurisdiction,
        generated_at=datetime.utcnow(),
        total_one_time_cents=total_one_time,
        total_recurring_annualized_cents=total_recurring,
        incremental_fee_count=incremental_count,
        requirement_count=len(bundle.requirements),
        fee_item_count=len(bundle.fee_schedule.fees),
        per_requirement=per_requirement,
    )


__all__ = [
    "CostEstimate",
    "RequirementCostBreakdown",
    "estimate_costs",
    "load_bundle",
]

