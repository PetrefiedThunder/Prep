"""
Federal Regulatory Integration

This module integrates city-level regulations with the federal regulatory layer,
creating the complete regulatory chain:
Federal Scope → State Code → City Ordinance → Facility Compliance
"""

import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from models import CityRegulation, CityJurisdiction
from database import get_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FederalRegulatoryIntegration:
    """
    Integration layer between city regulations and federal regulatory service.

    This class provides:
    - Linking city regulations to federal scopes via CFR citations
    - Validating federal certification requirements at city level
    - Providing complete regulatory chain information
    """

    def __init__(
        self,
        federal_service_url: str = "http://localhost:8001",
        db: Optional[Session] = None,
    ):
        """
        Initialize the integration layer.

        Args:
            federal_service_url: URL of the federal regulatory service
            db: Database session (creates new one if not provided)
        """
        self.federal_service_url = federal_service_url.rstrip("/")
        self.db = db or get_session()
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_federal_scopes(self) -> List[Dict[str, Any]]:
        """
        Get all federal scopes from the federal regulatory service.

        Returns:
            List of federal scopes with CFR citations
        """
        try:
            response = await self.client.get(f"{self.federal_service_url}/federal/scopes")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch federal scopes: {str(e)}")
            return []

    async def get_federal_scope_by_cfr(self, cfr_citation: str) -> Optional[Dict[str, Any]]:
        """
        Get federal scope by CFR citation.

        Args:
            cfr_citation: CFR citation (e.g., "21 CFR 117")

        Returns:
            Federal scope information or None
        """
        scopes = await self.get_federal_scopes()
        for scope in scopes:
            if scope.get("cfr_title_part_section") == cfr_citation:
                return scope
        return None

    async def get_certifiers_for_scope(
        self,
        cfr_citation: str,
        state: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get authorized certification bodies for a federal scope.

        Args:
            cfr_citation: CFR citation
            state: Optional state filter

        Returns:
            List of authorized certifiers
        """
        try:
            params = {}
            if state:
                params["state"] = state

            # First get the scope to find scope_id
            scope = await self.get_federal_scope_by_cfr(cfr_citation)
            if not scope:
                logger.warning(f"No federal scope found for CFR: {cfr_citation}")
                return []

            # Get certifiers for this scope
            response = await self.client.get(
                f"{self.federal_service_url}/federal/certification-bodies",
                params={"scope_id": scope["id"], **params}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch certifiers: {str(e)}")
            return []

    async def link_city_regulation_to_federal(
        self,
        regulation_id: str,
        cfr_citation: str,
    ) -> bool:
        """
        Link a city regulation to a federal scope via CFR citation.

        Args:
            regulation_id: City regulation ID
            cfr_citation: Federal CFR citation to link to

        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify the federal scope exists
            scope = await self.get_federal_scope_by_cfr(cfr_citation)
            if not scope:
                logger.error(f"Federal scope not found: {cfr_citation}")
                return False

            # Update the city regulation
            regulation = self.db.query(CityRegulation).filter(
                CityRegulation.id == regulation_id
            ).first()

            if not regulation:
                logger.error(f"City regulation not found: {regulation_id}")
                return False

            regulation.cfr_citation = cfr_citation
            regulation.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Linked regulation '{regulation.title}' to federal scope: {cfr_citation}")
            return True

        except Exception as e:
            logger.error(f"Failed to link regulation to federal scope: {str(e)}")
            self.db.rollback()
            return False

    async def get_complete_regulatory_chain(
        self,
        city_name: str,
        state: str,
        regulation_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get the complete regulatory chain from federal to city level.

        Args:
            city_name: City name
            state: State code
            regulation_type: Optional filter by regulation type

        Returns:
            Complete regulatory chain information
        """
        # Get city
        city = self.db.query(CityJurisdiction).filter(
            CityJurisdiction.city_name.ilike(city_name),
            CityJurisdiction.state == state.upper(),
        ).first()

        if not city:
            return {
                "error": f"City not found: {city_name}, {state}",
            }

        # Get city regulations
        query = self.db.query(CityRegulation).filter(
            CityRegulation.city_id == city.id,
            CityRegulation.is_active,
        )

        if regulation_type:
            query = query.filter(CityRegulation.regulation_type == regulation_type)

        city_regulations = query.all()

        # Build regulatory chain
        regulatory_chain = {
            "city": {
                "name": city.city_name,
                "state": city.state,
                "county": city.county,
            },
            "total_city_regulations": len(city_regulations),
            "regulations": [],
        }

        # For each city regulation, get federal linkage
        for reg in city_regulations:
            reg_info = {
                "city_regulation": {
                    "id": reg.id,
                    "type": reg.regulation_type,
                    "title": reg.title,
                    "local_code_reference": reg.local_code_reference,
                    "enforcement_agency": reg.enforcement_agency,
                },
                "state_code_reference": reg.state_code_reference,
                "federal_scope": None,
                "authorized_certifiers": [],
            }

            # If linked to federal scope, get details
            if reg.cfr_citation:
                scope = await self.get_federal_scope_by_cfr(reg.cfr_citation)
                if scope:
                    reg_info["federal_scope"] = {
                        "name": scope.get("name"),
                        "cfr_citation": scope.get("cfr_title_part_section"),
                        "program_reference": scope.get("program_reference"),
                    }

                    # Get authorized certifiers
                    certifiers = await self.get_certifiers_for_scope(
                        reg.cfr_citation,
                        state=state,
                    )
                    reg_info["authorized_certifiers"] = [
                        {
                            "name": c.get("name"),
                            "accreditation_body": c.get("accreditation_body"),
                            "status": c.get("status"),
                        }
                        for c in certifiers[:5]  # Limit to 5 certifiers
                    ]

            regulatory_chain["regulations"].append(reg_info)

        return regulatory_chain

    async def validate_facility_federal_compliance(
        self,
        facility_id: str,
        city_name: str,
        state: str,
        certification_body_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate that a facility's federal certifications are valid for city requirements.

        Args:
            facility_id: Facility ID
            city_name: City name
            state: State code
            certification_body_name: Name of the certification body used

        Returns:
            Validation results
        """
        # Get city regulations with federal linkages
        city = self.db.query(CityJurisdiction).filter(
            CityJurisdiction.city_name.ilike(city_name),
            CityJurisdiction.state == state.upper(),
        ).first()

        if not city:
            return {
                "valid": False,
                "error": f"City not found: {city_name}, {state}",
            }

        # Get regulations with CFR citations
        regulations = self.db.query(CityRegulation).filter(
            CityRegulation.city_id == city.id,
            CityRegulation.is_active,
            CityRegulation.cfr_citation.isnot(None),
        ).all()

        validation_results = {
            "facility_id": facility_id,
            "city": city_name,
            "state": state,
            "federal_requirements": [],
            "overall_valid": True,
        }

        # Check each federal requirement
        for reg in regulations:
            requirement = {
                "regulation_title": reg.title,
                "cfr_citation": reg.cfr_citation,
                "valid": False,
                "message": "",
            }

            if certification_body_name:
                # Check if the certification body is authorized for this scope
                certifiers = await self.get_certifiers_for_scope(reg.cfr_citation, state)
                certifier_names = [c.get("name", "").lower() for c in certifiers]

                if certification_body_name.lower() in certifier_names:
                    requirement["valid"] = True
                    requirement["message"] = f"Certification body '{certification_body_name}' is authorized"
                else:
                    requirement["valid"] = False
                    requirement["message"] = f"Certification body '{certification_body_name}' not authorized for {reg.cfr_citation}"
                    validation_results["overall_valid"] = False
            else:
                requirement["message"] = "No certification body provided"
                validation_results["overall_valid"] = False

            validation_results["federal_requirements"].append(requirement)

        return validation_results

    async def get_recommended_certifiers(
        self,
        city_name: str,
        state: str,
        facility_type: str,
    ) -> Dict[str, Any]:
        """
        Get recommended certification bodies for a facility type in a city.

        Args:
            city_name: City name
            state: State code
            facility_type: Type of facility

        Returns:
            Recommended certifiers with coverage information
        """
        # Get city regulations applicable to facility type
        city = self.db.query(CityJurisdiction).filter(
            CityJurisdiction.city_name.ilike(city_name),
            CityJurisdiction.state == state.upper(),
        ).first()

        if not city:
            return {
                "error": f"City not found: {city_name}, {state}",
            }

        regulations = self.db.query(CityRegulation).filter(
            CityRegulation.city_id == city.id,
            CityRegulation.is_active,
            CityRegulation.cfr_citation.isnot(None),
        ).all()

        # Filter by facility type
        applicable_regulations = [
            r for r in regulations
            if facility_type in r.applicable_facility_types
        ]

        # Get unique CFR citations
        cfr_citations = list(set([r.cfr_citation for r in applicable_regulations]))

        # Get certifiers for each scope
        certifier_coverage = {}
        for cfr in cfr_citations:
            certifiers = await self.get_certifiers_for_scope(cfr, state)
            for certifier in certifiers:
                name = certifier.get("name")
                if name not in certifier_coverage:
                    certifier_coverage[name] = {
                        "name": name,
                        "accreditation_body": certifier.get("accreditation_body"),
                        "covered_scopes": [],
                        "coverage_count": 0,
                    }
                certifier_coverage[name]["covered_scopes"].append(cfr)
                certifier_coverage[name]["coverage_count"] += 1

        # Sort by coverage count
        recommended = sorted(
            certifier_coverage.values(),
            key=lambda x: x["coverage_count"],
            reverse=True,
        )

        return {
            "city": city_name,
            "state": state,
            "facility_type": facility_type,
            "total_federal_requirements": len(cfr_citations),
            "federal_scopes_required": cfr_citations,
            "recommended_certifiers": recommended[:10],  # Top 10
        }

    async def close(self):
        """Close the HTTP client and database session"""
        await self.client.aclose()
        self.db.close()


async def main():
    """Example usage of the federal integration"""
    print("=" * 80)
    print("Federal Regulatory Integration - Demo")
    print("=" * 80)
    print()

    integration = FederalRegulatoryIntegration()

    try:
        # Get federal scopes
        print("Fetching federal scopes...")
        scopes = await integration.get_federal_scopes()
        print(f"✓ Found {len(scopes)} federal scopes")
        print()

        # Get complete regulatory chain for San Francisco
        print("Getting regulatory chain for San Francisco, CA...")
        chain = await integration.get_complete_regulatory_chain(
            city_name="San Francisco",
            state="CA",
        )
        print(f"✓ Found {chain.get('total_city_regulations', 0)} city regulations")
        print()

        # Get recommended certifiers
        print("Getting recommended certifiers for commercial kitchen...")
        recommendations = await integration.get_recommended_certifiers(
            city_name="San Francisco",
            state="CA",
            facility_type="commercial_kitchen",
        )
        print(f"✓ Found {len(recommendations.get('recommended_certifiers', []))} certifiers")
        print()

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        print("Note: This demo requires the federal regulatory service to be running")
        print("Start it with: python apps/federal_regulatory_service/main.py")

    finally:
        await integration.close()

    print("=" * 80)
    print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
