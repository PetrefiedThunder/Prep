"""
Integration tests for Federal Regulatory Service API endpoints.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self):
        """Test health check returns OK status."""
        response = client.get("/healthz")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ["ok", "degraded"]
        assert "version" in data
        assert "database_path" in data
        assert "database_exists" in data
        assert "record_counts" in data


class TestScopesEndpoint:
    """Tests for scopes endpoints."""

    def test_list_scopes(self):
        """Test listing all scopes."""
        response = client.get("/federal/scopes")
        assert response.status_code == 200

        scopes = response.json()
        assert isinstance(scopes, list)
        assert len(scopes) > 0

        # Check first scope has required fields
        scope = scopes[0]
        assert "id" in scope
        assert "name" in scope
        assert "cfr_title_part_section" in scope

    def test_scopes_include_pchf(self):
        """Test that PCHF scope is included."""
        response = client.get("/federal/scopes")
        scopes = response.json()

        scope_names = [s["name"] for s in scopes]
        assert any("Human Food" in name for name in scope_names)


class TestAccreditationBodiesEndpoint:
    """Tests for accreditation bodies endpoints."""

    def test_list_accreditation_bodies(self):
        """Test listing all accreditation bodies."""
        response = client.get("/federal/accreditation-bodies")
        assert response.status_code == 200

        abs = response.json()
        assert isinstance(abs, list)
        assert len(abs) >= 2  # At least ANAB and IAS

        # Check structure
        ab = abs[0]
        assert "id" in ab
        assert "name" in ab
        assert "url" in ab

    def test_accreditation_bodies_include_anab(self):
        """Test that ANAB is included."""
        response = client.get("/federal/accreditation-bodies")
        abs = response.json()

        ab_names = [ab["name"] for ab in abs]
        assert any("ANAB" in name for name in ab_names)


class TestCertificationBodiesEndpoint:
    """Tests for certification bodies endpoints."""

    def test_list_certification_bodies(self):
        """Test listing all certification bodies."""
        response = client.get("/federal/certification-bodies")
        assert response.status_code == 200

        cbs = response.json()
        assert isinstance(cbs, list)
        assert len(cbs) > 0

        # Check structure
        cb = cbs[0]
        assert "id" in cb
        assert "name" in cb

    def test_filter_certification_bodies_by_scope(self):
        """Test filtering certification bodies by scope."""
        response = client.get("/federal/certification-bodies?scope=Human%20Food")
        assert response.status_code == 200

        cbs = response.json()
        assert isinstance(cbs, list)
        assert len(cbs) > 0


class TestCertifiersEndpoint:
    """Tests for certifiers endpoints."""

    def test_list_certifiers(self):
        """Test listing all certifiers."""
        response = client.get("/federal/certifiers")
        assert response.status_code == 200

        certifiers = response.json()
        assert isinstance(certifiers, list)
        assert len(certifiers) > 0

        # Check structure
        certifier = certifiers[0]
        assert "certifier_id" in certifier
        assert "certifier_name" in certifier
        assert "accreditor_name" in certifier
        assert "scope_name" in certifier
        assert "scope_status" in certifier

    def test_filter_certifiers_by_scope(self):
        """Test filtering certifiers by scope."""
        response = client.get("/federal/certifiers?scope=Produce")
        assert response.status_code == 200

        certifiers = response.json()
        assert isinstance(certifiers, list)

        # All certifiers should have Produce in scope name
        for certifier in certifiers:
            assert "Produce" in certifier["scope_name"]

    def test_filter_active_certifiers(self):
        """Test filtering only active certifiers."""
        response = client.get("/federal/certifiers?active_only=true")
        assert response.status_code == 200

        certifiers = response.json()
        for certifier in certifiers:
            assert certifier["scope_status"] == "active"

    def test_get_specific_certifier(self):
        """Test getting details for a specific certifier."""
        # First get list to find a valid ID
        list_response = client.get("/federal/certification-bodies")
        cbs = list_response.json()

        if len(cbs) > 0:
            certifier_id = cbs[0]["id"]

            response = client.get(f"/federal/certifiers/{certifier_id}")
            assert response.status_code == 200

            certifier = response.json()
            assert certifier["id"] == certifier_id
            assert "name" in certifier
            assert "scopes" in certifier
            assert isinstance(certifier["scopes"], list)

    def test_get_nonexistent_certifier(self):
        """Test getting a non-existent certifier returns 404."""
        response = client.get("/federal/certifiers/99999")
        assert response.status_code == 404


class TestExpiringEndpoint:
    """Tests for expiring certifications endpoint."""

    def test_get_expiring_certifications(self):
        """Test getting expiring certifications."""
        response = client.get("/federal/expiring?days=365")
        assert response.status_code == 200

        expirations = response.json()
        assert isinstance(expirations, list)

        if len(expirations) > 0:
            expiration = expirations[0]
            assert "accreditor" in expiration
            assert "certifier" in expiration
            assert "scope" in expiration
            assert "expiration_date" in expiration
            assert "days_until_expiry" in expiration
            assert "priority" in expiration

    def test_expiring_with_custom_days(self):
        """Test expiring with custom day range."""
        response = client.get("/federal/expiring?days=90")
        assert response.status_code == 200

        expirations = response.json()
        assert isinstance(expirations, list)

    def test_expiring_invalid_days(self):
        """Test expiring with invalid days parameter."""
        response = client.get("/federal/expiring?days=0")
        assert response.status_code == 422  # Validation error


class TestAuthorityChainEndpoint:
    """Tests for authority chain endpoint."""

    def test_get_authority_chain(self):
        """Test getting authority chain for valid certifier and scope."""
        response = client.get(
            "/federal/authority-chain", params={"certifier_name": "NSF", "scope_name": "Human Food"}
        )

        if response.status_code == 200:
            chain = response.json()
            assert chain["federal_authority"] == "FDA"
            assert "accreditation_body" in chain
            assert "certification_body" in chain
            assert "scope" in chain
            assert "chain_validity" in chain
            assert chain["chain_validity"] in ["VALID", "INVALID"]

    def test_authority_chain_not_found(self):
        """Test authority chain with non-existent combination."""
        response = client.get(
            "/federal/authority-chain",
            params={"certifier_name": "NonExistentCertifier", "scope_name": "NonExistentScope"},
        )
        assert response.status_code == 404


class TestMatchEndpoint:
    """Tests for match endpoint."""

    def test_match_pchf_activity(self):
        """Test matching for PCHF activity."""
        response = client.post(
            "/federal/match",
            json={"activity": "preventive_controls_human_food", "jurisdiction": "CA-Los Angeles"},
        )
        assert response.status_code == 200

        match = response.json()
        assert match["activity"] == "preventive_controls_human_food"
        assert match["jurisdiction"] == "CA-Los Angeles"
        assert "matched_scopes" in match
        assert len(match["matched_scopes"]) > 0
        assert "certifiers" in match
        assert "cfr_references" in match

    def test_match_seafood_activity(self):
        """Test matching for seafood HACCP activity."""
        response = client.post("/federal/match", json={"activity": "seafood_haccp"})
        assert response.status_code == 200

        match = response.json()
        assert "matched_scopes" in match

        # Should match seafood scope
        scope_names = [s["name"] for s in match["matched_scopes"]]
        assert any("Seafood" in name for name in scope_names)

    def test_match_produce_activity(self):
        """Test matching for produce safety."""
        response = client.post("/federal/match", json={"activity": "produce_safety"})
        assert response.status_code == 200

        match = response.json()
        scope_names = [s["name"] for s in match["matched_scopes"]]
        assert any("Produce" in name for name in scope_names)

    def test_match_unknown_activity(self):
        """Test matching with unknown activity type."""
        response = client.post("/federal/match", json={"activity": "totally_unknown_activity"})
        assert response.status_code == 400

    def test_match_missing_activity(self):
        """Test match endpoint without required activity field."""
        response = client.post("/federal/match", json={})
        assert response.status_code == 422  # Validation error


class TestDataIntegrity:
    """Tests for data integrity and relationships."""

    def test_all_certifiers_have_valid_accreditors(self):
        """Test that all certifiers reference valid accreditation bodies."""
        certifiers_response = client.get("/federal/certifiers")
        certifiers = certifiers_response.json()

        abs_response = client.get("/federal/accreditation-bodies")
        abs = abs_response.json()
        ab_names = {ab["name"] for ab in abs}

        for certifier in certifiers:
            assert certifier["accreditor_name"] in ab_names

    def test_all_certifiers_have_valid_scopes(self):
        """Test that all certifiers reference valid scopes."""
        certifiers_response = client.get("/federal/certifiers")
        certifiers = certifiers_response.json()

        scopes_response = client.get("/federal/scopes")
        scopes = scopes_response.json()
        scope_names = {s["name"] for s in scopes}

        for certifier in certifiers:
            assert certifier["scope_name"] in scope_names

    def test_scopes_have_cfr_citations(self):
        """Test that scopes include CFR citations."""
        response = client.get("/federal/scopes")
        scopes = response.json()

        cfr_pattern_found = False
        for scope in scopes:
            if scope.get("cfr_title_part_section"):
                cfr_pattern_found = True
                # Basic validation - should contain "CFR"
                assert "CFR" in scope["cfr_title_part_section"]

        assert cfr_pattern_found, "At least one scope should have CFR citation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
