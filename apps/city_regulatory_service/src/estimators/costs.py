"""Cost estimation utilities for city regulatory requirements."""

from __future__ import annotations

import math
import re
from typing import Any, Iterator

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.city_regulatory_service.src.models import (
    CityAgency,
    CityJurisdiction,
    CityRequirement,
    FeeItem,
    FeeSchedule,
    RequirementsBundle,
)

_AMOUNT_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
_RECURRING_KEYWORDS = {
    "biennial": "biennial",
    "biannual": "semiannual",
    "semiannual": "semiannual",
    "semi annual": "semiannual",
    "semi-annual": "semiannual",
    "quarter": "quarterly",
    "quarterly": "quarterly",
    "month": "monthly",
    "monthly": "monthly",
    "week": "weekly",
    "weekly": "weekly",
    "day": "daily",
    "daily": "daily",
    "year": "annual",
    "annual": "annual",
    "annually": "annual",
    "per year": "annual",
    "per annum": "annual",
    "yearly": "yearly",
}
_INCREMENTAL_MARKERS = (
    "per application",
    "per inspection",
    "per reinspection",
    "per permit",
    "per employee",
    "per location",
    "per truck",
    "per seat",
    "per day",
    "per event",
)
_COMPONENT_KEYS = ("components", "items", "fees")


def _to_cents(value: Any) -> int | None:
    """Convert a fee amount to cents, handling strings with currency symbols."""

    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(round(float(value) * 100))
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "")
    match = _AMOUNT_PATTERN.search(text)
    if not match:
        return None
    amount = float(match.group(0))
    return int(round(amount * 100))


def _detect_incremental(schedule: str | None, *, explicit_flag: bool = False) -> bool:
    if explicit_flag:
        return True
    if not schedule:
        return False
    lowered = schedule.lower()
    return any(marker in lowered for marker in _INCREMENTAL_MARKERS)


def _infer_interval(schedule: str | None) -> tuple[str | None, bool]:
    """Return recurring interval (if any) and whether schedule implies one-time."""

    if not schedule:
        return None, True
    lowered = schedule.lower()
    for keyword, interval in _RECURRING_KEYWORDS.items():
        if keyword in lowered:
            return interval, False
    if "one-time" in lowered or "one time" in lowered or "single" in lowered:
        return None, True
    return None, True


def _iter_fee_components(details: Any) -> Iterator[dict[str, Any]]:
    if details is None:
        return
    if isinstance(details, dict):
        yielded = False
        for key in _COMPONENT_KEYS:
            value = details.get(key)
            if isinstance(value, list):
                for entry in value:
                    if isinstance(entry, dict):
                        yielded = True
                        yield entry
        if not yielded and any(k in details for k in ("amount", "amount_cents")):
            yield details
        return
    if isinstance(details, list):
        for entry in details:
            if isinstance(entry, dict):
                yield entry


def _build_fee_items(requirement: CityRequirement) -> list[FeeItem]:
    items: list[FeeItem] = []
    used_details = False

    for component in _iter_fee_components(requirement.fee_details):
        amount_cents = _to_cents(
            component.get("amount")
            or component.get("amount_cents")
            or component.get("value")
        )
        if amount_cents is None:
            continue
        schedule_hint = component.get("frequency") or component.get("schedule")
        interval, is_one_time = _infer_interval(schedule_hint)
        incremental = _detect_incremental(
            schedule_hint,
            explicit_flag=bool(component.get("incremental")),
        )
        label = component.get("label") or component.get("name") or requirement.requirement_label
        notes = component.get("notes") or schedule_hint

        if is_one_time:
            item = FeeItem(
                requirement_id=requirement.requirement_id,
                label=label,
                notes=notes,
                one_time_cents=amount_cents,
                incremental=incremental,
            )
        else:
            item = FeeItem(
                requirement_id=requirement.requirement_id,
                label=label,
                notes=notes,
                recurring_cents=amount_cents,
                recurring_interval=interval or "annual",
                incremental=incremental,
            )
        items.append(item)
        used_details = True

    if used_details:
        return items

    amount_cents = _to_cents(requirement.fee_amount)
    if amount_cents is None:
        return items

    interval, is_one_time = _infer_interval(requirement.fee_schedule)
    incremental = _detect_incremental(requirement.fee_schedule)
    notes = requirement.fee_schedule if requirement.fee_schedule not in (None, "", "unknown") else None

    if is_one_time:
        items.append(
            FeeItem(
                requirement_id=requirement.requirement_id,
                label=requirement.requirement_label,
                notes=notes,
                one_time_cents=amount_cents,
                incremental=incremental,
            )
        )
    else:
        items.append(
            FeeItem(
                requirement_id=requirement.requirement_id,
                label=requirement.requirement_label,
                notes=notes,
                recurring_cents=amount_cents,
                recurring_interval=interval or "annual",
                incremental=incremental,
            )
        )

    return items


def load_bundle(
    session: Session,
    *,
    jurisdiction: str,
    state: str | None = None,
) -> RequirementsBundle:
    """Load a :class:`RequirementsBundle` for the provided jurisdiction."""

    filters = [func.lower(CityJurisdiction.city) == jurisdiction.lower()]
    if state:
        filters.append(func.lower(CityJurisdiction.state) == state.lower())

    query = session.execute(select(CityJurisdiction).where(*filters))
    jurisdiction_row = query.scalars().first()

    if jurisdiction_row is None:
        raise LookupError(f"Jurisdiction '{jurisdiction}' not found")

    requirements_stmt = (
        select(CityRequirement, CityAgency)
        .join(CityAgency, CityRequirement.agency_id == CityAgency.id, isouter=True)
        .where(CityRequirement.jurisdiction_id == jurisdiction_row.id)
        .order_by(CityRequirement.requirement_label)
    )
    results = session.execute(requirements_stmt).all()

    bundle_requirements: list[RequirementsBundle.Requirement] = []
    for requirement, agency in results:
        items = _build_fee_items(requirement)
        schedule = FeeSchedule(
            jurisdiction_id=str(jurisdiction_row.id),
            jurisdiction_name=jurisdiction_row.city,
            state=jurisdiction_row.state,
            items=items,
        )
        bundle_requirements.append(
            RequirementsBundle.Requirement(
                requirement_id=requirement.requirement_id,
                label=requirement.requirement_label,
                agency=agency.name if agency else None,
                fee_schedule=schedule,
                metadata={
                    "requirement_type": requirement.requirement_type,
                    "source_url": requirement.source_url,
                },
            )
        )

    return RequirementsBundle(
        jurisdiction_id=str(jurisdiction_row.id),
        jurisdiction_name=jurisdiction_row.city,
        state=jurisdiction_row.state,
        requirements=bundle_requirements,
    )


def estimate_costs(bundle: RequirementsBundle) -> dict[str, Any]:
    """Return a structured cost summary for a :class:`RequirementsBundle`."""

    schedule = bundle.fee_schedule
    requirement_breakdown = []
    for requirement in bundle.requirements:
        req_schedule = requirement.fee_schedule
        requirement_breakdown.append(
            {
                "requirement_id": requirement.requirement_id,
                "label": requirement.label,
                "agency": requirement.agency,
                "one_time_cents": req_schedule.total_one_time_cents,
                "recurring_annualized_cents": req_schedule.total_recurring_annualized_cents,
                "has_incremental_fees": req_schedule.has_incremental,
                "items": [item.dict() for item in req_schedule.iter_items()],
                "metadata": requirement.metadata,
            }
        )

    summary = {
        "one_time_cents": schedule.total_one_time_cents,
        "recurring_annualized_cents": schedule.total_recurring_annualized_cents,
        "has_incremental_fees": schedule.has_incremental,
        "requirement_count": len(bundle.requirements),
    }
    if bundle.requirements:
        summary["average_one_time_cents"] = math.floor(
            schedule.total_one_time_cents / len(bundle.requirements)
        )
        summary["average_recurring_annualized_cents"] = math.floor(
            schedule.total_recurring_annualized_cents / len(bundle.requirements)
        )
    else:
        summary["average_one_time_cents"] = 0
        summary["average_recurring_annualized_cents"] = 0

    return {
        "jurisdiction": {
            "id": bundle.jurisdiction_id,
            "name": bundle.jurisdiction_name,
            "state": bundle.state,
        },
        "summary": summary,
        "requirements": requirement_breakdown,
    }


__all__ = ["load_bundle", "estimate_costs"]
