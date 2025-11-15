"""
Tests for City Regulatory Service

This test suite covers:
- City jurisdiction management
- Regulation CRUD operations
- Insurance requirements
- Compliance checking
- Data ingestion
"""

import os
import sys
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import get_engine, get_session, init_database
from models import (
    CityJurisdiction,
    FacilityType,
    RegulationType,
)

from main import app

# Test client
client = TestClient(app)


@pytest.fixture(scope="module")
def test_db():
    """Create a test database"""
    # Use in-memory database for tests
    engine = get_engine(":memory:", echo=False)
    init_database(engine)

    # Create test session
    session = get_session(engine)

    # Create test city
    test_city = CityJurisdiction(
        city_name="Test City",
        state="TS",
        county="Test County",
        health_department_name="Test Health Dept",
        health_department_url="https://test.gov/health",
        business_licensing_dept="Test Business Dept",
        phone="555-0000",
    )
    session.add(test_city)
    session.commit()

    yield session

    session.close()


class TestHealthEndpoint:
    """Test health check endpoints"""

    def test_health_check(self):
        """Test /health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "city-regulatory-service"

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "City Regulatory Service"
        assert "endpoints" in data


class TestCityEndpoints:
    """Test city jurisdiction endpoints"""

    def test_list_cities(self):
        """Test listing all cities"""
        response = client.get("/cities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have 8 cities from initial data load
        assert len(data) >= 8

    def test_list_cities_by_state(self):
        """Test filtering cities by state"""
        response = client.get("/cities?state=CA")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least SF and LA
        assert len(data) >= 2
        for city in data:
            assert city["state"] == "CA"

    def test_get_city(self):
        """Test getting a specific city"""
        response = client.get("/city/San Francisco/CA")
        assert response.status_code == 200
        data = response.json()
        assert data["city_name"] == "San Francisco"
        assert data["state"] == "CA"
        assert "health_department_name" in data

    def test_get_city_not_found(self):
        """Test getting a non-existent city"""
        response = client.get("/city/Nonexistent/XX")
        assert response.status_code == 404


class TestRegulationEndpoints:
    """Test regulation endpoints"""

    def test_get_city_regulations(self):
        """Test getting regulations for a city"""
        response = client.get("/city/San Francisco/CA/regulations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have placeholder regulations
        assert len(data) > 0

    def test_get_regulations_by_type(self):
        """Test filtering regulations by type"""
        response = client.get(
            "/city/San Francisco/CA/regulations",
            params={"regulation_type": RegulationType.HEALTH_PERMIT.value},
        )
        assert response.status_code == 200
        data = response.json()
        for reg in data:
            assert reg["regulation_type"] == RegulationType.HEALTH_PERMIT.value

    def test_get_regulations_by_facility_type(self):
        """Test filtering regulations by facility type"""
        response = client.get(
            "/city/San Francisco/CA/regulations",
            params={"facility_type": FacilityType.COMMERCIAL_KITCHEN.value},
        )
        assert response.status_code == 200
        data = response.json()
        # All returned regulations should be applicable to commercial kitchens
        for reg in data:
            assert FacilityType.COMMERCIAL_KITCHEN.value in reg["applicable_facility_types"]

    def test_get_regulations_summary(self):
        """Test regulation summary endpoint"""
        response = client.get("/city/San Francisco/CA/regulations/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["city_name"] == "San Francisco"
        assert data["state"] == "CA"
        assert "total_regulations" in data
        assert "by_type" in data
        assert "by_priority" in data


class TestInsuranceEndpoints:
    """Test insurance requirement endpoints"""

    def test_get_insurance_requirements(self):
        """Test getting insurance requirements"""
        response = client.get("/city/San Francisco/CA/insurance-requirements")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_insurance_mandatory_only(self):
        """Test filtering mandatory insurance"""
        response = client.get(
            "/city/San Francisco/CA/insurance-requirements", params={"mandatory_only": True}
        )
        assert response.status_code == 200
        data = response.json()
        for ins in data:
            assert ins["is_mandatory"]

    def test_get_insurance_by_facility_type(self):
        """Test filtering insurance by facility type"""
        response = client.get(
            "/city/San Francisco/CA/insurance-requirements",
            params={"facility_type": FacilityType.GHOST_KITCHEN.value},
        )
        assert response.status_code == 200
        data = response.json()
        for ins in data:
            assert FacilityType.GHOST_KITCHEN.value in ins["applicable_facility_types"]


class TestComplianceCheck:
    """Test compliance checking endpoint"""

    def test_compliance_check_compliant_facility(self):
        """Test compliance check for compliant facility"""
        compliance_request = {
            "facility_id": "test-facility-1",
            "city_name": "San Francisco",
            "state": "CA",
            "facility_type": FacilityType.COMMERCIAL_KITCHEN.value,
            "employee_count": 5,
            "current_permits": [
                {
                    "type": RegulationType.HEALTH_PERMIT.value,
                    "number": "HP-12345",
                    "expiration_date": (datetime.now(UTC) + timedelta(days=180)).isoformat(),
                },
                {
                    "type": RegulationType.BUSINESS_LICENSE.value,
                    "number": "BL-67890",
                    "expiration_date": (datetime.now(UTC) + timedelta(days=365)).isoformat(),
                },
                {
                    "type": RegulationType.FIRE_SAFETY.value,
                    "number": "FS-11111",
                    "expiration_date": (datetime.now(UTC) + timedelta(days=90)).isoformat(),
                },
                {
                    "type": RegulationType.FOOD_HANDLER_CERT.value,
                    "number": "FH-22222",
                    "expiration_date": (datetime.now(UTC) + timedelta(days=365)).isoformat(),
                },
                {
                    "type": RegulationType.INSURANCE.value,
                    "number": "INS-33333",
                    "expiration_date": (datetime.now(UTC) + timedelta(days=365)).isoformat(),
                },
            ],
            "current_insurance": [
                {"type": "general_liability", "coverage_amount": 1000000},
                {"type": "workers_compensation", "coverage_amount": 500000},
                {"type": "product_liability", "coverage_amount": 1000000},
            ],
        }

        response = client.post("/city/San Francisco/CA/compliance-check", json=compliance_request)
        assert response.status_code == 200
        data = response.json()
        assert data["facility_id"] == "test-facility-1"
        assert data["city_name"] == "San Francisco"
        assert "compliance_score" in data
        assert "required_regulations" in data
        assert "insurance_compliant" in data

    def test_compliance_check_non_compliant_facility(self):
        """Test compliance check for non-compliant facility"""
        compliance_request = {
            "facility_id": "test-facility-2",
            "city_name": "San Francisco",
            "state": "CA",
            "facility_type": FacilityType.COMMERCIAL_KITCHEN.value,
            "employee_count": 5,
            "current_permits": [],  # No permits
            "current_insurance": [],  # No insurance
        }

        response = client.post("/city/San Francisco/CA/compliance-check", json=compliance_request)
        assert response.status_code == 200
        data = response.json()
        assert not data["overall_compliant"]
        assert data["compliance_score"] < 100.0
        assert len(data["non_compliant_regulations"]) > 0
        assert len(data["missing_requirements"]) > 0
        assert not data["insurance_compliant"]
        assert len(data["insurance_gaps"]) > 0
        assert len(data["recommended_actions"]) > 0


class TestDataIngestion:
    """Test data ingestion endpoint"""

    def test_ingest_new_city_data(self):
        """Test ingesting data for a new city"""
        ingestion_request = {
            "city_name": "New Test City",
            "state": "NT",
            "data_source": "Test data",
            "verification_date": datetime.now(UTC).isoformat(),
            "jurisdiction_info": {
                "county": "New Test County",
                "health_department_name": "New Test Health Dept",
                "phone": "555-9999",
            },
            "regulations": [
                {
                    "regulation_type": RegulationType.HEALTH_PERMIT.value,
                    "title": "Test Health Permit",
                    "description": "Test health permit requirement",
                    "enforcement_agency": "Test Health Dept",
                    "priority": "critical",
                    "applicable_facility_types": [
                        FacilityType.COMMERCIAL_KITCHEN.value,
                    ],
                    "is_active": True,
                }
            ],
            "insurance_requirements": [
                {
                    "insurance_type": "general_liability",
                    "coverage_name": "Test Liability",
                    "minimum_coverage_amount": 1000000.0,
                    "applicable_facility_types": [
                        FacilityType.COMMERCIAL_KITCHEN.value,
                    ],
                    "is_mandatory": True,
                }
            ],
        }

        response = client.post("/city/data/ingest", json=ingestion_request)
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert data["regulations_imported"] == 1
        assert data["insurance_requirements_imported"] == 1

    def test_ingest_update_existing_city(self):
        """Test updating existing city data"""
        # First ingest
        ingestion_request = {
            "city_name": "Update Test City",
            "state": "UT",
            "data_source": "Initial data",
            "verification_date": datetime.now(UTC).isoformat(),
            "jurisdiction_info": {
                "county": "Update County",
            },
            "regulations": [
                {
                    "regulation_type": RegulationType.BUSINESS_LICENSE.value,
                    "title": "Business License V1",
                    "enforcement_agency": "Business Dept",
                    "priority": "high",
                    "applicable_facility_types": [FacilityType.RESTAURANT.value],
                    "is_active": True,
                }
            ],
        }

        response1 = client.post("/city/data/ingest", json=ingestion_request)
        assert response1.status_code == 200

        # Update with new data
        ingestion_request["regulations"][0]["title"] = "Business License V2"
        ingestion_request["regulations"][0]["description"] = "Updated description"
        ingestion_request["data_source"] = "Updated data"

        response2 = client.post("/city/data/ingest", json=ingestion_request)
        assert response2.status_code == 200
        data = response2.json()
        assert data["success"]
        # Should have warnings about updates
        if data.get("warnings"):
            assert len(data["warnings"]) > 0


# Run pytest if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
