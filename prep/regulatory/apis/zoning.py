"""Municipal zoning integrations for regulatory intelligence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .health_departments import BaseAPIClient, RegulatoryAPIError


class ZoningAPIError(RegulatoryAPIError):
    """Raised when zoning API requests fail."""


@dataclass(slots=True)
class ZoningResult:
    """Structured zoning response."""

    address: str
    zoning_district: str | None
    land_use: str | None
    jurisdiction: str
    notes: str | None
    raw: dict[str, Any]


class SFPlanningAPI(BaseAPIClient):
    """San Francisco planning API client."""

    BASE_URL = "https://data.sfgov.org/resource/pz4h-wbhj.json"

    async def get_zoning(self, address: str) -> ZoningResult:
        params = {
            "$limit": 1,
            "$order": "last_updated DESC",
            "address": address.upper(),
        }
        data = await self._fetch_json(self.BASE_URL, params=params)
        if not data:
            raise ZoningAPIError(f"No zoning data found for {address} in San Francisco")
        return self._transform(address, data[0], jurisdiction="San Francisco, CA")

    def _transform(self, address: str, payload: dict[str, Any], jurisdiction: str) -> ZoningResult:
        return ZoningResult(
            address=address,
            zoning_district=payload.get("zoning_district"),
            land_use=payload.get("land_use"),
            jurisdiction=jurisdiction,
            notes=payload.get("notes") or payload.get("remarks"),
            raw=payload,
        )


class NYCPlanningAPI(BaseAPIClient):
    """New York City planning open data integration."""

    BASE_URL = "https://data.cityofnewyork.us/resource/9wwi-sb8x.json"

    async def get_zoning(self, address: str) -> ZoningResult:
        params = {
            "$limit": 1,
            "$order": "effective_date DESC",
            "address": address.upper(),
        }
        data = await self._fetch_json(self.BASE_URL, params=params)
        if not data:
            raise ZoningAPIError(f"No zoning data found for {address} in New York City")
        return self._transform(address, data[0], jurisdiction="New York, NY")

    def _transform(self, address: str, payload: dict[str, Any], jurisdiction: str) -> ZoningResult:
        return ZoningResult(
            address=address,
            zoning_district=payload.get("zoning_district"),
            land_use=payload.get("land_use"),
            jurisdiction=jurisdiction,
            notes=payload.get("description") or payload.get("comments"),
            raw=payload,
        )


class ChicagoZoningAPI(BaseAPIClient):
    """Chicago zoning open data integration."""

    BASE_URL = "https://data.cityofchicago.org/resource/7cve-jgbp.json"

    async def get_zoning(self, address: str) -> ZoningResult:
        params = {
            "$limit": 1,
            "$order": "map_date DESC",
            "street_address": address.upper(),
        }
        data = await self._fetch_json(self.BASE_URL, params=params)
        if not data:
            raise ZoningAPIError(f"No zoning data found for {address} in Chicago")
        return self._transform(address, data[0], jurisdiction="Chicago, IL")

    def _transform(self, address: str, payload: dict[str, Any], jurisdiction: str) -> ZoningResult:
        return ZoningResult(
            address=address,
            zoning_district=payload.get("zoning_classification"),
            land_use=payload.get("land_use"),
            jurisdiction=jurisdiction,
            notes=payload.get("notes") or payload.get("zoning_notes"),
            raw=payload,
        )


class MunicipalZoningAPI:
    """Aggregates municipal zoning providers with simple routing by address."""

    def __init__(self) -> None:
        self.apis: dict[str, BaseAPIClient] = {
            "san_francisco": SFPlanningAPI(),
            "new_york": NYCPlanningAPI(),
            "chicago": ChicagoZoningAPI(),
        }

    async def get_zoning_info(self, address: str) -> ZoningResult:
        city_key = self.extract_city_from_address(address)
        if not city_key or city_key not in self.apis:
            raise ZoningAPIError(f"Unsupported zoning jurisdiction for address '{address}'")
        client = self.apis[city_key]
        return await client.get_zoning(address)

    @staticmethod
    def extract_city_from_address(address: str) -> str | None:
        normalized = address.lower()
        if "san francisco" in normalized:
            return "san_francisco"
        if re.search(r",\s*ny\b|new york", normalized):
            return "new_york"
        if "chicago" in normalized:
            return "chicago"
        return None


__all__ = [
    "ZoningAPIError",
    "ZoningResult",
    "SFPlanningAPI",
    "NYCPlanningAPI",
    "ChicagoZoningAPI",
    "MunicipalZoningAPI",
]
