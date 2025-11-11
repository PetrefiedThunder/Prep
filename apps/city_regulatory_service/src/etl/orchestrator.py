"""
ETL orchestrator for city regulatory data ingestion.

Coordinates the extraction, transformation, and loading of city regulatory data
into the Prep regulatory engine.
"""

from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Any

from sqlalchemy.orm import Session

from apps.city_regulatory_service.src.adapters import (
    NewYorkCityAdapter,
    SanFranciscoAdapter,
)
from apps.city_regulatory_service.src.models import (
    CityAgency,
    CityETLRun,
    CityJurisdiction,
    CityRequirement,
)
from apps.city_regulatory_service.src.normalizers import RequirementNormalizer

logger = logging.getLogger(__name__)


# Registry of available city adapters
CITY_ADAPTERS = {
    "San Francisco": SanFranciscoAdapter,
    "New York": NewYorkCityAdapter,
}


class CityETLOrchestrator:
    """Orchestrates ETL pipeline for city regulatory data."""

    def __init__(self, db_session: Session):
        """
        Initialize the ETL orchestrator.

        Args:
            db_session: Database session for persistence
        """
        self.db_session = db_session

    def ensure_jurisdiction(self, city: str, state: str) -> CityJurisdiction:
        """
        Ensure jurisdiction record exists in database.

        Args:
            city: City name
            state: State code

        Returns:
            CityJurisdiction instance
        """
        jurisdiction = (
            self.db_session.query(CityJurisdiction)
            .filter_by(city=city, state=state)
            .first()
        )

        if not jurisdiction:
            logger.info(f"Creating jurisdiction record for {city}, {state}")
            jurisdiction = CityJurisdiction(
                city=city,
                state=state,
            )
            self.db_session.add(jurisdiction)
            self.db_session.flush()

        return jurisdiction

    def ensure_agency(
        self,
        jurisdiction: CityJurisdiction,
        agency_name: str,
        agency_type: str,
        portal_link: str | None = None,
    ) -> CityAgency:
        """
        Ensure agency record exists in database.

        Args:
            jurisdiction: CityJurisdiction instance
            agency_name: Name of the agency
            agency_type: Type of agency
            portal_link: Optional portal URL

        Returns:
            CityAgency instance
        """
        agency = (
            self.db_session.query(CityAgency)
            .filter_by(jurisdiction_id=jurisdiction.id, name=agency_name)
            .first()
        )

        if not agency:
            logger.info(f"Creating agency record: {agency_name}")
            agency = CityAgency(
                jurisdiction_id=jurisdiction.id,
                name=agency_name,
                agency_type=agency_type,
                portal_link=portal_link,
            )
            self.db_session.add(agency)
            self.db_session.flush()

        return agency

    def load_requirement(
        self,
        jurisdiction: CityJurisdiction,
        agency: CityAgency,
        normalized_req: Any,
    ) -> CityRequirement:
        """
        Load a normalized requirement into the database.

        Args:
            jurisdiction: CityJurisdiction instance
            agency: CityAgency instance
            normalized_req: NormalizedRequirement instance

        Returns:
            CityRequirement instance
        """
        # Check if requirement already exists
        existing = (
            self.db_session.query(CityRequirement)
            .filter_by(
                jurisdiction_id=jurisdiction.id,
                requirement_id=normalized_req.requirement_id,
            )
            .first()
        )

        if existing:
            # Update existing requirement
            logger.info(f"Updating requirement: {normalized_req.requirement_id}")
            existing.requirement_label = normalized_req.requirement_label
            existing.requirement_type = normalized_req.normalized_type
            existing.agency_id = agency.id
            existing.applies_to = normalized_req.applies_to
            existing.required_documents = normalized_req.required_documents
            existing.submission_channel = normalized_req.submission_channel
            existing.application_url = normalized_req.application_url
            existing.inspection_required = normalized_req.inspection_required
            existing.renewal_frequency = normalized_req.renewal_frequency
            existing.fee_amount = normalized_req.fee_amount
            existing.fee_schedule = normalized_req.fee_schedule
            existing.rules = normalized_req.rules
            existing.source_url = normalized_req.source_url
            existing.last_updated = normalized_req.last_updated
            return existing
        else:
            # Create new requirement
            logger.info(f"Creating requirement: {normalized_req.requirement_id}")
            requirement = CityRequirement(
                jurisdiction_id=jurisdiction.id,
                agency_id=agency.id,
                requirement_id=normalized_req.requirement_id,
                requirement_label=normalized_req.requirement_label,
                requirement_type=normalized_req.normalized_type,
                applies_to=normalized_req.applies_to,
                required_documents=normalized_req.required_documents,
                submission_channel=normalized_req.submission_channel,
                application_url=normalized_req.application_url,
                inspection_required=normalized_req.inspection_required,
                renewal_frequency=normalized_req.renewal_frequency,
                fee_amount=normalized_req.fee_amount,
                fee_schedule=normalized_req.fee_schedule,
                rules=normalized_req.rules,
                source_url=normalized_req.source_url,
                last_updated=normalized_req.last_updated,
                is_active=True,
            )
            self.db_session.add(requirement)
            return requirement

    def run_etl_for_city(self, city: str) -> dict[str, Any]:
        """
        Run complete ETL pipeline for a specific city.

        Args:
            city: City name

        Returns:
            ETL run statistics
        """
        adapter_class = CITY_ADAPTERS.get(city)
        if not adapter_class:
            raise ValueError(f"No adapter found for city: {city}")

        # Start ETL run tracking
        jurisdiction = self.ensure_jurisdiction(city, adapter_class.STATE)

        etl_run = CityETLRun(
            jurisdiction_id=jurisdiction.id,
            run_started_at=datetime.now(UTC),
            status="running",
        )
        self.db_session.add(etl_run)
        self.db_session.flush()

        stats = {
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "errors": [],
        }

        try:
            # Extract raw data from adapter
            logger.info(f"Extracting data for {city}")
            raw_requirements = adapter_class.get_all_requirements()

            for raw_req in raw_requirements:
                try:
                    # Transform: Normalize the data
                    normalized = RequirementNormalizer.normalize(raw_req)

                    # Ensure agency exists
                    agency = self.ensure_agency(
                        jurisdiction=jurisdiction,
                        agency_name=normalized.governing_agency,
                        agency_type=normalized.agency_type,
                    )

                    # Load: Insert or update in database
                    existing = (
                        self.db_session.query(CityRequirement)
                        .filter_by(
                            jurisdiction_id=jurisdiction.id,
                            requirement_id=normalized.requirement_id,
                        )
                        .first()
                    )

                    self.load_requirement(jurisdiction, agency, normalized)

                    stats["processed"] += 1
                    if existing:
                        stats["updated"] += 1
                    else:
                        stats["inserted"] += 1

                except Exception as e:
                    logger.error(f"Error processing requirement: {e}")
                    stats["errors"].append(str(e))

            # Commit changes
            self.db_session.commit()

            # Update ETL run record
            etl_run.run_completed_at = datetime.now(UTC)
            etl_run.status = "completed" if not stats["errors"] else "completed_with_errors"
            etl_run.requirements_processed = stats["processed"]
            etl_run.requirements_inserted = stats["inserted"]
            etl_run.requirements_updated = stats["updated"]
            etl_run.errors = stats["errors"]
            self.db_session.commit()

            logger.info(f"ETL completed for {city}: {stats}")

        except Exception as e:
            logger.error(f"ETL failed for {city}: {e}")
            etl_run.status = "failed"
            etl_run.errors = [str(e)]
            etl_run.run_completed_at = datetime.now(UTC)
            self.db_session.commit()
            raise

        return stats

    def run_etl_for_all_cities(self) -> dict[str, dict[str, Any]]:
        """
        Run ETL pipeline for all available cities.

        Returns:
            Dictionary of city -> statistics
        """
        results = {}

        for city in CITY_ADAPTERS:
            try:
                logger.info(f"Starting ETL for {city}")
                stats = self.run_etl_for_city(city)
                results[city] = stats
            except Exception as e:
                logger.error(f"Failed to run ETL for {city}: {e}")
                results[city] = {"error": str(e)}

        return results


__all__ = ["CityETLOrchestrator", "CITY_ADAPTERS"]
