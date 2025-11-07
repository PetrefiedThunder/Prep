"""
Smoke tests for Prep platform health checks.

Tests service availability, database connectivity, and storage layer.
Run after `make up && make migrate` to verify the stack is operational.
"""

import os
from typing import Any

import asyncpg
import boto3
import pytest
import requests
from botocore.client import Config


# Service endpoints
PYTHON_API_BASE = "http://localhost:8000"
NODE_API_BASE = "http://localhost:3000"
MINIO_ENDPOINT = "http://localhost:9000"

# Database config
DB_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/prepchef"
)

# MinIO config
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")


class TestServiceHealth:
    """Test health endpoints for all FastAPI services."""

    def test_python_api_healthz(self):
        """Python compliance API should respond to /healthz."""
        response = requests.get(f"{PYTHON_API_BASE}/healthz", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        # Common health response patterns
        assert data.get("status") in ["ok", "healthy", "up"]

    def test_python_api_health_alternate(self):
        """Python compliance API should respond to /health (alternate endpoint)."""
        response = requests.get(f"{PYTHON_API_BASE}/health", timeout=5)
        # Accept 200 or 404 (if endpoint doesn't exist, that's okay)
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "status" in data

    def test_python_api_openapi(self):
        """Python compliance API should serve OpenAPI spec."""
        response = requests.get(f"{PYTHON_API_BASE}/openapi.json", timeout=5)
        assert response.status_code == 200
        openapi_spec = response.json()
        assert "openapi" in openapi_spec
        assert "info" in openapi_spec
        assert "paths" in openapi_spec

    def test_node_api_reachable(self):
        """Node API should be reachable on port 3000."""
        try:
            response = requests.get(NODE_API_BASE, timeout=5)
            # Accept any non-5xx response (may redirect, may return 404, etc.)
            assert response.status_code < 500
        except requests.exceptions.ConnectionError:
            pytest.skip("Node API not running (optional for Python-only setup)")


class TestDatabaseConnectivity:
    """Test PostgreSQL database connectivity and schema."""

    @pytest.mark.asyncio
    async def test_database_connection(self):
        """Database should accept connections."""
        # Parse DATABASE_URL to get connection params
        # Format: postgresql://user:pass@host:port/dbname
        if DB_URL.startswith("postgresql://"):
            db_url = DB_URL.replace("postgresql://", "")
        elif DB_URL.startswith("postgresql+asyncpg://"):
            db_url = DB_URL.replace("postgresql+asyncpg://", "")
        else:
            db_url = DB_URL

        # Extract components
        if "@" in db_url:
            auth, rest = db_url.split("@", 1)
            user, password = auth.split(":", 1) if ":" in auth else (auth, "")
            host_port, database = rest.split("/", 1)
            host, port = (
                host_port.split(":", 1) if ":" in host_port else (host_port, "5432")
            )
        else:
            # Fallback defaults
            user, password, host, port, database = (
                "postgres",
                "postgres",
                "localhost",
                "5432",
                "prepchef",
            )

        conn = await asyncpg.connect(
            user=user, password=password, database=database, host=host, port=int(port)
        )
        try:
            # Simple connectivity test
            result = await conn.fetchval("SELECT 1")
            assert result == 1
        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_core_tables_exist(self):
        """Core database tables should exist after migrations."""
        # Parse DB_URL
        if DB_URL.startswith("postgresql://"):
            db_url = DB_URL.replace("postgresql://", "")
        elif DB_URL.startswith("postgresql+asyncpg://"):
            db_url = DB_URL.replace("postgresql+asyncpg://", "")
        else:
            db_url = DB_URL

        if "@" in db_url:
            auth, rest = db_url.split("@", 1)
            user, password = auth.split(":", 1) if ":" in auth else (auth, "")
            host_port, database = rest.split("/", 1)
            host, port = (
                host_port.split(":", 1) if ":" in host_port else (host_port, "5432")
            )
        else:
            user, password, host, port, database = (
                "postgres",
                "postgres",
                "localhost",
                "5432",
                "prepchef",
            )

        conn = await asyncpg.connect(
            user=user, password=password, database=database, host=host, port=int(port)
        )
        try:
            # Core tables from init.sql
            core_tables = ["users", "kitchens", "bookings", "reviews", "compliance_documents"]

            for table_name in core_tables:
                # Check table exists and is queryable
                result = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {table_name}"  # noqa: S608
                )
                assert result is not None
                # Don't assert count > 0 as tables may be empty initially
                assert result >= 0

        finally:
            await conn.close()


class TestMinIOStorage:
    """Test MinIO object storage connectivity."""

    def test_minio_health(self):
        """MinIO should respond to health check endpoint."""
        response = requests.get(f"{MINIO_ENDPOINT}/minio/health/live", timeout=5)
        assert response.status_code == 200

    def test_minio_read_write(self):
        """MinIO should allow write and read operations."""
        # Configure boto3 client for MinIO
        s3_client = boto3.client(
            "s3",
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

        bucket_name = "smoke-test-bucket"
        test_key = "smoke-test/test-object.txt"
        test_content = b"Prep platform smoke test content"

        try:
            # Create bucket if it doesn't exist
            try:
                s3_client.head_bucket(Bucket=bucket_name)
            except Exception:
                s3_client.create_bucket(Bucket=bucket_name)

            # Write test object
            s3_client.put_object(Bucket=bucket_name, Key=test_key, Body=test_content)

            # Read test object
            response = s3_client.get_object(Bucket=bucket_name, Key=test_key)
            retrieved_content = response["Body"].read()

            assert retrieved_content == test_content

        finally:
            # Cleanup
            try:
                s3_client.delete_object(Bucket=bucket_name, Key=test_key)
                # Try to delete bucket (will fail if not empty, that's okay)
                s3_client.delete_bucket(Bucket=bucket_name)
            except Exception:
                pass  # Best effort cleanup


class TestIntegrationReadiness:
    """Test that the full stack is ready for integration testing."""

    def test_all_critical_services_up(self):
        """All critical services should be reachable."""
        services_status = {}

        # Check Python API
        try:
            response = requests.get(f"{PYTHON_API_BASE}/healthz", timeout=5)
            services_status["python_api"] = response.status_code == 200
        except Exception:
            services_status["python_api"] = False

        # Check MinIO
        try:
            response = requests.get(f"{MINIO_ENDPOINT}/minio/health/live", timeout=5)
            services_status["minio"] = response.status_code == 200
        except Exception:
            services_status["minio"] = False

        # Require at minimum Python API and MinIO
        assert services_status["python_api"], "Python API must be healthy"
        assert services_status["minio"], "MinIO must be healthy"

        # Print status for debugging
        print("\nService Status:")
        for service, status in services_status.items():
            status_str = "✓" if status else "✗"
            print(f"  {status_str} {service}")
