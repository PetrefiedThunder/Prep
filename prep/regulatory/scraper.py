"""Async web scraper utilities for collecting regulatory data."""

from __future__ import annotations

from datetime import datetime
import hashlib
import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import aiohttp
from aiobotocore.session import get_session
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class RegulatoryScraper:
    """High level scraping routines for regulatory data sources."""

    def __init__(
        self,
        *,
        s3_bucket: str = "kitchenshare-etl-raw",
        s3_client_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logger
        self._s3_bucket = s3_bucket
        self._s3_client_kwargs = s3_client_kwargs or {}
        self._aws_session = get_session()

    async def __aenter__(self) -> "RegulatoryScraper":
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[override]
        if self.session:
            await self.session.close()
            self.session = None

    async def scrape_health_department(self, state: str, city: Optional[str] = None) -> List[Dict]:
        """Scrape health department regulations for a state/city."""

        base_urls = {
            "CA": "https://www.cdph.ca.gov/Programs/CEH/DFDCS/Pages/FDBPrograms/FoodSafetyProgram.aspx",
            "NY": "https://www.health.ny.gov/environmental/food/",
            "TX": "https://www.dshs.texas.gov/food-establishments",
            "FL": "https://www.floridahealth.gov/environmental-health/food-safety/",
            "IL": "https://dph.illinois.gov/topics-services/food-safety.html",
        }

        regulations: List[Dict] = []
        if not self.session:
            raise RuntimeError("RegulatoryScraper session is not initialized. Use as async context manager.")

        if state in base_urls:
            try:
                source_url = base_urls[state]
                async with self.session.get(source_url) as response:
                    if response.status == 200:
                        raw_bytes = await response.read()
                        await self._persist_raw_bytes(raw_bytes, source_url)
                        content = self._decode_response(raw_bytes, response)
                        regulations = await self.parse_health_regulations(
                            content, state, city, source_url
                        )
                    else:
                        self.logger.warning(
                            "Health department request for %s returned status %s", state, response.status
                        )
            except Exception as exc:  # pragma: no cover - network errors aren't deterministic
                self.logger.error("Error scraping %s health department: %s", state, exc)

        return regulations

    async def _persist_raw_bytes(self, payload: bytes, source_url: str) -> None:
        """Persist the fetched payload to S3 for archival."""

        if not payload:
            return

        key = self._build_s3_key(source_url)
        try:
            async with self._aws_session.create_client("s3", **self._s3_client_kwargs) as client:
                await client.put_object(Bucket=self._s3_bucket, Key=key, Body=payload)
        except Exception:  # pragma: no cover - depends on environment configuration
            self.logger.exception("Failed to upload raw payload for %s", source_url)

    def _build_s3_key(self, source_url: str) -> str:
        """Construct an S3 object key for a given source URL."""

        today = datetime.utcnow().strftime("%Y-%m-%d")
        filename = self._slugify_filename(source_url)
        digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:16]
        return f"{today}/{digest}-{filename}"

    def _slugify_filename(self, source_url: str) -> str:
        parsed = urlparse(source_url)
        candidate = parsed.path.rsplit("/", 1)[-1] or parsed.netloc or "document"
        stem, ext = os.path.splitext(candidate)
        if not stem:
            stem = parsed.netloc or "document"
        slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-") or "document"
        extension = ext.lower() if ext else ".html"
        return f"{slug}{extension}"

    def _decode_response(self, payload: bytes, response: aiohttp.ClientResponse) -> str:
        encoding = response.charset or "utf-8"
        try:
            return payload.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            return payload.decode("utf-8", errors="replace")

    async def parse_health_regulations(
        self, html: str, state: str, city: Optional[str], source_url: str
    ) -> List[Dict]:
        """Parse health regulations from HTML content."""

        soup = BeautifulSoup(html, "html.parser")
        regulations: List[Dict] = []

        patterns = [
            r"permits? required",
            r"food handler.*certificat",
            r"inspection.*required",
            r"health.*code",
            r"safety.*standard",
        ]

        text_content = soup.get_text("\n").lower()
        lines = [line.strip() for line in text_content.split("\n") if line.strip()]

        for line in lines:
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    regulations.append(
                        {
                            "regulation_type": "health_permit",
                            "title": f"Health Regulation - {state}",
                            "description": line,
                            "requirements": {"notes": line},
                            "applicable_to": ["host"],
                            "jurisdiction": city or state,
                            "effective_date": datetime.utcnow(),
                            "citation": f"Health Dept - {state}",
                            "source_url": source_url,
                            "source_type": "health_dept",
                        }
                    )
                    break

        return regulations

    async def scrape_insurance_requirements(
        self, state: str, business_type: str = "commercial_kitchen"
    ) -> Dict:
        """Scrape insurance requirements for commercial kitchen rentals."""

        # Mock insurance data - in production, this would scrape from insurance providers
        insurance_standards = {
            "CA": {
                "minimum_coverage": {
                    "general_liability": 1_000_000,
                    "property_damage": 1_000_000,
                    "workers_comp": 500_000,
                },
                "required_policies": ["general_liability", "property_damage", "workers_comp"],
                "notes": "Additional coverage recommended for equipment and business interruption",
                "source_type": "insurance",
            },
            "NY": {
                "minimum_coverage": {
                    "general_liability": 2_000_000,
                    "property_damage": 1_000_000,
                },
                "required_policies": ["general_liability", "property_damage"],
                "notes": "NYC requires additional permits for shared kitchens",
                "source_type": "insurance",
            },
            "TX": {
                "minimum_coverage": {
                    "general_liability": 500_000,
                    "property_damage": 500_000,
                },
                "required_policies": ["general_liability"],
                "notes": "Texas has relatively lenient insurance requirements",
                "source_type": "insurance",
            },
            "FL": {
                "minimum_coverage": {
                    "general_liability": 1_000_000,
                    "workers_comp": 1_000_000,
                },
                "required_policies": ["general_liability", "workers_comp"],
                "notes": "Hurricane coverage recommended in coastal areas",
                "source_type": "insurance",
            },
        }

        defaults = {
            "minimum_coverage": {"general_liability": 1_000_000},
            "required_policies": ["general_liability"],
            "notes": "Standard commercial liability insurance required",
            "source_type": "insurance",
        }

        requirements = insurance_standards.get(state, defaults).copy()
        requirements.setdefault("business_type", business_type)
        requirements.setdefault("special_requirements", None)
        requirements.setdefault("source_url", f"https://insurance.{state.lower()}.gov")
        return requirements

    async def scrape_zoning_regulations(self, city: Optional[str], state: str) -> List[Dict]:
        """Scrape zoning regulations for commercial kitchen operations."""

        zoning_data: List[Dict] = []

        zoning_issues = [
            "Commercial kitchen operations in residential zones",
            "Parking requirements for food businesses",
            "Hours of operation restrictions",
            "Noise and odor regulations",
            "Waste disposal requirements",
        ]

        city_label = city or state
        source_url = None
        if city:
            source_url = f"https://{city.lower().replace(' ', '')}.{state.lower()}.gov/zoning"

        for issue in zoning_issues:
            zoning_data.append(
                {
                    "regulation_type": "zoning",
                    "title": f"Zoning Regulation - {city_label}",
                    "description": issue,
                    "requirements": {"notes": f"Check local zoning laws for {issue.lower()}"},
                    "applicable_to": ["host"],
                    "jurisdiction": city_label,
                    "citation": f"Zoning Code - {city_label}",
                    "source_url": source_url,
                    "source_type": "zoning",
                }
            )

        return zoning_data


__all__ = ["RegulatoryScraper"]
