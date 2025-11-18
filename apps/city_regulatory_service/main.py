"""
City Regulatory Service

FastAPI microservice providing access to city-level compliance requirements,
building on the federal regulatory engine.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from apps.city_regulatory_service.src.etl import CITY_ADAPTERS, CityETLOrchestrator
from apps.city_regulatory_service.src.models import (
    CityAgency,
    CityJurisdiction,
    CityRequirement,
)
from prep.models.db import SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Prep City Regulatory Service",
    description="City-level compliance backbone for the Prep Regulatory Engine",
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
# Pydantic Models
# ============================================================================


class JurisdictionResponse(BaseModel):
    """Jurisdiction information."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    city: str
    state: str
    county: str | None = None
    population: int | None = None
    food_code_version: str | None = None
    portal_url: str | None = None
    business_license_url: str | None = None
    health_department_url: str | None = None


class AgencyResponse(BaseModel):
    """Agency information."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    agency_type: str
    contact_email: str | None = None
    contact_phone: str | None = None
    portal_link: str | None = None


class RequirementResponse(BaseModel):
    """City regulatory requirement."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    requirement_id: str
    requirement_label: str
    requirement_type: str
    jurisdiction_city: str
    jurisdiction_state: str
    agency_name: str
    applies_to: list[str]
    required_documents: list[str]
    submission_channel: str
    application_url: str | None = None
    inspection_required: bool
    renewal_frequency: str
    fee_amount: float | None = None
    fee_schedule: str
    source_url: str
    last_updated: datetime
    rules: dict[str, Any]


class RequirementDetailResponse(BaseModel):
    """Detailed requirement with jurisdiction and agency info."""

    requirement: RequirementResponse
    jurisdiction: JurisdictionResponse
    agency: AgencyResponse


class ComplianceQueryRequest(BaseModel):
    """Request for compliance requirements query."""

    jurisdiction: str = Field(..., description="City name (e.g., 'San Francisco', 'New York')")
    business_type: str | None = Field(
        None, description="Business type filter (e.g., 'restaurant', 'food_truck')"
    )
    requirement_type: str | None = Field(
        None, description="Requirement type filter (e.g., 'business_license', 'health_permit')"
    )


class ComplianceQueryResponse(BaseModel):
    """Response with compliance requirements."""

    jurisdiction: str
    business_type: str | None
    requirement_count: int
    requirements: list[RequirementResponse]
    estimated_total_cost: float | None = None


class ETLRunRequest(BaseModel):
    """Request to trigger ETL run."""

    city: str | None = Field(
        None, description="Specific city to run ETL for, or None for all cities"
    )


class ETLRunResponse(BaseModel):
    """Response from ETL run."""

    status: str
    cities_processed: list[str]
    results: dict[str, dict[str, Any]]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    database_connected: bool
    available_cities: list[str]
    total_requirements: int


# ============================================================================
# Helper Functions
# ============================================================================


def format_requirement_response(
    req: CityRequirement,
    jurisdiction: CityJurisdiction,
    agency: CityAgency,
) -> RequirementResponse:
    """Format requirement for API response."""
    return RequirementResponse(
        id=str(req.id),
        requirement_id=req.requirement_id,
        requirement_label=req.requirement_label,
        requirement_type=req.requirement_type,
        jurisdiction_city=jurisdiction.city,
        jurisdiction_state=jurisdiction.state,
        agency_name=agency.name,
        applies_to=req.applies_to or [],
        required_documents=req.required_documents or [],
        submission_channel=req.submission_channel or "unknown",
        application_url=req.application_url,
        inspection_required=req.inspection_required,
        renewal_frequency=req.renewal_frequency or "unknown",
        fee_amount=float(req.fee_amount) if req.fee_amount else None,
        fee_schedule=req.fee_schedule or "unknown",
        source_url=req.source_url,
        last_updated=req.last_updated,
        rules=req.rules or {},
    )


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/healthz", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """Health check endpoint."""

    database_connected = False
    total_requirements = 0

    try:
        total_requirements = db.query(func.count(CityRequirement.id)).scalar() or 0
        database_connected = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    return HealthResponse(
        status="ok" if database_connected else "degraded",
        version="1.0.0",
        database_connected=database_connected,
        available_cities=list(CITY_ADAPTERS.keys()),
        total_requirements=total_requirements,
    )


@app.get("/cities/jurisdictions", response_model=list[JurisdictionResponse])
async def list_jurisdictions(db: Session = Depends(get_db)) -> list[JurisdictionResponse]:
    """
    List all available city jurisdictions.

    Returns all jurisdictions with metadata.
    """
    jurisdictions = db.query(CityJurisdiction).order_by(CityJurisdiction.city).all()

    return [
        JurisdictionResponse(
            id=str(j.id),
            city=j.city,
            state=j.state,
            county=j.county,
            population=j.population,
            food_code_version=j.food_code_version,
            portal_url=j.portal_url,
            business_license_url=j.business_license_url,
            health_department_url=j.health_department_url,
        )
        for j in jurisdictions
    ]


@app.get("/cities/{city}/agencies", response_model=list[AgencyResponse])
async def list_agencies(
    city: str,
    db: Session = Depends(get_db),
) -> list[AgencyResponse]:
    """
    List agencies for a specific city.

    Returns all agencies that enforce regulations in the specified city.
    """
    jurisdiction = db.query(CityJurisdiction).filter_by(city=city).first()

    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Jurisdiction '{city}' not found",
        )

    agencies = (
        db.query(CityAgency)
        .filter_by(jurisdiction_id=jurisdiction.id)
        .order_by(CityAgency.name)
        .all()
    )

    return [
        AgencyResponse(
            id=str(a.id),
            name=a.name,
            agency_type=a.agency_type,
            contact_email=a.contact_email,
            contact_phone=a.contact_phone,
            portal_link=a.portal_link,
        )
        for a in agencies
    ]


@app.get("/compliance/requirements", response_model=list[RequirementResponse])
async def list_requirements(
    jurisdiction: str | None = Query(None, description="Filter by city name"),
    business_type: str | None = Query(None, description="Filter by business type"),
    requirement_type: str | None = Query(None, description="Filter by requirement type"),
    db: Session = Depends(get_db),
) -> list[RequirementResponse]:
    """
    List compliance requirements with optional filters.

    Supports filtering by jurisdiction, business type, and requirement type.
    """
    query = (
        db.query(
            CityRequirement,
            CityJurisdiction,
            CityAgency,
        )
        .join(
            CityJurisdiction,
            CityRequirement.jurisdiction_id == CityJurisdiction.id,
        )
        .join(
            CityAgency,
            CityRequirement.agency_id == CityAgency.id,
        )
        .filter(CityRequirement.is_active)
    )

    if jurisdiction:
        query = query.filter(CityJurisdiction.city.ilike(f"%{jurisdiction}%"))

    if requirement_type:
        query = query.filter(CityRequirement.requirement_type == requirement_type)

    results = query.all()

    # Filter by business type if specified
    if business_type:
        filtered_results = []
        for req, juris, agency in results:
            applies_to = req.applies_to or []
            if business_type.lower() in [bt.lower() for bt in applies_to] or "all" in applies_to:
                filtered_results.append((req, juris, agency))
        results = filtered_results

    return [format_requirement_response(req, juris, agency) for req, juris, agency in results]


@app.post("/compliance/query", response_model=ComplianceQueryResponse)
async def query_compliance_requirements(
    request: ComplianceQueryRequest,
    db: Session = Depends(get_db),
) -> ComplianceQueryResponse:
    """
    Query compliance requirements for a specific jurisdiction and business type.

    Returns comprehensive compliance checklist with cost estimates.
    """
    # Find jurisdiction
    jurisdiction = (
        db.query(CityJurisdiction)
        .filter(CityJurisdiction.city.ilike(f"%{request.jurisdiction}%"))
        .first()
    )

    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Jurisdiction '{request.jurisdiction}' not found",
        )

    # Build query
    query = (
        db.query(
            CityRequirement,
            CityJurisdiction,
            CityAgency,
        )
        .join(
            CityJurisdiction,
            CityRequirement.jurisdiction_id == CityJurisdiction.id,
        )
        .join(
            CityAgency,
            CityRequirement.agency_id == CityAgency.id,
        )
        .filter(
            CityRequirement.jurisdiction_id == jurisdiction.id,
            CityRequirement.is_active,
        )
    )

    if request.requirement_type:
        query = query.filter(CityRequirement.requirement_type == request.requirement_type)

    results = query.all()

    # Filter by business type if specified
    if request.business_type:
        filtered_results = []
        for req, juris, agency in results:
            applies_to = req.applies_to or []
            if (
                request.business_type.lower() in [bt.lower() for bt in applies_to]
                or "all" in applies_to
            ):
                filtered_results.append((req, juris, agency))
        results = filtered_results

    # Calculate total cost estimate
    total_cost = 0.0
    for req, _, _ in results:
        if req.fee_amount:
            total_cost += float(req.fee_amount)

    requirements = [
        format_requirement_response(req, juris, agency) for req, juris, agency in results
    ]

    return ComplianceQueryResponse(
        jurisdiction=jurisdiction.city,
        business_type=request.business_type,
        requirement_count=len(requirements),
        requirements=requirements,
        estimated_total_cost=total_cost if total_cost > 0 else None,
    )


@app.get("/compliance/requirements/{requirement_id}", response_model=RequirementDetailResponse)
async def get_requirement_detail(
    requirement_id: str,
    db: Session = Depends(get_db),
) -> RequirementDetailResponse:
    """
    Get detailed information about a specific requirement.

    Returns complete requirement details with jurisdiction and agency info.
    """
    result = (
        db.query(
            CityRequirement,
            CityJurisdiction,
            CityAgency,
        )
        .join(
            CityJurisdiction,
            CityRequirement.jurisdiction_id == CityJurisdiction.id,
        )
        .join(
            CityAgency,
            CityRequirement.agency_id == CityAgency.id,
        )
        .filter(CityRequirement.requirement_id == requirement_id)
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement '{requirement_id}' not found",
        )

    req, juris, agency = result

    return RequirementDetailResponse(
        requirement=format_requirement_response(req, juris, agency),
        jurisdiction=JurisdictionResponse(
            id=str(juris.id),
            city=juris.city,
            state=juris.state,
            county=juris.county,
            population=juris.population,
            food_code_version=juris.food_code_version,
            portal_url=juris.portal_url,
            business_license_url=juris.business_license_url,
            health_department_url=juris.health_department_url,
        ),
        agency=AgencyResponse(
            id=str(agency.id),
            name=agency.name,
            agency_type=agency.agency_type,
            contact_email=agency.contact_email,
            contact_phone=agency.contact_phone,
            portal_link=agency.portal_link,
        ),
    )


@app.post("/etl/run", response_model=ETLRunResponse)
async def trigger_etl(
    request: ETLRunRequest,
    db: Session = Depends(get_db),
) -> ETLRunResponse:
    """
    Trigger ETL pipeline to ingest city regulatory data.

    Can run for a specific city or all available cities.
    """
    try:
        orchestrator = CityETLOrchestrator(db)

        if request.city:
            if request.city not in CITY_ADAPTERS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"City '{request.city}' not supported. Available: {list(CITY_ADAPTERS.keys())}",
                )
            results = {request.city: orchestrator.run_etl_for_city(request.city)}
            cities = [request.city]
        else:
            results = orchestrator.run_etl_for_all_cities()
            cities = list(CITY_ADAPTERS.keys())

        return ETLRunResponse(
            status="completed",
            cities_processed=cities,
            results=results,
        )

    except Exception as e:
        logger.error(f"ETL run failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ETL failed: {str(e)}",
        )


# ============================================================================
# Main entry point
# ============================================================================

if __name__ == "__main__":
    import os

    import uvicorn

    # Bind to localhost by default for security; allow override via environment variable
    host = os.getenv("BIND_HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=8002)
