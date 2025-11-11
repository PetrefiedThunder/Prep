"""
City Regulatory Data ETL Pipeline

This module provides tools for extracting, transforming, and loading city
regulatory data from various sources into the compliance database.
"""

import csv
import json
import logging
import os
from datetime import datetime, UTC
from typing import Any

from database import get_session
from models import (
    CityInsuranceRequirement,
    CityJurisdiction,
    CityRegulation,
    RegulationType,
)
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CityRegulatoryETL:
    """
    ETL pipeline for city regulatory data.

    This class handles:
    - Loading data from JSON, CSV, or API sources
    - Transforming data into the proper schema
    - Loading data into the database
    - Updating existing records
    """

    def __init__(self, db: Session | None = None):
        """
        Initialize the ETL pipeline.

        Args:
            db: Database session (creates new one if not provided)
        """
        self.db = db or get_session()
        self.stats = {
            "jurisdictions_created": 0,
            "jurisdictions_updated": 0,
            "regulations_created": 0,
            "regulations_updated": 0,
            "insurance_requirements_created": 0,
            "insurance_requirements_updated": 0,
            "errors": [],
            "warnings": [],
        }

    def load_from_json(self, json_file_path: str) -> dict[str, int]:
        """
        Load regulatory data from a JSON file.

        Expected JSON structure:
        {
            "city_info": {
                "city_name": "San Francisco",
                "state": "CA",
                "county": "San Francisco County",
                ...
            },
            "regulations": [
                {
                    "regulation_type": "health_permit",
                    "title": "Food Service Establishment Permit",
                    ...
                }
            ],
            "insurance_requirements": [
                {
                    "insurance_type": "general_liability",
                    "coverage_name": "Commercial General Liability",
                    ...
                }
            ]
        }

        Args:
            json_file_path: Path to JSON file

        Returns:
            Statistics about the import
        """
        logger.info(f"Loading data from JSON file: {json_file_path}")

        if not os.path.exists(json_file_path):
            raise FileNotFoundError(f"JSON file not found: {json_file_path}")

        with open(json_file_path) as f:
            data = json.load(f)

        # Process city jurisdiction info
        if "city_info" in data:
            self._process_jurisdiction(data["city_info"])

        # Get the city
        city = self._get_city(
            data["city_info"]["city_name"],
            data["city_info"]["state"]
        )

        if not city:
            raise ValueError(f"Failed to create/find city: {data['city_info']['city_name']}")

        # Process regulations
        if "regulations" in data:
            for reg_data in data["regulations"]:
                self._process_regulation(city.id, reg_data)

        # Process insurance requirements
        if "insurance_requirements" in data:
            for ins_data in data["insurance_requirements"]:
                self._process_insurance_requirement(city.id, ins_data)

        # Commit all changes
        self.db.commit()

        logger.info("JSON import complete")
        logger.info(f"Stats: {json.dumps(self.stats, indent=2)}")

        return self.stats

    def load_from_csv(
        self,
        city_name: str,
        state: str,
        regulations_csv: str | None = None,
        insurance_csv: str | None = None,
    ) -> dict[str, int]:
        """
        Load regulatory data from CSV files.

        Regulations CSV columns:
        - regulation_type
        - title
        - description
        - local_code_reference
        - enforcement_agency
        - priority
        - applicable_facility_types (pipe-separated)
        - ... (other optional fields)

        Insurance CSV columns:
        - insurance_type
        - coverage_name
        - minimum_coverage_amount
        - applicable_facility_types (pipe-separated)
        - ... (other optional fields)

        Args:
            city_name: City name
            state: State code
            regulations_csv: Path to regulations CSV
            insurance_csv: Path to insurance requirements CSV

        Returns:
            Statistics about the import
        """
        logger.info(f"Loading CSV data for {city_name}, {state}")

        # Get or create city
        city = self._get_city(city_name, state)
        if not city:
            raise ValueError(f"City not found: {city_name}, {state}")

        # Load regulations CSV
        if regulations_csv and os.path.exists(regulations_csv):
            logger.info(f"Loading regulations from: {regulations_csv}")
            with open(regulations_csv) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Transform CSV row to regulation data
                    reg_data = self._transform_csv_regulation(row)
                    self._process_regulation(city.id, reg_data)

        # Load insurance CSV
        if insurance_csv and os.path.exists(insurance_csv):
            logger.info(f"Loading insurance requirements from: {insurance_csv}")
            with open(insurance_csv) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Transform CSV row to insurance data
                    ins_data = self._transform_csv_insurance(row)
                    self._process_insurance_requirement(city.id, ins_data)

        # Commit changes
        self.db.commit()

        logger.info("CSV import complete")
        logger.info(f"Stats: {json.dumps(self.stats, indent=2)}")

        return self.stats

    def bulk_update_city(
        self,
        city_name: str,
        state: str,
        regulations: list[dict[str, Any]],
        insurance_requirements: list[dict[str, Any]] | None = None,
        jurisdiction_info: dict[str, Any] | None = None,
    ) -> dict[str, int]:
        """
        Bulk update all data for a city.

        Args:
            city_name: City name
            state: State code
            regulations: List of regulation dictionaries
            insurance_requirements: List of insurance requirement dictionaries
            jurisdiction_info: Optional jurisdiction information to update

        Returns:
            Statistics about the update
        """
        logger.info(f"Bulk updating data for {city_name}, {state}")

        # Update jurisdiction info if provided
        if jurisdiction_info:
            jurisdiction_info.update({
                "city_name": city_name,
                "state": state,
            })
            self._process_jurisdiction(jurisdiction_info)

        # Get city
        city = self._get_city(city_name, state)
        if not city:
            raise ValueError(f"City not found: {city_name}, {state}")

        # Process regulations
        for reg_data in regulations:
            self._process_regulation(city.id, reg_data)

        # Process insurance requirements
        if insurance_requirements:
            for ins_data in insurance_requirements:
                self._process_insurance_requirement(city.id, ins_data)

        # Commit changes
        self.db.commit()

        logger.info("Bulk update complete")
        logger.info(f"Stats: {json.dumps(self.stats, indent=2)}")

        return self.stats

    def _process_jurisdiction(self, jurisdiction_data: dict[str, Any]) -> None:
        """Process city jurisdiction data"""
        city_name = jurisdiction_data.get("city_name")
        state = jurisdiction_data.get("state")

        if not city_name or not state:
            self.stats["errors"].append("Missing city_name or state in jurisdiction data")
            return

        # Check if jurisdiction exists
        existing = self.db.query(CityJurisdiction).filter(
            CityJurisdiction.city_name.ilike(city_name),
            CityJurisdiction.state == state.upper(),
        ).first()

        if existing:
            # Update existing
            for key, value in jurisdiction_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.now(UTC)
            self.stats["jurisdictions_updated"] += 1
            logger.info(f"Updated jurisdiction: {city_name}, {state}")
        else:
            # Create new
            jurisdiction = CityJurisdiction(
                **jurisdiction_data,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self.db.add(jurisdiction)
            self.stats["jurisdictions_created"] += 1
            logger.info(f"Created jurisdiction: {city_name}, {state}")

    def _process_regulation(self, city_id: str, regulation_data: dict[str, Any]) -> None:
        """Process regulation data"""
        try:
            regulation_type = regulation_data.get("regulation_type")
            title = regulation_data.get("title")

            if not regulation_type or not title:
                self.stats["errors"].append(f"Missing regulation_type or title: {regulation_data}")
                return

            # Validate regulation_type
            if regulation_type not in [rt.value for rt in RegulationType]:
                self.stats["warnings"].append(f"Unknown regulation_type: {regulation_type}")

            # Ensure applicable_facility_types is a list
            facility_types = regulation_data.get("applicable_facility_types", [])
            if isinstance(facility_types, str):
                # Handle pipe-separated string
                facility_types = [ft.strip() for ft in facility_types.split("|")]
            regulation_data["applicable_facility_types"] = facility_types

            # Convert date strings to datetime objects
            for date_field in ["effective_date", "expiration_date", "last_verified"]:
                if date_field in regulation_data and isinstance(regulation_data[date_field], str):
                    try:
                        regulation_data[date_field] = datetime.fromisoformat(
                            regulation_data[date_field].replace('Z', '+00:00')
                        )
                    except ValueError:
                        self.stats["warnings"].append(f"Invalid date format for {date_field}: {regulation_data[date_field]}")
                        regulation_data[date_field] = None

            # Check if regulation exists
            existing = self.db.query(CityRegulation).filter(
                CityRegulation.city_id == city_id,
                CityRegulation.regulation_type == regulation_type,
                CityRegulation.title == title,
            ).first()

            if existing:
                # Update existing
                for key, value in regulation_data.items():
                    if hasattr(existing, key) and key not in ["id", "city_id", "created_at"]:
                        setattr(existing, key, value)
                existing.updated_at = datetime.now(UTC)
                self.stats["regulations_updated"] += 1
                logger.debug(f"Updated regulation: {title}")
            else:
                # Create new
                regulation = CityRegulation(
                    city_id=city_id,
                    **regulation_data,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                self.db.add(regulation)
                self.stats["regulations_created"] += 1
                logger.debug(f"Created regulation: {title}")

        except Exception as e:
            self.stats["errors"].append(f"Failed to process regulation: {str(e)}")
            logger.error(f"Error processing regulation: {str(e)}")

    def _process_insurance_requirement(self, city_id: str, insurance_data: dict[str, Any]) -> None:
        """Process insurance requirement data"""
        try:
            insurance_type = insurance_data.get("insurance_type")
            coverage_name = insurance_data.get("coverage_name")

            if not insurance_type or not coverage_name:
                self.stats["errors"].append(f"Missing insurance_type or coverage_name: {insurance_data}")
                return

            # Ensure applicable_facility_types is a list
            facility_types = insurance_data.get("applicable_facility_types", [])
            if isinstance(facility_types, str):
                facility_types = [ft.strip() for ft in facility_types.split("|")]
            insurance_data["applicable_facility_types"] = facility_types

            # Convert minimum_coverage_amount to float
            if "minimum_coverage_amount" in insurance_data:
                insurance_data["minimum_coverage_amount"] = float(insurance_data["minimum_coverage_amount"])

            # Check if requirement exists
            existing = self.db.query(CityInsuranceRequirement).filter(
                CityInsuranceRequirement.city_id == city_id,
                CityInsuranceRequirement.insurance_type == insurance_type,
            ).first()

            if existing:
                # Update existing
                for key, value in insurance_data.items():
                    if hasattr(existing, key) and key not in ["id", "city_id", "created_at"]:
                        setattr(existing, key, value)
                existing.updated_at = datetime.now(UTC)
                self.stats["insurance_requirements_updated"] += 1
                logger.debug(f"Updated insurance requirement: {coverage_name}")
            else:
                # Create new
                insurance_req = CityInsuranceRequirement(
                    city_id=city_id,
                    **insurance_data,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                self.db.add(insurance_req)
                self.stats["insurance_requirements_created"] += 1
                logger.debug(f"Created insurance requirement: {coverage_name}")

        except Exception as e:
            self.stats["errors"].append(f"Failed to process insurance requirement: {str(e)}")
            logger.error(f"Error processing insurance requirement: {str(e)}")

    def _get_city(self, city_name: str, state: str) -> CityJurisdiction | None:
        """Get city jurisdiction by name and state"""
        return self.db.query(CityJurisdiction).filter(
            CityJurisdiction.city_name.ilike(city_name),
            CityJurisdiction.state == state.upper(),
        ).first()

    def _transform_csv_regulation(self, row: dict[str, str]) -> dict[str, Any]:
        """Transform CSV row to regulation data structure"""
        # Parse applicable facility types
        facility_types_str = row.get("applicable_facility_types", "")
        facility_types = [ft.strip() for ft in facility_types_str.split("|") if ft.strip()]

        # Parse JSON fields if present
        requirements = row.get("requirements")
        if requirements:
            try:
                requirements = json.loads(requirements)
            except json.JSONDecodeError:
                requirements = None

        application_process = row.get("application_process")
        if application_process:
            try:
                application_process = json.loads(application_process)
            except json.JSONDecodeError:
                application_process = None

        required_documents = row.get("required_documents")
        if required_documents:
            try:
                required_documents = json.loads(required_documents)
            except json.JSONDecodeError:
                required_documents = [doc.strip() for doc in required_documents.split("|") if doc.strip()]

        fees = row.get("fees")
        if fees:
            try:
                fees = json.loads(fees)
            except json.JSONDecodeError:
                fees = None

        return {
            "regulation_type": row.get("regulation_type"),
            "title": row.get("title"),
            "description": row.get("description"),
            "local_code_reference": row.get("local_code_reference"),
            "cfr_citation": row.get("cfr_citation"),
            "state_code_reference": row.get("state_code_reference"),
            "enforcement_agency": row.get("enforcement_agency", ""),
            "agency_contact": row.get("agency_contact"),
            "agency_phone": row.get("agency_phone"),
            "agency_url": row.get("agency_url"),
            "penalty_for_violation": row.get("penalty_for_violation"),
            "fine_amount_min": float(row["fine_amount_min"]) if row.get("fine_amount_min") else None,
            "fine_amount_max": float(row["fine_amount_max"]) if row.get("fine_amount_max") else None,
            "requirements": requirements,
            "application_process": application_process,
            "required_documents": required_documents,
            "fees": fees,
            "applicable_facility_types": facility_types,
            "employee_count_threshold": int(row["employee_count_threshold"]) if row.get("employee_count_threshold") else None,
            "revenue_threshold": float(row["revenue_threshold"]) if row.get("revenue_threshold") else None,
            "is_active": row.get("is_active", "true").lower() == "true",
            "priority": row.get("priority", "medium"),
            "renewal_period_days": int(row["renewal_period_days"]) if row.get("renewal_period_days") else None,
            "data_source": row.get("data_source"),
            "notes": row.get("notes"),
        }

    def _transform_csv_insurance(self, row: dict[str, str]) -> dict[str, Any]:
        """Transform CSV row to insurance requirement data structure"""
        # Parse applicable facility types
        facility_types_str = row.get("applicable_facility_types", "")
        facility_types = [ft.strip() for ft in facility_types_str.split("|") if ft.strip()]

        return {
            "insurance_type": row.get("insurance_type"),
            "coverage_name": row.get("coverage_name"),
            "description": row.get("description"),
            "minimum_coverage_amount": float(row.get("minimum_coverage_amount", 0)),
            "per_occurrence_limit": float(row["per_occurrence_limit"]) if row.get("per_occurrence_limit") else None,
            "aggregate_limit": float(row["aggregate_limit"]) if row.get("aggregate_limit") else None,
            "deductible_max": float(row["deductible_max"]) if row.get("deductible_max") else None,
            "applicable_facility_types": facility_types,
            "employee_count_threshold": int(row["employee_count_threshold"]) if row.get("employee_count_threshold") else None,
            "local_ordinance": row.get("local_ordinance"),
            "state_requirement": row.get("state_requirement"),
            "is_mandatory": row.get("is_mandatory", "true").lower() == "true",
            "notes": row.get("notes"),
        }

    def export_city_data_to_json(
        self,
        city_name: str,
        state: str,
        output_file: str,
    ) -> None:
        """
        Export city data to JSON file.

        Args:
            city_name: City name
            state: State code
            output_file: Output JSON file path
        """
        logger.info(f"Exporting {city_name}, {state} to {output_file}")

        # Get city
        city = self._get_city(city_name, state)
        if not city:
            raise ValueError(f"City not found: {city_name}, {state}")

        # Get regulations
        regulations = self.db.query(CityRegulation).filter(
            CityRegulation.city_id == city.id
        ).all()

        # Get insurance requirements
        insurance_reqs = self.db.query(CityInsuranceRequirement).filter(
            CityInsuranceRequirement.city_id == city.id
        ).all()

        # Build export data
        export_data = {
            "city_info": {
                "city_name": city.city_name,
                "state": city.state,
                "county": city.county,
                "fips_code": city.fips_code,
                "population": city.population,
                "health_department_name": city.health_department_name,
                "health_department_url": city.health_department_url,
                "business_licensing_dept": city.business_licensing_dept,
                "business_licensing_url": city.business_licensing_url,
                "fire_department_name": city.fire_department_name,
                "fire_department_url": city.fire_department_url,
                "phone": city.phone,
                "timezone": city.timezone,
            },
            "regulations": [],
            "insurance_requirements": [],
        }

        # Add regulations
        for reg in regulations:
            reg_dict = {
                "regulation_type": reg.regulation_type,
                "title": reg.title,
                "description": reg.description,
                "local_code_reference": reg.local_code_reference,
                "enforcement_agency": reg.enforcement_agency,
                "priority": reg.priority,
                "applicable_facility_types": reg.applicable_facility_types,
                "requirements": reg.requirements,
                "fees": reg.fees,
                "is_active": reg.is_active,
            }
            export_data["regulations"].append(reg_dict)

        # Add insurance requirements
        for ins in insurance_reqs:
            ins_dict = {
                "insurance_type": ins.insurance_type,
                "coverage_name": ins.coverage_name,
                "minimum_coverage_amount": ins.minimum_coverage_amount,
                "applicable_facility_types": ins.applicable_facility_types,
                "is_mandatory": ins.is_mandatory,
            }
            export_data["insurance_requirements"].append(ins_dict)

        # Write to file
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported {len(regulations)} regulations and {len(insurance_reqs)} insurance requirements")

    def close(self):
        """Close the database session"""
        self.db.close()


def main():
    """Example usage of the ETL pipeline"""
    print("=" * 80)
    print("City Regulatory Data ETL Pipeline")
    print("=" * 80)
    print()

    # Create ETL instance
    etl = CityRegulatoryETL()

    # Example: Export existing city data
    try:
        etl.export_city_data_to_json(
            city_name="San Francisco",
            state="CA",
            output_file="/home/user/Prep/data/cities/san_francisco_ca_example.json"
        )
        print("✓ Exported San Francisco data to JSON")
    except Exception as e:
        print(f"✗ Export failed: {str(e)}")

    # Close session
    etl.close()

    print()
    print("=" * 80)
    print("ETL pipeline demo complete")
    print("=" * 80)
    print()
    print("Usage:")
    print("1. Load from JSON: etl.load_from_json('city_data.json')")
    print("2. Load from CSV: etl.load_from_csv('City', 'ST', 'regs.csv', 'ins.csv')")
    print("3. Bulk update: etl.bulk_update_city('City', 'ST', regulations, insurance)")
    print("4. Export: etl.export_city_data_to_json('City', 'ST', 'output.json')")
    print()


if __name__ == "__main__":
    main()
