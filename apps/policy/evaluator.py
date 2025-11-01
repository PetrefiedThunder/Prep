"""Lightweight municipal booking evaluator used in golden tests."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "regengine" / "cities"

_FEE_REASON_ALIASES = {
    "tot": "fees.tot.assessed",
    "lodging": "fees.lodging.assessed",
    "kingcountylodging": "fees.lodging.assessed",
    "king county lodging": "fees.lodging.assessed",
    "b&o": "fees.bo.assessed",
    "bo": "fees.bo.assessed",
}


def _load_yaml(path: Path) -> Dict[str, Any]:
    if path.exists():
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError:
            yaml = None  # type: ignore[assignment]
        if 'yaml' in locals() and yaml is not None:
            with path.open("r", encoding="utf-8") as handle:
                return yaml.safe_load(handle) or {}
    json_fallback = path.with_suffix(".json")
    if json_fallback.exists():
        with json_fallback.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    return {}


def _load_json(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return data
    return []


def _parse_time(value: str) -> dt.time:
    hour, minute = [int(part) for part in value.split(":", 1)]
    return dt.time(hour=hour, minute=minute)


def _parse_datetime(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value)


def _normalize_permits(permits: Iterable[Any]) -> Sequence[str]:
    normalized: List[str] = []
    for permit in permits:
        if isinstance(permit, str):
            normalized.append(permit.lower())
        elif isinstance(permit, dict):
            kind = permit.get("kind")
            if kind:
                normalized.append(str(kind).lower())
    return normalized


def _intervals_overlap(start_a: dt.datetime, end_a: dt.datetime, start_b: dt.datetime, end_b: dt.datetime) -> bool:
    return start_a < end_b and start_b < end_a


def _quiet_hours_overlap(start: dt.datetime, end: dt.datetime, quiet_start: dt.time, quiet_end: dt.time) -> bool:
    def in_quiet(candidate: dt.datetime) -> bool:
        local_time = candidate.timetz()
        if quiet_start <= quiet_end:
            return quiet_start <= local_time.replace(tzinfo=None) < quiet_end
        return local_time.replace(tzinfo=None) >= quiet_start or local_time.replace(tzinfo=None) < quiet_end

    cursor = start
    step = dt.timedelta(minutes=30)
    while cursor < end:
        if in_quiet(cursor):
            return True
        cursor += step
    # Also test the end instant (minus a microsecond) to catch short bookings
    return in_quiet(end - dt.timedelta(microseconds=1))


def _fee_reasons(fees: Sequence[Dict[str, Any]]) -> List[str]:
    reasons: List[str] = []
    for fee in fees:
        code = str(fee.get("code", "")).lower()
        name = str(fee.get("name", "")).lower()
        alias_key = code or name
        reason = _FEE_REASON_ALIASES.get(alias_key)
        if not reason and alias_key:
            # try stripping punctuation/spaces
            alias_key = alias_key.replace(" ", "").replace("&", "&")
            reason = _FEE_REASON_ALIASES.get(alias_key)
        if reason and reason not in reasons:
            reasons.append(reason)
    return reasons


def evaluate_booking(
    *,
    city: str,
    maker: Dict[str, Any],
    kitchen: Dict[str, Any],
    booking: Dict[str, Any],
    now: Optional[dt.datetime] = None,
) -> Tuple[str, List[str]]:
    """Evaluate a booking request against fixture-backed city rules."""

    config_dir = _FIXTURE_ROOT / city / "fixtures"
    config = _load_yaml(config_dir / "config.yaml")
    fee_schedule = _load_yaml(config_dir / "fee_schedule.yaml")
    zoning_codes = _load_json(config_dir / "zoning_codes.json")
    zoning_lookup = {entry.get("code"): entry for entry in zoning_codes}

    booking_start = _parse_datetime(booking["start"])
    booking_end = _parse_datetime(booking["end"])

    denies: List[str] = []
    conditions: List[str] = []

    required_permits = [str(p).lower() for p in config.get("permit_kinds", [])]
    kitchen_permits = set(_normalize_permits(kitchen.get("permits", [])))
    for permit_kind in required_permits:
        if permit_kind not in kitchen_permits:
            denies.append(f"permit.{permit_kind}.missing")

    zoning_config = config.get("zoning", {})
    kitchen_zoning = kitchen.get("zoning", {})
    if zoning_config.get("require_neighborhood_notice"):
        zone_entry = zoning_lookup.get(kitchen_zoning.get("code"))
        requires_notice = zone_entry.get("neighborhood_notice") if zone_entry else True
        if requires_notice and not kitchen_zoning.get("notice_doc"):
            conditions.append("zoning.notice.required")

    if config.get("community_notification_required") and not kitchen.get("community_notice_doc"):
        denies.append("community.notice.required")

    insurance_cfg = config.get("insurance", {})
    maker_insurance = maker.get("coi") or maker.get("insurance") or {}
    general_required = int(insurance_cfg.get("liability_min", 0))
    aggregate_required = int(insurance_cfg.get("aggregate_min", 0))
    additional_insured = insurance_cfg.get("additional_insured_legal")

    general_limit = int(maker_insurance.get("general", 0))
    aggregate_limit = int(maker_insurance.get("aggregate", 0))
    insured_phrase = maker_insurance.get("ai")

    if general_limit < general_required:
        denies.append("insurance.liability.min")
    if aggregate_limit < aggregate_required:
        denies.append("insurance.aggregate.min")
    if additional_insured and insured_phrase != additional_insured:
        denies.append("insurance.additional_insured.mismatch")

    quiet_cfg = config.get("sound_ordinance", {}).get("quiet_hours")
    if quiet_cfg:
        quiet_start = _parse_time(quiet_cfg["start"])
        quiet_end = _parse_time(quiet_cfg["end"])
        if _quiet_hours_overlap(booking_start, booking_end, quiet_start, quiet_end):
            denies.append("sound.quiet_hours")

    rental_cfg = config.get("rental_limits", {})
    max_hours = rental_cfg.get("max_hours_per_day_per_facility")
    if max_hours:
        hours_today = float(kitchen.get("hours_booked_today", 0))
        booking_hours = (booking_end - booking_start).total_seconds() / 3600
        if hours_today + booking_hours > float(max_hours):
            conditions.append("rental.limit.daily_cap_near")

    inspection = kitchen.get("inspection")
    if inspection and inspection.get("start") and inspection.get("end"):
        inspection_start = _parse_datetime(inspection["start"])
        inspection_end = _parse_datetime(inspection["end"])
        if _intervals_overlap(booking_start, booking_end, inspection_start, inspection_end):
            denies.append("calendar.inspection.conflict")

    if kitchen.get("inspection_result") == "fail":
        denies.append("inspection.failed.unlisted")

    maintenance = kitchen.get("maintenance")
    if maintenance and maintenance.get("start") and maintenance.get("end"):
        maintenance_start = _parse_datetime(maintenance["start"])
        maintenance_end = _parse_datetime(maintenance["end"])
        if _intervals_overlap(booking_start, booking_end, maintenance_start, maintenance_end):
            denies.append("calendar.maintenance.conflict")
        else:
            buffer = maintenance_start - booking_end
            if dt.timedelta(0) <= buffer < dt.timedelta(minutes=30):
                conditions.append("calendar.maintenance.buffer_required")

    if maker.get("requires_ada") and not kitchen.get("ada_accessible", False):
        conditions.append("ada.accessibility.required")

    if kitchen.get("grease_overdue"):
        conditions.append("grease.service.overdue")

    product_type = booking.get("product_type")
    if product_type == "outdoor_cooking" and booking_start.month in {11, 12, 1, 2}:
        conditions.append("seasonal.restriction.notice")

    if booking.get("fees_required"):
        fee_reasons = _fee_reasons(fee_schedule.get("fees", []))
        for reason in fee_reasons:
            conditions.append(reason)

    verdict = "ALLOW"
    if denies:
        verdict = "DENY"
        reasons = denies + conditions
    elif conditions:
        verdict = "ALLOW_WITH_CONDITIONS"
        reasons = conditions
    else:
        reasons = []

    return verdict, reasons


__all__ = ["evaluate_booking"]
