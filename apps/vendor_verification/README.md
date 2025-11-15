# Vendor Verification Service

A FastAPI microservice for onboarding and verifying vendors for shared/commercial kitchens.

## Product Promise

We help kitchen operators onboard and verify vendors faster with structured checks. We do **NOT** guarantee full legal compliance.

## Features

- **Vendor Management**: Create and manage vendor profiles with location and contact information
- **Document Management**: Upload and track vendor documents (business licenses, food handler cards, insurance)
- **Automated Verification**: Run verification checks based on jurisdiction-specific rules
- **Multi-Tenancy**: Complete tenant isolation with API key authentication
- **Audit Trail**: Track all vendor and verification events

## Architecture

### Components

- **FastAPI Service** (`apps/vendor_verification/`)
  - REST API for vendor management and verification
  - Pydantic models for request/response validation
  - SQLAlchemy ORM for database access
  - Simple RegEngine adapter for verification logic

- **Database** (PostgreSQL)
  - `tenants` - API key holders
  - `vendors` - Vendor profiles
  - `vendor_documents` - Document metadata with S3/MinIO storage
  - `verification_runs` - Verification history and results
  - `audit_events` - Audit trail

- **Operator UI** (Next.js in `apps/harborhomes/`)
  - `/operator/vendors` - Vendor list
  - `/operator/vendors/[id]` - Vendor details and document management
  - `/operator/verifications/[id]` - Verification results

## API Overview

See [OpenAPI Specification](../../openapi/vendor_verification_v1.yaml) for full details.

### Authentication

All endpoints require an API key header:
```
X-Prep-Api-Key: your-api-key-here
```

### Core Endpoints

- `POST /api/v1/vendors` - Create/update vendor (idempotent)
- `GET /api/v1/vendors` - List vendors
- `GET /api/v1/vendors/{id}` - Get vendor details
- `POST /api/v1/vendors/{id}/documents` - Upload document (returns presigned URL)
- `GET /api/v1/vendors/{id}/documents` - List vendor documents
- `POST /api/v1/vendors/{id}/verifications` - Run verification
- `GET /api/v1/vendors/{id}/verifications/{id}` - Get verification results

## Running the Service

### Prerequisites

- Python 3.10+
- PostgreSQL
- MinIO or S3 (for document storage)

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export DATABASE_URL="postgresql://user:pass@localhost/prep"
export VENDOR_DOCS_BUCKET="prep-vendor-documents"
export MINIO_ENDPOINT="http://localhost:9000"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
```

3. Run database migrations:
```bash
alembic upgrade head
```

4. Start the service:
```bash
python -m apps.vendor_verification.main
```

The service will be available at `http://localhost:8003`.

## Verification Logic (v1)

For v1, implements simple San Francisco shared kitchen rules:

**Required Documents:**
- Business License
- Food Handler Card
- Liability Insurance

**Checks:**
- All required documents must be present
- All documents must match the target jurisdiction
- No documents should be expired

**Decision:**
- `pass` - All checks passed
- `fail` - One or more checks failed

**Scoring:**
- Pass: score = 0.97
- Fail: score reduces by ~0.34 per failed check

## Testing

Run tests with pytest:

```bash
pytest apps/vendor_verification/tests/
```

### Test Coverage

- **Tenant Isolation**: Ensures vendors/verifications cannot be accessed across tenants
- **Happy Path**: Complete flow with valid documents → `passed` status
- **Failure Path**: Missing or expired documents → `failed` status with details
- **API Basics**: Auth, health check, idempotency

## Future Enhancements

- [ ] Multiple jurisdiction support (currently SF only)
- [ ] Dynamic ruleset loading
- [ ] Webhook callbacks for verification completion
- [ ] Document expiration notifications
- [ ] Advanced verification scoring
- [ ] Real presigned URL generation (currently mock)
- [ ] Document verification (OCR, validation)

## API Client Generation

Generate API clients from the OpenAPI spec:

```bash
openapi-generator-cli generate \
  -i openapi/vendor_verification_v1.yaml \
  -g python \
  -o generated/vendor-verification-client
```
