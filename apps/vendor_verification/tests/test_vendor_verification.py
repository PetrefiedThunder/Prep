"""
Integration tests for Vendor Verification API.

Tests cover:
1. Tenant isolation - ensures vendors/verifications are isolated per tenant
2. Happy path - vendor creation, document upload, and successful verification
3. Failure path - verification with missing/expired documents
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.vendor_verification.auth import hash_api_key
from apps.vendor_verification.main import app, get_db
from apps.vendor_verification.orm_models import (
    Base,
    Tenant,
)

# Create in-memory SQLite database for testing
# Use StaticPool to ensure all connections share the same in-memory database
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Create tables
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def tenant_a(db_session):
    """Create tenant A for testing."""
    api_key = "test-api-key-tenant-a"
    tenant = Tenant(
        id=uuid4(),
        name="Tenant A",
        api_key_hash=hash_api_key(api_key),
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return {"tenant": tenant, "api_key": api_key}


@pytest.fixture
def tenant_b(db_session):
    """Create tenant B for testing."""
    api_key = "test-api-key-tenant-b"
    tenant = Tenant(
        id=uuid4(),
        name="Tenant B",
        api_key_hash=hash_api_key(api_key),
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return {"tenant": tenant, "api_key": api_key}


class TestTenantIsolation:
    """Test that tenant data is properly isolated."""

    def test_vendor_isolation(self, client, tenant_a, tenant_b, db_session):
        """
        Test that vendors from tenant A cannot be accessed by tenant B.

        Creates a vendor under tenant A, then attempts to access it
        with tenant B's API key. Should return 404.
        """
        # Create vendor under tenant A
        vendor_data = {
            "external_id": "vendor-123",
            "legal_name": "Test Vendor LLC",
            "primary_location": {"country": "US", "state": "CA", "city": "San Francisco"},
        }

        response = client.post(
            "/api/v1/vendors",
            json=vendor_data,
            headers={"X-Prep-Api-Key": tenant_a["api_key"]},
        )
        assert response.status_code == 200
        vendor = response.json()
        vendor_id = vendor["vendor_id"]

        # Attempt to access vendor with tenant B's API key
        response = client.get(
            f"/api/v1/vendors/{vendor_id}",
            headers={"X-Prep-Api-Key": tenant_b["api_key"]},
        )
        assert response.status_code == 404
        error = response.json()
        assert error["detail"]["code"] == "vendor_not_found"

    def test_verification_isolation(self, client, tenant_a, tenant_b, db_session):
        """
        Test that verifications from tenant A cannot be accessed by tenant B.
        """
        # Create vendor and verification under tenant A
        vendor_data = {
            "external_id": "vendor-456",
            "legal_name": "Another Vendor LLC",
            "primary_location": {"country": "US", "state": "CA", "city": "San Francisco"},
        }

        response = client.post(
            "/api/v1/vendors",
            json=vendor_data,
            headers={"X-Prep-Api-Key": tenant_a["api_key"]},
        )
        vendor = response.json()
        vendor_id = vendor["vendor_id"]

        # Create verification
        verification_data = {
            "jurisdiction": {"country": "US", "state": "CA", "city": "San Francisco"},
            "purpose": "shared_kitchen_rental",
        }

        response = client.post(
            f"/api/v1/vendors/{vendor_id}/verifications",
            json=verification_data,
            headers={"X-Prep-Api-Key": tenant_a["api_key"]},
        )
        assert response.status_code == 200
        verification = response.json()
        verification_id = verification["verification_id"]

        # Attempt to access verification with tenant B's API key
        response = client.get(
            f"/api/v1/vendors/{vendor_id}/verifications/{verification_id}",
            headers={"X-Prep-Api-Key": tenant_b["api_key"]},
        )
        assert response.status_code == 404


class TestHappyPath:
    """Test successful vendor verification flow."""

    def test_complete_verification_flow(self, client, tenant_a, db_session):
        """
        Test complete happy path:
        1. Create vendor
        2. Upload required documents (business license, food handler card, liability insurance)
        3. Run verification
        4. Verify status is 'passed'
        """
        # Step 1: Create vendor
        vendor_data = {
            "external_id": "happy-vendor-001",
            "legal_name": "Happy Catering LLC",
            "doing_business_as": "Happy Catering",
            "primary_location": {"country": "US", "state": "CA", "city": "San Francisco"},
            "contact": {"email": "contact@happycatering.com", "phone": "+1-415-555-0100"},
        }

        response = client.post(
            "/api/v1/vendors",
            json=vendor_data,
            headers={"X-Prep-Api-Key": tenant_a["api_key"]},
        )
        assert response.status_code == 200
        vendor = response.json()
        vendor_id = vendor["vendor_id"]
        assert vendor["status"] == "onboarding"
        assert vendor["legal_name"] == "Happy Catering LLC"

        # Step 2: Upload required documents (all valid, not expired)
        jurisdiction = {"country": "US", "state": "CA", "city": "San Francisco"}
        future_date = (datetime.now(UTC) + timedelta(days=365)).date().isoformat()

        required_docs = [
            {
                "type": "business_license",
                "jurisdiction": jurisdiction,
                "file_name": "business_license.pdf",
                "content_type": "application/pdf",
                "expires_on": future_date,
            },
            {
                "type": "food_handler_card",
                "jurisdiction": jurisdiction,
                "file_name": "food_handler.pdf",
                "content_type": "application/pdf",
                "expires_on": future_date,
            },
            {
                "type": "liability_insurance",
                "jurisdiction": jurisdiction,
                "file_name": "insurance.pdf",
                "content_type": "application/pdf",
                "expires_on": future_date,
            },
        ]

        for doc_data in required_docs:
            response = client.post(
                f"/api/v1/vendors/{vendor_id}/documents",
                json=doc_data,
                headers={"X-Prep-Api-Key": tenant_a["api_key"]},
            )
            assert response.status_code == 200
            doc_response = response.json()
            assert "document_id" in doc_response
            assert "upload_url" in doc_response

        # Step 3: Run verification
        verification_data = {
            "jurisdiction": jurisdiction,
            "purpose": "shared_kitchen_rental",
            "requested_by": "operator-123",
        }

        response = client.post(
            f"/api/v1/vendors/{vendor_id}/verifications",
            json=verification_data,
            headers={"X-Prep-Api-Key": tenant_a["api_key"]},
        )
        assert response.status_code == 200
        verification = response.json()
        verification_id = verification["verification_id"]
        assert verification["status"] == "passed"

        # Step 4: Get verification details
        response = client.get(
            f"/api/v1/vendors/{vendor_id}/verifications/{verification_id}",
            headers={"X-Prep-Api-Key": tenant_a["api_key"]},
        )
        assert response.status_code == 200
        detail = response.json()

        assert detail["status"] == "passed"
        assert detail["decision"]["overall"] == "pass"
        assert detail["decision"]["score"] > 0.9
        assert len(detail["decision"]["check_results"]) > 0

        # All checks should pass
        for check in detail["decision"]["check_results"]:
            assert check["status"] == "pass"

        # Verify recommendation
        assert "approved" in detail["recommendation"]["summary"].lower()


class TestFailurePath:
    """Test verification with missing or expired documents."""

    def test_verification_with_missing_document(self, client, tenant_a, db_session):
        """
        Test verification fails when required document is missing.

        Creates vendor with only 2 of 3 required documents, then runs
        verification. Should get 'failed' status with appropriate check results.
        """
        # Create vendor
        vendor_data = {
            "external_id": "missing-doc-vendor",
            "legal_name": "Incomplete Vendor LLC",
            "primary_location": {"country": "US", "state": "CA", "city": "San Francisco"},
        }

        response = client.post(
            "/api/v1/vendors",
            json=vendor_data,
            headers={"X-Prep-Api-Key": tenant_a["api_key"]},
        )
        vendor_id = response.json()["vendor_id"]

        # Upload only 2 documents (missing liability insurance)
        jurisdiction = {"country": "US", "state": "CA", "city": "San Francisco"}
        future_date = (datetime.now(UTC) + timedelta(days=365)).date().isoformat()

        docs = [
            {
                "type": "business_license",
                "jurisdiction": jurisdiction,
                "file_name": "business_license.pdf",
                "content_type": "application/pdf",
                "expires_on": future_date,
            },
            {
                "type": "food_handler_card",
                "jurisdiction": jurisdiction,
                "file_name": "food_handler.pdf",
                "content_type": "application/pdf",
                "expires_on": future_date,
            },
            # Missing: liability_insurance
        ]

        for doc_data in docs:
            client.post(
                f"/api/v1/vendors/{vendor_id}/documents",
                json=doc_data,
                headers={"X-Prep-Api-Key": tenant_a["api_key"]},
            )

        # Run verification
        verification_data = {
            "jurisdiction": jurisdiction,
            "purpose": "shared_kitchen_rental",
        }

        response = client.post(
            f"/api/v1/vendors/{vendor_id}/verifications",
            json=verification_data,
            headers={"X-Prep-Api-Key": tenant_a["api_key"]},
        )
        assert response.status_code == 200
        verification = response.json()
        assert verification["status"] == "failed"

        # Get verification details
        verification_id = verification["verification_id"]
        response = client.get(
            f"/api/v1/vendors/{vendor_id}/verifications/{verification_id}",
            headers={"X-Prep-Api-Key": tenant_a["api_key"]},
        )
        detail = response.json()

        assert detail["decision"]["overall"] == "fail"
        assert detail["decision"]["score"] < 1.0

        # Find the failed check for liability insurance
        failed_checks = [
            check for check in detail["decision"]["check_results"] if check["status"] == "fail"
        ]
        assert len(failed_checks) > 0

        # At least one check should be for liability insurance
        insurance_checks = [
            check for check in failed_checks if "liability_insurance" in check["code"]
        ]
        assert len(insurance_checks) > 0

    def test_verification_with_expired_document(self, client, tenant_a, db_session):
        """
        Test verification fails when required document is expired.
        """
        # Create vendor
        vendor_data = {
            "external_id": "expired-doc-vendor",
            "legal_name": "Expired Vendor LLC",
            "primary_location": {"country": "US", "state": "CA", "city": "San Francisco"},
        }

        response = client.post(
            "/api/v1/vendors",
            json=vendor_data,
            headers={"X-Prep-Api-Key": tenant_a["api_key"]},
        )
        vendor_id = response.json()["vendor_id"]

        # Upload documents with one expired
        jurisdiction = {"country": "US", "state": "CA", "city": "San Francisco"}
        future_date = (datetime.now(UTC) + timedelta(days=365)).date().isoformat()
        past_date = (datetime.now(UTC) - timedelta(days=30)).date().isoformat()

        docs = [
            {
                "type": "business_license",
                "jurisdiction": jurisdiction,
                "file_name": "business_license.pdf",
                "content_type": "application/pdf",
                "expires_on": future_date,
            },
            {
                "type": "food_handler_card",
                "jurisdiction": jurisdiction,
                "file_name": "food_handler.pdf",
                "content_type": "application/pdf",
                "expires_on": past_date,  # EXPIRED
            },
            {
                "type": "liability_insurance",
                "jurisdiction": jurisdiction,
                "file_name": "insurance.pdf",
                "content_type": "application/pdf",
                "expires_on": future_date,
            },
        ]

        for doc_data in docs:
            client.post(
                f"/api/v1/vendors/{vendor_id}/documents",
                json=doc_data,
                headers={"X-Prep-Api-Key": tenant_a["api_key"]},
            )

        # Run verification
        verification_data = {
            "jurisdiction": jurisdiction,
            "purpose": "shared_kitchen_rental",
        }

        response = client.post(
            f"/api/v1/vendors/{vendor_id}/verifications",
            json=verification_data,
            headers={"X-Prep-Api-Key": tenant_a["api_key"]},
        )
        verification = response.json()
        assert verification["status"] == "failed"

        # Get verification details
        verification_id = verification["verification_id"]
        response = client.get(
            f"/api/v1/vendors/{vendor_id}/verifications/{verification_id}",
            headers={"X-Prep-Api-Key": tenant_a["api_key"]},
        )
        detail = response.json()

        assert detail["decision"]["overall"] == "fail"

        # Should have a failed check for food handler card
        failed_checks = [
            check for check in detail["decision"]["check_results"] if check["status"] == "fail"
        ]
        food_handler_checks = [check for check in failed_checks if "food_handler" in check["code"]]
        assert len(food_handler_checks) > 0
        assert "expired" in food_handler_checks[0]["details"].lower()


class TestAPIBasics:
    """Test basic API functionality."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "degraded"]
        assert "version" in data

    def test_unauthorized_access(self, client):
        """Test that requests without API key are rejected."""
        response = client.get("/api/v1/vendors")
        assert response.status_code in [401, 422]  # 422 for missing required header

    def test_invalid_api_key(self, client):
        """Test that requests with invalid API key are rejected."""
        response = client.get("/api/v1/vendors", headers={"X-Prep-Api-Key": "invalid-key"})
        assert response.status_code == 401

    def test_vendor_upsert_idempotency(self, client, tenant_a):
        """Test that vendor creation is idempotent on external_id."""
        vendor_data = {
            "external_id": "idempotent-vendor",
            "legal_name": "Original Name",
            "primary_location": {"country": "US"},
        }

        # Create vendor
        response1 = client.post(
            "/api/v1/vendors",
            json=vendor_data,
            headers={"X-Prep-Api-Key": tenant_a["api_key"]},
        )
        assert response1.status_code == 200
        vendor1 = response1.json()

        # Update with same external_id
        vendor_data["legal_name"] = "Updated Name"
        response2 = client.post(
            "/api/v1/vendors",
            json=vendor_data,
            headers={"X-Prep-Api-Key": tenant_a["api_key"]},
        )
        assert response2.status_code == 200
        vendor2 = response2.json()

        # Should be same vendor ID
        assert vendor1["vendor_id"] == vendor2["vendor_id"]
        assert vendor2["legal_name"] == "Updated Name"

    def test_verification_idempotency(self, client, tenant_a, db_session):
        """Test that verification with idempotency key doesn't create duplicates."""
        # Create vendor
        vendor_data = {
            "external_id": "idempotent-verify-vendor",
            "legal_name": "Test Vendor",
            "primary_location": {"country": "US", "state": "CA", "city": "San Francisco"},
        }
        response = client.post(
            "/api/v1/vendors",
            json=vendor_data,
            headers={"X-Prep-Api-Key": tenant_a["api_key"]},
        )
        vendor_id = response.json()["vendor_id"]

        # Create verification with idempotency key
        verification_data = {
            "jurisdiction": {"country": "US", "state": "CA", "city": "San Francisco"},
            "purpose": "shared_kitchen_rental",
        }

        idempotency_key = "test-idempotency-key-123"

        response1 = client.post(
            f"/api/v1/vendors/{vendor_id}/verifications",
            json=verification_data,
            headers={
                "X-Prep-Api-Key": tenant_a["api_key"],
                "Idempotency-Key": idempotency_key,
            },
        )
        assert response1.status_code == 200
        verification1 = response1.json()

        # Repeat with same idempotency key
        response2 = client.post(
            f"/api/v1/vendors/{vendor_id}/verifications",
            json=verification_data,
            headers={
                "X-Prep-Api-Key": tenant_a["api_key"],
                "Idempotency-Key": idempotency_key,
            },
        )
        assert response2.status_code == 200
        verification2 = response2.json()

        # Should return the same verification
        assert verification1["verification_id"] == verification2["verification_id"]
