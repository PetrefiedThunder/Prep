"""Async API clients for state and municipal health department integrations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any, Dict, Iterable, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class RegulatoryAPIError(RuntimeError):
    """Raised when a regulatory API request fails."""


@dataclass(slots=True)
class InspectionRecord:
    """Structured inspection data returned by health department APIs."""

    permit_number: str
    inspection_date: datetime
    result: str
    violation_points: Optional[int]
    jurisdiction: str
    raw: Dict[str, Any]


class BaseAPIClient:
    """Base helper for HTTP interactions with regulatory APIs."""

    def __init__(self, *, timeout: int = 30) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def _fetch_json(
        self, url: str, *, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None
    ) -> Any:
        """Perform a GET request and return parsed JSON, raising errors for non-200 responses."""

        async with aiohttp.ClientSession(timeout=self._timeout, headers=headers) as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    body = await response.text()
                    raise RegulatoryAPIError(
                        f"Request to {url} failed with status {response.status}: {body[:500]}"
                    )

                if response.content_type == "application/json":
                    return await response.json()

                raise RegulatoryAPIError(
                    f"Expected JSON response from {url} but received content-type {response.content_type}."
                )

    async def _post_json(
        self,
        url: str,
        *,
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """Perform a POST request returning parsed JSON."""

        async with aiohttp.ClientSession(timeout=self._timeout, headers=headers) as session:
            async with session.post(url, json=payload) as response:
                if response.status not in {200, 201}:
                    body = await response.text()
                    raise RegulatoryAPIError(
                        f"POST to {url} failed with status {response.status}: {body[:500]}"
                    )

                if response.content_type == "application/json":
                    return await response.json()

                raise RegulatoryAPIError(
                    f"Expected JSON response from {url} but received content-type {response.content_type}."
                )


class CaliforniaHealthDepartmentAPI(BaseAPIClient):
    """Integration with the California Department of Public Health open data services."""

    BASE_URL = "https://data.ca.gov/api/3/action"
    LICENSE_RESOURCE_ID = "7e6c-dm7j"
    INSPECTION_RESOURCE_ID = "bbg6-2f3t"

    async def get_business_licenses(self, business_type: str = "food establishment", limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch licensed food establishments from the California open data portal."""

        params = {
            "resource_id": self.LICENSE_RESOURCE_ID,
            "limit": limit,
            "q": business_type,
        }
        data = await self._fetch_json(f"{self.BASE_URL}/datastore_search", params=params)
        records = data.get("result", {}).get("records", [])
        return [self._transform_license(record) for record in records]

    async def get_inspection_records(self, permit_number: str, limit: int = 25) -> List[InspectionRecord]:
        """Return inspection history for a specific California permit number."""

        params = {
            "resource_id": self.INSPECTION_RESOURCE_ID,
            "limit": limit,
            "filters": f"{{\"permit_number\": \"{permit_number}\"}}",
        }
        data = await self._fetch_json(f"{self.BASE_URL}/datastore_search", params=params)
        records = data.get("result", {}).get("records", [])
        inspections: List[InspectionRecord] = []
        for record in records:
            transformed = self._transform_inspection(record)
            if transformed:
                inspections.append(transformed)
        return inspections

    def parse_license_data(self, data: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize raw license data into a consistent schema."""

        return [self._transform_license(record) for record in data]

    def _transform_license(self, record: Dict[str, Any]) -> Dict[str, Any]:
        jurisdiction = record.get("facility_city") or record.get("city") or "CA"
        return {
            "name": record.get("facility_name") or record.get("business_name"),
            "permit_number": record.get("permit_number"),
            "address": record.get("facility_address") or record.get("address"),
            "jurisdiction": jurisdiction,
            "status": record.get("permit_status") or record.get("status"),
            "record_updated": self._parse_datetime(record.get("last_updated")),
            "raw": record,
        }

    def _transform_inspection(self, record: Dict[str, Any]) -> Optional[InspectionRecord]:
        permit_number = record.get("permit_number") or record.get("permit")
        date_text = record.get("inspection_date") or record.get("activity_date")
        if not permit_number or not date_text:
            return None

        return InspectionRecord(
            permit_number=permit_number,
            inspection_date=self._parse_datetime(date_text) or datetime.utcnow(),
            result=record.get("inspection_result") or record.get("pe_description", "unknown"),
            violation_points=self._parse_int(record.get("points_deducted") or record.get("inspection_score")),
            jurisdiction=record.get("facility_city") or record.get("city") or "CA",
            raw=record,
        )

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        logger.debug("Unable to parse datetime value: %s", value)
        return None

    @staticmethod
    def _parse_int(value: Any) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


class NewYorkHealthDepartmentAPI(BaseAPIClient):
    """Integration with the New York State Department of Health open data services."""

    BASE_URL = "https://health.data.ny.gov"
    DATASET_ID = "43nn-pn8j"

    async def get_restaurant_inspections(self, county: Optional[str] = None, limit: int = 100) -> List[InspectionRecord]:
        """Fetch restaurant inspection data from the New York open data portal."""

        params: Dict[str, Any] = {"$limit": limit, "$order": "inspection_date DESC"}
        if county:
            params["county"] = county
        data = await self._fetch_json(f"{self.BASE_URL}/resource/{self.DATASET_ID}.json", params=params)
        inspections: List[InspectionRecord] = []
        for item in data:
            transformed = self._transform_record(item)
            if transformed:
                inspections.append(transformed)
        return inspections

    async def get_facility_details(self, camis: str) -> Dict[str, Any]:
        """Return detailed information for a single facility identified by CAMIS number."""

        params = {"camis": camis, "$limit": 1}
        data = await self._fetch_json(f"{self.BASE_URL}/resource/{self.DATASET_ID}.json", params=params)
        if not data:
            raise RegulatoryAPIError(f"No facility found for CAMIS {camis}")
        return data[0]

    def _transform_record(self, record: Dict[str, Any]) -> Optional[InspectionRecord]:
        camis = record.get("camis")
        inspection_date = record.get("inspection_date")
        if not camis or not inspection_date:
            return None

        return InspectionRecord(
            permit_number=str(camis),
            inspection_date=self._parse_datetime(inspection_date) or datetime.utcnow(),
            result=record.get("action", "unknown"),
            violation_points=self._parse_int(record.get("violation_points")),
            jurisdiction=record.get("county") or "NY",
            raw=record,
        )

    @staticmethod
    def _parse_datetime(value: str) -> Optional[datetime]:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        logger.debug("Unable to parse NY inspection date: %s", value)
        return None

    @staticmethod
    def _parse_int(value: Any) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


__all__ = [
    "RegulatoryAPIError",
    "InspectionRecord",
    "CaliforniaHealthDepartmentAPI",
    "NewYorkHealthDepartmentAPI",
]
