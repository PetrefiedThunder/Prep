"""
Vendor Verification Service

FastAPI microservice for onboarding and verifying vendors for shared/commercial kitchens.
"""

from __future__ import annotations

import hashlib
import logging
import os
from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Header, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from apps.vendor_verification.auth import get_current_tenant, hash_api_key
from apps.vendor_verification.models import (
    ContactInfo,
    DocumentListResponse,
    DocumentRequest,
    DocumentResponse,
    DocumentUploadResponse,
    ErrorResponse,
    InitiatedFrom,
    Location,
    VendorListResponse,
    VendorRequest,
    VendorResponse,
    VendorStatus,
    VerificationDetail,
    VerificationRequest,
    VerificationResponse,
    VerificationStatus,
)
from apps.vendor_verification.orm_models import (
    AuditEvent,
    Tenant,
    Vendor,
    VendorDocument,
    VerificationRun,
)
from apps.vendor_verification.reg_adapter import get_ruleset_metadata, run_verification
from prep.models.db import SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Prep Vendor Verification Service",
    description="Vendor verification for shared/commercial kitchens",
    version="1.0.0",
)


# ============================================================================
# Database Connection Management
# ============================================================================


def get_db() -> Generator[Session, None, None]:
    """Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Helper Functions
# ============================================================================


def get_storage_config() -> dict[str, str]:
    """Get MinIO/S3 storage configuration."""
    return {
        "bucket": os.getenv("VENDOR_DOCS_BUCKET", "prep-vendor-documents"),
        "endpoint": os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        "access_key": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        "secret_key": os.getenv("MINIO_SECRET_KEY", "minioadmin"),
    }


def generate_presigned_upload_url(storage_key: str, content_type: str, expires_in: int = 3600) -> str:
    """
    Generate a presigned URL for uploading a document.

    For v1, returns a placeholder URL. In production, this would use boto3
    to generate a real presigned URL for MinIO/S3.

    Args:
        storage_key: The storage key for the object
        content_type: MIME type of the file
        expires_in: URL expiration time in seconds

    Returns:
        Presigned upload URL
    """
    config = get_storage_config()

    # In production, use boto3:
    # import boto3
    # s3_client = boto3.client(
    #     's3',
    #     endpoint_url=config['endpoint'],
    #     aws_access_key_id=config['access_key'],
    #     aws_secret_access_key=config['secret_key'],
    # )
    # url = s3_client.generate_presigned_url(
    #     'put_object',
    #     Params={'Bucket': config['bucket'], 'Key': storage_key, 'ContentType': content_type},
    #     ExpiresIn=expires_in,
    # )

    # For v1, return a mock presigned URL
    return f"{config['endpoint']}/{config['bucket']}/{storage_key}?signature=mock&expires={expires_in}"


def create_audit_event(
    db: Session,
    tenant_id: UUID,
    actor_type: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict | None = None,
    actor_id: str | None = None,
) -> None:
    """Create an audit event."""
    event = AuditEvent(
        tenant_id=tenant_id,
        actor_type=actor_type,
        actor_id=actor_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=str(entity_id),
        payload=payload or {},
    )
    db.add(event)


# ============================================================================
# Dependency Wrappers for Auth
# ============================================================================


async def get_tenant_dependency(
    api_key: str = Header(..., alias="X-Prep-Api-Key"),
    db: Session = Depends(get_db),
) -> Tenant:
    """Get current tenant from API key."""
    api_key_hash = hash_api_key(api_key)
    tenant = db.query(Tenant).filter(Tenant.api_key_hash == api_key_hash).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                code="unauthorized",
                message="Invalid or missing API key",
            ).model_dump(),
        )

    return tenant


# ============================================================================
# Health Check
# ============================================================================


@app.get("/healthz")
async def health_check(db: Session = Depends(get_db)) -> dict:
    """Health check endpoint."""
    try:
        db.execute(func.now())
        database_connected = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        database_connected = False

    return {
        "status": "ok" if database_connected else "degraded",
        "version": "1.0.0",
        "database_connected": database_connected,
    }


# ============================================================================
# Vendor Endpoints
# ============================================================================


@app.post("/api/v1/vendors", response_model=VendorResponse)
async def create_or_update_vendor(
    request: VendorRequest,
    tenant: Tenant = Depends(get_tenant_dependency),
    db: Session = Depends(get_db),
) -> VendorResponse:
    """
    Create or update a vendor (idempotent upsert).

    Always returns 200, never 409.
    """
    # Check if vendor exists
    existing_vendor = (
        db.query(Vendor)
        .filter(
            Vendor.tenant_id == tenant.id,
            Vendor.external_id == request.external_id,
        )
        .first()
    )

    now = datetime.now(UTC)

    if existing_vendor:
        # Update existing vendor
        existing_vendor.legal_name = request.legal_name
        existing_vendor.doing_business_as = request.doing_business_as
        existing_vendor.primary_location = request.primary_location.model_dump()
        existing_vendor.contact = request.contact.model_dump() if request.contact else None
        existing_vendor.tax_id_last4 = request.tax_id_last4
        existing_vendor.updated_at = now

        db.commit()
        db.refresh(existing_vendor)

        # Audit event
        create_audit_event(
            db=db,
            tenant_id=tenant.id,
            actor_type="api",
            event_type="vendor_updated",
            entity_type="vendor",
            entity_id=str(existing_vendor.id),
            payload={"external_id": request.external_id},
        )
        db.commit()

        vendor = existing_vendor
        event_type = "updated"
    else:
        # Create new vendor
        vendor = Vendor(
            tenant_id=tenant.id,
            external_id=request.external_id,
            legal_name=request.legal_name,
            doing_business_as=request.doing_business_as,
            status=VendorStatus.ONBOARDING.value,
            primary_location=request.primary_location.model_dump(),
            contact=request.contact.model_dump() if request.contact else None,
            tax_id_last4=request.tax_id_last4,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        # Audit event
        create_audit_event(
            db=db,
            tenant_id=tenant.id,
            actor_type="api",
            event_type="vendor_created",
            entity_type="vendor",
            entity_id=str(vendor.id),
            payload={"external_id": request.external_id},
        )
        db.commit()

        event_type = "created"

    logger.info(f"Vendor {event_type}: {vendor.id} (external_id={request.external_id})")

    # Convert to response
    return VendorResponse(
        vendor_id=vendor.id,
        external_id=vendor.external_id,
        legal_name=vendor.legal_name,
        doing_business_as=vendor.doing_business_as,
        status=VendorStatus(vendor.status),
        primary_location=Location(**vendor.primary_location),
        contact=None if vendor.contact is None else ContactInfo(**vendor.contact),
        tax_id_last4=vendor.tax_id_last4,
        created_at=vendor.created_at,
        updated_at=vendor.updated_at,
    )


@app.get("/api/v1/vendors", response_model=VendorListResponse)
async def list_vendors(
    status_filter: VendorStatus | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant: Tenant = Depends(get_tenant_dependency),
    db: Session = Depends(get_db),
) -> VendorListResponse:
    """List vendors for the authenticated tenant."""
    query = db.query(Vendor).filter(Vendor.tenant_id == tenant.id)

    if status_filter:
        query = query.filter(Vendor.status == status_filter.value)

    total = query.count()
    vendors = query.order_by(Vendor.created_at.desc()).limit(limit).offset(offset).all()

    items = []
    for vendor in vendors:
        items.append(
            VendorResponse(
                vendor_id=vendor.id,
                external_id=vendor.external_id,
                legal_name=vendor.legal_name,
                doing_business_as=vendor.doing_business_as,
                status=VendorStatus(vendor.status),
                primary_location=Location(**vendor.primary_location),
                contact=None if vendor.contact is None else ContactInfo(**vendor.contact),
                tax_id_last4=vendor.tax_id_last4,
                created_at=vendor.created_at,
                updated_at=vendor.updated_at,
            )
        )

    return VendorListResponse(items=items, total=total)


@app.get("/api/v1/vendors/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: UUID,
    tenant: Tenant = Depends(get_tenant_dependency),
    db: Session = Depends(get_db),
) -> VendorResponse:
    """Get vendor details."""
    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.id == vendor_id,
            Vendor.tenant_id == tenant.id,
        )
        .first()
    )

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code="vendor_not_found",
                message="Vendor not found",
            ).model_dump(),
        )

    return VendorResponse(
        vendor_id=vendor.id,
        external_id=vendor.external_id,
        legal_name=vendor.legal_name,
        doing_business_as=vendor.doing_business_as,
        status=VendorStatus(vendor.status),
        primary_location=Location(**vendor.primary_location),
        contact=None if vendor.contact is None else ContactInfo(**vendor.contact),
        tax_id_last4=vendor.tax_id_last4,
        created_at=vendor.created_at,
        updated_at=vendor.updated_at,
    )


# ============================================================================
# Document Endpoints
# ============================================================================


@app.post("/api/v1/vendors/{vendor_id}/documents", response_model=DocumentUploadResponse)
async def create_vendor_document(
    vendor_id: UUID,
    request: DocumentRequest,
    tenant: Tenant = Depends(get_tenant_dependency),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    """Create a vendor document and return presigned upload URL."""
    # Verify vendor belongs to tenant
    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.id == vendor_id,
            Vendor.tenant_id == tenant.id,
        )
        .first()
    )

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code="vendor_not_found",
                message="Vendor not found",
            ).model_dump(),
        )

    # Generate storage key
    doc_id = uuid4()
    storage_key = f"tenant/{tenant.id}/vendor/{vendor_id}/{doc_id}"

    # Create document record
    document = VendorDocument(
        id=doc_id,
        vendor_id=vendor_id,
        type=request.type.value,
        jurisdiction=request.jurisdiction.model_dump(),
        expires_on=datetime.combine(request.expires_on, datetime.min.time(), tzinfo=UTC) if request.expires_on else None,
        storage_key=storage_key,
        file_name=request.file_name,
        content_type=request.content_type,
    )

    db.add(document)

    # Audit event
    create_audit_event(
        db=db,
        tenant_id=tenant.id,
        actor_type="api",
        event_type="document_created",
        entity_type="document",
        entity_id=str(doc_id),
        payload={
            "vendor_id": str(vendor_id),
            "type": request.type.value,
        },
    )

    db.commit()
    db.refresh(document)

    # Generate presigned URL
    upload_url = generate_presigned_upload_url(storage_key, request.content_type)
    expires_in = 3600

    logger.info(f"Document created: {doc_id} for vendor {vendor_id}")

    return DocumentUploadResponse(
        document_id=doc_id,
        upload_url=upload_url,
        upload_expires_in=expires_in,
    )


@app.get("/api/v1/vendors/{vendor_id}/documents", response_model=DocumentListResponse)
async def list_vendor_documents(
    vendor_id: UUID,
    tenant: Tenant = Depends(get_tenant_dependency),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    """List all documents for a vendor."""
    # Verify vendor belongs to tenant
    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.id == vendor_id,
            Vendor.tenant_id == tenant.id,
        )
        .first()
    )

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code="vendor_not_found",
                message="Vendor not found",
            ).model_dump(),
        )

    documents = (
        db.query(VendorDocument)
        .filter(VendorDocument.vendor_id == vendor_id)
        .order_by(VendorDocument.created_at.desc())
        .all()
    )

    items = []
    for doc in documents:
        items.append(
            DocumentResponse(
                document_id=doc.id,
                type=doc.type,
                jurisdiction=Location(**doc.jurisdiction),
                expires_on=doc.expires_on.date() if doc.expires_on else None,
                file_name=doc.file_name,
                content_type=doc.content_type,
                storage_key=doc.storage_key,
                created_at=doc.created_at,
            )
        )

    return DocumentListResponse(items=items, total=len(items))


# ============================================================================
# Verification Endpoints
# ============================================================================


@app.post("/api/v1/vendors/{vendor_id}/verifications", response_model=VerificationResponse)
async def create_verification(
    vendor_id: UUID,
    request: VerificationRequest,
    tenant: Tenant = Depends(get_tenant_dependency),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> VerificationResponse:
    """Trigger a verification run for a vendor."""
    # Verify vendor belongs to tenant
    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.id == vendor_id,
            Vendor.tenant_id == tenant.id,
        )
        .first()
    )

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code="vendor_not_found",
                message="Vendor not found",
            ).model_dump(),
        )

    # Check for idempotency
    if idempotency_key:
        existing_run = (
            db.query(VerificationRun)
            .filter(
                VerificationRun.tenant_id == tenant.id,
                VerificationRun.vendor_id == vendor_id,
                VerificationRun.idempotency_key == idempotency_key,
            )
            .first()
        )

        if existing_run:
            logger.info(f"Returning existing verification run: {existing_run.id} (idempotency key: {idempotency_key})")
            return VerificationResponse(
                verification_id=existing_run.id,
                vendor_id=existing_run.vendor_id,
                status=VerificationStatus(existing_run.status),
                jurisdiction=Location(**existing_run.jurisdiction),
                kitchen_id=existing_run.kitchen_id,
            )

    # Get vendor documents
    documents = db.query(VendorDocument).filter(VendorDocument.vendor_id == vendor_id).all()

    # Get ruleset metadata
    ruleset_name, regulation_version, engine_version = get_ruleset_metadata(request.jurisdiction)

    # Create verification run
    verification = VerificationRun(
        tenant_id=tenant.id,
        vendor_id=vendor_id,
        status=VerificationStatus.IN_REVIEW.value,
        jurisdiction=request.jurisdiction.model_dump(),
        kitchen_id=request.kitchen_id,
        initiated_by=request.requested_by,
        initiated_from=InitiatedFrom.API.value,
        ruleset_name=ruleset_name,
        regulation_version=regulation_version,
        engine_version=engine_version,
        idempotency_key=idempotency_key,
    )

    db.add(verification)
    db.flush()  # Get the ID

    # Run verification immediately
    decision, recommendation = run_verification(vendor, documents, request.jurisdiction)

    # Update verification with results
    verification.decision_snapshot = {
        "decision": decision.model_dump(mode='json'),
        "recommendation": recommendation.model_dump(mode='json'),
    }
    verification.status = (
        VerificationStatus.PASSED.value
        if decision.overall.value == "pass"
        else VerificationStatus.FAILED.value
    )
    verification.evaluated_at = datetime.now(UTC)

    # Audit event
    create_audit_event(
        db=db,
        tenant_id=tenant.id,
        actor_type="api",
        actor_id=request.requested_by,
        event_type="verification_completed",
        entity_type="verification",
        entity_id=str(verification.id),
        payload={
            "vendor_id": str(vendor_id),
            "status": verification.status,
            "overall": decision.overall.value,
        },
    )

    db.commit()
    db.refresh(verification)

    logger.info(f"Verification created: {verification.id} for vendor {vendor_id}, status: {verification.status}")

    return VerificationResponse(
        verification_id=verification.id,
        vendor_id=vendor_id,
        status=VerificationStatus(verification.status),
        jurisdiction=request.jurisdiction,
        kitchen_id=request.kitchen_id,
    )


@app.get(
    "/api/v1/vendors/{vendor_id}/verifications/{verification_id}",
    response_model=VerificationDetail,
)
async def get_verification(
    vendor_id: UUID,
    verification_id: UUID,
    tenant: Tenant = Depends(get_tenant_dependency),
    db: Session = Depends(get_db),
) -> VerificationDetail:
    """Get detailed verification information."""
    # Verify vendor belongs to tenant
    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.id == vendor_id,
            Vendor.tenant_id == tenant.id,
        )
        .first()
    )

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code="vendor_not_found",
                message="Vendor not found",
            ).model_dump(),
        )

    # Get verification
    verification = (
        db.query(VerificationRun)
        .filter(
            VerificationRun.id == verification_id,
            VerificationRun.vendor_id == vendor_id,
            VerificationRun.tenant_id == tenant.id,
        )
        .first()
    )

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                code="verification_not_found",
                message="Verification not found",
            ).model_dump(),
        )

    # Extract decision and recommendation from snapshot
    snapshot = verification.decision_snapshot or {}
    decision_data = snapshot.get("decision", {})
    recommendation_data = snapshot.get("recommendation", {})

    from apps.vendor_verification.models import Decision, Recommendation

    decision = Decision(**decision_data) if decision_data else Decision(overall="fail", score=0.0, check_results=[])
    recommendation = Recommendation(**recommendation_data) if recommendation_data else Recommendation(summary="No recommendation available")

    return VerificationDetail(
        verification_id=verification.id,
        vendor_id=verification.vendor_id,
        status=VerificationStatus(verification.status),
        evaluated_at=verification.evaluated_at,
        jurisdiction=Location(**verification.jurisdiction),
        kitchen_id=verification.kitchen_id,
        decision=decision,
        recommendation=recommendation,
        ruleset_name=verification.ruleset_name,
        regulation_version=verification.regulation_version,
        engine_version=verification.engine_version,
        initiated_by=verification.initiated_by,
        initiated_from=InitiatedFrom(verification.initiated_from),
        created_at=verification.created_at,
        updated_at=verification.updated_at,
    )


# ============================================================================
# Main entry point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
