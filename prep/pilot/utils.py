"""Helpers for determining pilot program eligibility."""

from __future__ import annotations

from collections.abc import Iterable

from prep.settings import get_settings


def _normalize_zip(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped.replace(" ", "").upper()


def _normalize_state(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped.upper()


def _normalize_county(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    normalized = stripped.upper()
    if normalized.endswith(" COUNTY"):
        normalized = normalized[: -len(" COUNTY")].strip()
    return normalized or None


def _build_county_keys(values: Iterable[str]) -> set[tuple[str, str | None]]:
    keys: set[tuple[str, str | None]] = set()
    for raw in values:
        if raw is None:
            continue
        text = str(raw).strip()
        if not text:
            continue
        parts = [part.strip() for part in text.split(",") if part.strip()]
        county_part = parts[0] if parts else text
        state_part = parts[1] if len(parts) > 1 else None
        county_key = _normalize_county(county_part)
        if not county_key:
            continue
        keys.add((county_key, _normalize_state(state_part)))
    return keys


def is_pilot_location(
    *,
    state: str | None,
    city: str | None = None,
    county: str | None = None,
    zip_code: str | None = None,
) -> bool:
    """Return ``True`` if the provided location participates in the pilot program."""

    settings = get_settings()

    normalized_zip = _normalize_zip(zip_code)
    if normalized_zip:
        pilot_zips = {
            code for code in (_normalize_zip(item) for item in settings.pilot_zip_codes) if code
        }
        if normalized_zip in pilot_zips:
            return True

    pilot_counties = _build_county_keys(settings.pilot_counties)
    normalized_county = _normalize_county(county)
    normalized_state = _normalize_state(state)

    if normalized_county:
        if (normalized_county, normalized_state) in pilot_counties:
            return True
        if (normalized_county, None) in pilot_counties:
            return True

    if city:
        normalized_city = _normalize_county(city)
        if normalized_city and (
            (normalized_city, normalized_state) in pilot_counties
            or (normalized_city, None) in pilot_counties
        ):
            return True

    return False


__all__ = ["is_pilot_location"]
