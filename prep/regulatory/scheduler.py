"""Recurring scraping scheduler for regulatory updates."""

from __future__ import annotations

import asyncio
import logging
from typing import List

import aioschedule as schedule

from jobs import run_expiry_check_async
from prep.regulatory.scraper import RegulatoryScraper


class RegulatoryScheduler:
    """Manage recurring scraping tasks."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.is_running = False

    async def start_scheduler(self) -> None:
        """Start the regulatory scraping scheduler."""

        self.is_running = True
        schedule.every().day.at("02:00").do(self.scrape_priority_states)
        schedule.every().sunday.at("03:00").do(self.scrape_all_states)
        schedule.every().month.do(self.deep_scrape)
        schedule.every().day.at("05:00").do(self.run_coi_expiry_checks)

        self.logger.info("Regulatory scheduler started")

        while self.is_running:
            await schedule.run_pending()
            await asyncio.sleep(60)

    async def scrape_priority_states(self) -> None:
        """Scrape high-priority states daily."""

        priority_states = ["CA", "NY", "TX", "FL", "IL"]
        self.logger.info("Scraping priority states: %s", priority_states)

        async with RegulatoryScraper() as scraper:
            for state in priority_states:
                try:
                    regulations = await scraper.scrape_health_department(state)
                    await self.save_regulations(state, regulations)
                except Exception as exc:  # pragma: no cover - network errors aren't deterministic
                    self.logger.error("Error scraping %s: %s", state, exc)

    async def scrape_all_states(self) -> None:
        """Scrape all states weekly."""

        all_states: List[str] = [
            "AL",
            "AK",
            "AZ",
            "AR",
            "CA",
            "CO",
            "CT",
            "DE",
            "FL",
            "GA",
            "HI",
            "ID",
            "IL",
            "IN",
            "IA",
            "KS",
            "KY",
            "LA",
            "ME",
            "MD",
            "MA",
            "MI",
            "MN",
            "MS",
            "MO",
            "MT",
            "NE",
            "NV",
            "NH",
            "NJ",
            "NM",
            "NY",
            "NC",
            "ND",
            "OH",
            "OK",
            "OR",
            "PA",
            "RI",
            "SC",
            "SD",
            "TN",
            "TX",
            "UT",
            "VT",
            "VA",
            "WA",
            "WV",
            "WI",
            "WY",
        ]

        self.logger.info("Scraping all states weekly")

        async with RegulatoryScraper() as scraper:
            for state in all_states:
                try:
                    regulations = await scraper.scrape_health_department(state)
                    await scraper.scrape_insurance_requirements(state)
                    await self.save_regulations(state, regulations)
                    await asyncio.sleep(1)
                except Exception as exc:  # pragma: no cover - network errors aren't deterministic
                    self.logger.error("Error scraping %s: %s", state, exc)

    async def deep_scrape(self) -> None:
        """Monthly deep scrape with comprehensive data collection."""

        self.logger.info("Starting monthly deep scrape")
        # Placeholder for extended scraping logic.

    async def run_coi_expiry_checks(self) -> None:
        """Trigger the COI expiry job and log the resulting summary."""

        summary = await run_expiry_check_async()
        self.logger.info(
            "COI expiry job completed",
            extra={
                "total_documents": summary.total_documents,
                "sms_sent": summary.sms_sent,
                "emails_sent": summary.emails_sent,
                "skipped": summary.skipped,
            },
        )

    async def save_regulations(self, state: str, regulations: List[dict]) -> None:
        """Persist scraped regulations to storage (placeholder)."""

        self.logger.info("Saved %s regulations for %s", len(regulations), state)


__all__ = ["RegulatoryScheduler"]
