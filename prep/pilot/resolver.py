"""Helpers for determining whether a user belongs to the pilot program."""

from __future__ import annotations

import re
from dataclasses import dataclass

from prep.settings import Settings


@dataclass(slots=True)
class PilotResolution:
    """Result of attempting to match a registration payload to a pilot cohort."""

    matched_zip: str | None = None
    matched_county: str | None = None

    @property
    def is_pilot(self) -> bool:
        """Return ``True`` when either the ZIP or county matched a pilot location."""

        return bool(self.matched_zip or self.matched_county)


def resolve_pilot_membership(
    zip_code: str | None,
    county: str | None,
    settings: Settings,
) -> PilotResolution:
    """Determine whether the supplied location belongs to the pilot program."""

    normalized_zip = _normalize_zip(zip_code) if zip_code else None
    normalized_county = _normalize_county(county) if county else None

    pilot_zip_map = {_normalize_zip(candidate): candidate for candidate in settings.pilot_zip_codes}
    pilot_county_map = {
        _normalize_county(candidate): candidate for candidate in settings.pilot_counties
    }

    matched_zip = pilot_zip_map.get(normalized_zip) if normalized_zip else None
    matched_county = pilot_county_map.get(normalized_county) if normalized_county else None

    return PilotResolution(matched_zip=matched_zip, matched_county=matched_county)


def _normalize_zip(value: str) -> str:
    digits = re.sub(r"[^0-9]", "", value)
    if len(digits) >= 5:
        return digits[:5]
    return value.strip().upper()


def _normalize_county(value: str) -> str:
    cleaned = " ".join(value.split())
    return cleaned.lower()


__all__ = ["PilotResolution", "resolve_pilot_membership"]
