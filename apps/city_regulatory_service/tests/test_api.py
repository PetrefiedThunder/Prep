"""Tests for city regulatory API endpoints."""

from fastapi.testclient import TestClient

from apps.city_regulatory_service.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self):
        """Test health check returns 200."""
        response = client.get("/healthz")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "available_cities" in data

    def test_health_check_has_cities(self):
        """Test health check includes supported cities."""
        response = client.get("/healthz")
        data = response.json()

        cities = data["available_cities"]
        assert "San Francisco" in cities
        assert "New York" in cities


class TestComplianceEndpoints:
    """Test compliance query endpoints."""

    def test_list_requirements_no_filter(self):
        """Test listing requirements without filters."""
        response = client.get("/compliance/requirements")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_list_requirements_with_jurisdiction_filter(self):
        """Test filtering by jurisdiction."""
        response = client.get("/compliance/requirements?jurisdiction=San Francisco")
        assert response.status_code == 200

        data = response.json()
        # May be empty if DB not populated, but should not error
        assert isinstance(data, list)

    def test_compliance_query_missing_jurisdiction(self):
        """Test compliance query with missing jurisdiction."""
        response = client.post(
            "/compliance/query",
            json={"business_type": "restaurant"}
        )
        # Should return 422 for validation error
        assert response.status_code == 422

    def test_compliance_query_valid(self):
        """Test valid compliance query."""
        response = client.post(
            "/compliance/query",
            json={
                "jurisdiction": "San Francisco",
                "business_type": "restaurant"
            }
        )
        # May 404 if DB not populated, but should not 500
        assert response.status_code in [200, 404]


class TestJurisdictionEndpoints:
    """Test jurisdiction endpoints."""

    def test_list_jurisdictions(self):
        """Test listing jurisdictions."""
        response = client.get("/cities/jurisdictions")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_list_agencies_invalid_city(self):
        """Test listing agencies for invalid city."""
        response = client.get("/cities/InvalidCity/agencies")
        # Should return 404 for unknown city
        assert response.status_code == 404


class TestETLEndpoints:
    """Test ETL endpoints."""

    def test_etl_run_invalid_city(self):
        """Test ETL run with invalid city."""
        response = client.post(
            "/etl/run",
            json={"city": "InvalidCity"}
        )
        # Should return 400 for unsupported city
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "not supported" in data["detail"].lower()

    def test_etl_run_valid_structure(self):
        """Test ETL run has valid response structure."""
        # Note: This will actually run ETL if DB is available
        # In production tests, you'd mock the DB
        response = client.post(
            "/etl/run",
            json={"city": "San Francisco"}
        )

        # May fail if no DB, but structure should be consistent
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "cities_processed" in data
            assert "results" in data
