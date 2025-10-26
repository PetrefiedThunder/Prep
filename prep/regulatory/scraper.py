"""Async web scraper utilities for collecting regulatory data."""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
import re
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

from typing_extensions import ParamSpec

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


_P = ParamSpec("_P")
_R = TypeVar("_R")


class ServerSideError(RuntimeError):
    """Raised when an upstream server responds with a 5xx status code."""

    def __init__(self, url: str, status: int, *, body: str | None = None) -> None:
        super().__init__(f"Server error {status} for {url}")
        self.url = url
        self.status = status
        self.body = body


def _extract_status(exc: BaseException) -> Optional[int]:
    """Return an HTTP status code from a raised exception if available."""

    for attribute in ("status", "status_code"):
        value = getattr(exc, attribute, None)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)

    response = getattr(exc, "response", None)
    if response is not None:
        for attribute in ("status", "status_code"):
            value = getattr(response, attribute, None)
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)

    return None


def with_backoff(*, retries: int, base_delay: float) -> Callable[[Callable[_P, Awaitable[_R]]], Callable[_P, Awaitable[_R]]]:
    """Retry an async callable on retryable HTTP errors with exponential backoff."""

    def decorator(func: Callable[_P, Awaitable[_R]]) -> Callable[_P, Awaitable[_R]]:
        if not asyncio.iscoroutinefunction(func):
            raise TypeError("with_backoff can only be applied to async callables")

        @wraps(func)
        async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            attempt = 0
            delay = base_delay
            while True:
                try:
                    return await func(*args, **kwargs)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # pragma: no cover - defensive fallback
                    status = _extract_status(exc)
                    if status is not None and 500 <= status < 600 and attempt < retries:
                        attempt += 1
                        logger.warning(
                            "Retrying after %s error for %s (attempt %s/%s) in %.1fs",
                            status,
                            getattr(exc, "url", None) or getattr(exc, "request", exc),
                            attempt,
                            retries,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                    raise

        return wrapper

    return decorator


class RegulatoryScraper:
    """High level scraping routines for regulatory data sources."""

    def __init__(self) -> None:
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logger

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
                content = await self._fetch_health_department_page(base_urls[state])
            except ServerSideError as exc:
                self.logger.error(
                    "Health department request for %s failed with status %s after retries", state, exc.status
                )
            except aiohttp.ClientResponseError as exc:
                self.logger.warning(
                    "Health department request for %s returned status %s", state, exc.status
                )
            except aiohttp.ClientError as exc:  # pragma: no cover - network errors aren't deterministic
                self.logger.error("Error scraping %s health department: %s", state, exc)
            else:
                regulations = await self.parse_health_regulations(
                    content, state, city, base_urls[state]
                )

        return regulations

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


    @with_backoff(retries=5, base_delay=1.5)
    async def _fetch_health_department_page(self, url: str, *, params: Optional[Dict[str, Any]] = None) -> str:
        """Retrieve a health department page, retrying on transient server failures."""

        if not self.session:
            raise RuntimeError("RegulatoryScraper session is not initialized. Use as async context manager.")

        async with self.session.get(url, params=params) as response:
            body = await response.text()
            if 500 <= response.status < 600:
                raise ServerSideError(url, response.status, body=body[:500])
            if response.status >= 400:
                raise aiohttp.ClientResponseError(
                    response.request_info,
                    response.history,
                    status=response.status,
                    message=body[:500],
                    headers=response.headers,
                )
            return body


__all__ = ["RegulatoryScraper"]
