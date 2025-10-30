"""
City Regulatory Service - FastAPI Application

This service provides access to city-level compliance regulations for food
preparation facilities across major US cities.

API Endpoints:
- GET /city/{city_name}/{state}/regulations - Get regulations for a city
- GET /city/{city_name}/{state}/insurance-requirements - Get insurance requirements
- GET /city/{city_name}/{state}/compliance-check - Check facility compliance
- POST /city/data/ingest - Ingest new regulatory data
- GET /cities - List all supported cities
- GET /health - Health check endpoint
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from models import (
    CityJurisdiction,
    CityRegulation,
    CityInsuranceRequirement,
    CityPermitApplication,
    FacilityComplianceStatus,
    CityJurisdictionSchema,
    CityRegulationSchema,
    CityInsuranceRequirementSchema,
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    RegulationSummary,
    DataIngestionRequest,
    DataIngestionResponse,
    RegulationType,
    FacilityType,
    ComplianceStatus,
)
from database import get_session, get_engine, init_database
City Regulatory Service

FastAPI microservice providing access to city-level compliance requirements,
building on the federal regulatory engine.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from prep.models.db import SessionLocal
from apps.city_regulatory_service.src.etl import CITY_ADAPTERS, CityETLOrchestrator
from apps.city_regulatory_service.src.models import (
    CityAgency,
    CityJurisdiction,
    CityRequirement,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="City Regulatory Service",
    description="City-level compliance regulations for food preparation facilities",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get database session
def get_db():
    """Dependency to provide database session"""
    db = get_session()
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
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "city-regulatory-service",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "City Regulatory Service",
        "version": "1.0.0",
        "description": "City-level compliance regulations for food preparation facilities",
        "endpoints": {
            "cities": "/cities",
            "regulations": "/city/{city_name}/{state}/regulations",
            "insurance": "/city/{city_name}/{state}/insurance-requirements",
            "compliance_check": "/city/{city_name}/{state}/compliance-check",
            "data_ingest": "/city/data/ingest",
        },
    }


# ============================================================================
# CITY INFORMATION ENDPOINTS
# ============================================================================

@app.get("/cities", response_model=List[CityJurisdictionSchema])
async def list_cities(
    state: Optional[str] = Query(None, description="Filter by state code (e.g., 'CA')"),
    db: Session = Depends(get_db),
):
    """
    List all supported cities.

    Args:
        state: Optional state filter
        db: Database session

    Returns:
        List of city jurisdictions
    """
    query = db.query(CityJurisdiction)

    if state:
        query = query.filter(CityJurisdiction.state == state.upper())

    cities = query.order_by(CityJurisdiction.city_name).all()

    logger.info(f"Retrieved {len(cities)} cities")
    return cities


@app.get("/city/{city_name}/{state}", response_model=CityJurisdictionSchema)
async def get_city(
    city_name: str,
    state: str,
    db: Session = Depends(get_db),
):
    """
    Get details for a specific city.

    Args:
        city_name: City name (e.g., "San Francisco")
        state: State code (e.g., "CA")
        db: Database session

    Returns:
        City jurisdiction details
    """
    city = db.query(CityJurisdiction).filter(
        and_(
            CityJurisdiction.city_name.ilike(city_name),
            CityJurisdiction.state == state.upper(),
        )
    ).first()

    if not city:
        raise HTTPException(
            status_code=404,
            detail=f"City not found: {city_name}, {state}",
        )

    return city


# ============================================================================
# REGULATION ENDPOINTS
# ============================================================================

@app.get("/city/{city_name}/{state}/regulations", response_model=List[CityRegulationSchema])
async def get_city_regulations(
    city_name: str,
    state: str,
    regulation_type: Optional[str] = Query(None, description="Filter by regulation type"),
    facility_type: Optional[str] = Query(None, description="Filter by facility type"),
    priority: Optional[str] = Query(None, description="Filter by priority (critical/high/medium/low)"),
    active_only: bool = Query(True, description="Only return active regulations"),
    db: Session = Depends(get_db),
):
    """
    Get all regulations for a specific city.

    Args:
        city_name: City name
        state: State code
        regulation_type: Optional filter by regulation type
        facility_type: Optional filter by applicable facility type
        priority: Optional filter by priority
        active_only: Only return active regulations
        db: Database session

    Returns:
        List of city regulations
    """
    # Find the city
    city = db.query(CityJurisdiction).filter(
        and_(
            CityJurisdiction.city_name.ilike(city_name),
            CityJurisdiction.state == state.upper(),
        )
    ).first()

    if not city:
        raise HTTPException(
            status_code=404,
            detail=f"City not found: {city_name}, {state}",
        )

    # Query regulations
    query = db.query(CityRegulation).filter(CityRegulation.city_id == city.id)

    if active_only:
        query = query.filter(CityRegulation.is_active == True)

    if regulation_type:
        query = query.filter(CityRegulation.regulation_type == regulation_type)

    if priority:
        query = query.filter(CityRegulation.priority == priority)

    regulations = query.order_by(CityRegulation.priority.desc(), CityRegulation.title).all()

    # Filter by facility type if specified
    if facility_type:
        regulations = [
            r for r in regulations
            if facility_type in r.applicable_facility_types
        ]

    logger.info(f"Retrieved {len(regulations)} regulations for {city_name}, {state}")
    return regulations


@app.get("/city/{city_name}/{state}/regulations/summary", response_model=RegulationSummary)
async def get_regulations_summary(
    city_name: str,
    state: str,
    db: Session = Depends(get_db),
):
    """
    Get a summary of regulations for a city.

    Args:
        city_name: City name
        state: State code
        db: Database session

    Returns:
        Summary statistics about regulations
    """
    # Find the city
    city = db.query(CityJurisdiction).filter(
        and_(
            CityJurisdiction.city_name.ilike(city_name),
            CityJurisdiction.state == state.upper(),
        )
    ).first()

    if not city:
        raise HTTPException(
            status_code=404,
            detail=f"City not found: {city_name}, {state}",
        )

    # Get all regulations
    regulations = db.query(CityRegulation).filter(
        CityRegulation.city_id == city.id
    ).all()

    # Count by type
    by_type = {}
    by_priority = {}
    facility_types_set = set()

    for reg in regulations:
        # Count by type
        reg_type = reg.regulation_type
        by_type[reg_type] = by_type.get(reg_type, 0) + 1

        # Count by priority
        priority = reg.priority
        by_priority[priority] = by_priority.get(priority, 0) + 1

        # Collect facility types
        for ft in reg.applicable_facility_types:
            facility_types_set.add(ft)

    return RegulationSummary(
        city_name=city.city_name,
        state=city.state,
        total_regulations=len(regulations),
        by_type=by_type,
        by_priority=by_priority,
        total_facility_types=len(facility_types_set),
        last_updated=city.updated_at,
    )


# ============================================================================
# INSURANCE REQUIREMENTS ENDPOINTS
# ============================================================================

@app.get("/city/{city_name}/{state}/insurance-requirements", response_model=List[CityInsuranceRequirementSchema])
async def get_insurance_requirements(
    city_name: str,
    state: str,
    facility_type: Optional[str] = Query(None, description="Filter by facility type"),
    mandatory_only: bool = Query(False, description="Only return mandatory coverage"),
    db: Session = Depends(get_db),
):
    """
    Get insurance requirements for a city.

    Args:
        city_name: City name
        state: State code
        facility_type: Optional filter by facility type
        mandatory_only: Only return mandatory coverage
        db: Database session

    Returns:
        List of insurance requirements
    """
    # Find the city
    city = db.query(CityJurisdiction).filter(
        and_(
            CityJurisdiction.city_name.ilike(city_name),
            CityJurisdiction.state == state.upper(),
        )
    ).first()

    if not city:
        raise HTTPException(
            status_code=404,
            detail=f"City not found: {city_name}, {state}",
        )

    # Query insurance requirements
    query = db.query(CityInsuranceRequirement).filter(
        CityInsuranceRequirement.city_id == city.id
    )

    if mandatory_only:
        query = query.filter(CityInsuranceRequirement.is_mandatory == True)

    requirements = query.order_by(CityInsuranceRequirement.insurance_type).all()

    # Filter by facility type if specified
    if facility_type:
        requirements = [
            r for r in requirements
            if facility_type in r.applicable_facility_types
        ]

    logger.info(f"Retrieved {len(requirements)} insurance requirements for {city_name}, {state}")
    return requirements


# ============================================================================
# COMPLIANCE CHECK ENDPOINTS
# ============================================================================

@app.post("/city/{city_name}/{state}/compliance-check", response_model=ComplianceCheckResponse)
async def check_facility_compliance(
    city_name: str,
    state: str,
    request: ComplianceCheckRequest,
    db: Session = Depends(get_db),
):
    """
    Check compliance status for a facility in a specific city.

    Args:
        city_name: City name
        state: State code
        request: Compliance check request details
        db: Database session

    Returns:
        Compliance check results with recommendations
    """
    # Find the city
    city = db.query(CityJurisdiction).filter(
        and_(
            CityJurisdiction.city_name.ilike(city_name),
            CityJurisdiction.state == state.upper(),
        )
    ).first()

    if not city:
        raise HTTPException(
            status_code=404,
            detail=f"City not found: {city_name}, {state}",
        )

    # Get all applicable regulations for this facility type
    all_regulations = db.query(CityRegulation).filter(
        and_(
            CityRegulation.city_id == city.id,
            CityRegulation.is_active == True,
        )
    ).all()

    # Filter regulations applicable to this facility type
    applicable_regulations = [
        reg for reg in all_regulations
        if request.facility_type.value in reg.applicable_facility_types
    ]

    # Filter by employee count threshold
    if request.employee_count:
        applicable_regulations = [
            reg for reg in applicable_regulations
            if reg.employee_count_threshold is None or request.employee_count >= reg.employee_count_threshold
        ]

    # Filter by revenue threshold
    if request.annual_revenue:
        applicable_regulations = [
            reg for reg in applicable_regulations
            if reg.revenue_threshold is None or request.annual_revenue >= reg.revenue_threshold
        ]

    # Check current permits against requirements
    current_permit_types = set()
    if request.current_permits:
        current_permit_types = {p.get("type", "") for p in request.current_permits}

    compliant_regulations = []
    non_compliant_regulations = []
    missing_requirements = []

    for reg in applicable_regulations:
        # Simple compliance check - in production this would be more sophisticated
        if reg.regulation_type in current_permit_types:
            compliant_regulations.append(reg.id)
        else:
            non_compliant_regulations.append(reg.id)
            missing_requirements.append({
                "regulation_id": reg.id,
                "regulation_type": reg.regulation_type,
                "title": reg.title,
                "priority": reg.priority,
                "enforcement_agency": reg.enforcement_agency,
                "estimated_cost": reg.fees.get("application_fee", 0) if reg.fees else 0,
                "estimated_time_days": reg.renewal_period_days or 30,
            })

    # Check insurance requirements
    insurance_requirements = db.query(CityInsuranceRequirement).filter(
        CityInsuranceRequirement.city_id == city.id
    ).all()

    applicable_insurance = [
        ins for ins in insurance_requirements
        if request.facility_type.value in ins.applicable_facility_types
    ]

    current_insurance_types = set()
    if request.current_insurance:
        current_insurance_types = {i.get("type", "") for i in request.current_insurance}

    insurance_gaps = []
    for ins in applicable_insurance:
        if ins.is_mandatory and ins.insurance_type not in current_insurance_types:
            insurance_gaps.append(f"{ins.coverage_name} (${ins.minimum_coverage_amount:,.0f} minimum)")

    insurance_compliant = len(insurance_gaps) == 0

    # Calculate compliance score
    total_requirements = len(applicable_regulations) + len(applicable_insurance)
    met_requirements = len(compliant_regulations) + (len(applicable_insurance) - len(insurance_gaps))
    compliance_score = (met_requirements / total_requirements * 100) if total_requirements > 0 else 100.0

    # Overall compliance
    overall_compliant = len(non_compliant_regulations) == 0 and insurance_compliant

    # Generate recommended actions
    recommended_actions = []
    for missing in missing_requirements:
        recommended_actions.append({
            "action": f"Obtain {missing['title']}",
            "priority": missing["priority"],
            "agency": missing["enforcement_agency"],
            "estimated_cost": missing["estimated_cost"],
            "estimated_days": missing["estimated_time_days"],
        })

    # Estimate total cost and time to comply
    estimated_cost = sum(m["estimated_cost"] for m in missing_requirements)
    estimated_time = max([m["estimated_time_days"] for m in missing_requirements], default=0)

    # Calculate next review date (earliest expiration)
    next_review = None
    if request.current_permits:
        expiration_dates = [
            datetime.fromisoformat(p["expiration_date"])
            for p in request.current_permits
            if "expiration_date" in p
        ]
        if expiration_dates:
            next_review = min(expiration_dates)

    return ComplianceCheckResponse(
        facility_id=request.facility_id,
        city_name=city.city_name,
        state=city.state,
        overall_compliant=overall_compliant,
        compliance_score=compliance_score,
        required_regulations=[CityRegulationSchema.model_validate(r) for r in applicable_regulations],
        compliant_regulations=compliant_regulations,
        non_compliant_regulations=non_compliant_regulations,
        missing_requirements=missing_requirements,
        insurance_compliant=insurance_compliant,
        insurance_gaps=insurance_gaps if insurance_gaps else None,
        recommended_actions=recommended_actions,
        estimated_cost_to_comply=estimated_cost if estimated_cost > 0 else None,
        estimated_time_to_comply_days=estimated_time if estimated_time > 0 else None,
        check_timestamp=datetime.utcnow(),
        next_review_date=next_review,
    )


# ============================================================================
# DATA INGESTION ENDPOINTS
# ============================================================================

@app.post("/city/data/ingest", response_model=DataIngestionResponse)
async def ingest_regulatory_data(
    request: DataIngestionRequest,
    db: Session = Depends(get_db),
):
    """
    Ingest new regulatory data for a city.

    This endpoint allows bulk import of regulatory data collected from
    city sources.

    Args:
        request: Data ingestion request
        db: Database session

    Returns:
        Ingestion results with counts and errors
    """
    errors = []
    warnings = []

    try:
        # Find or create city jurisdiction
        city = db.query(CityJurisdiction).filter(
            and_(
                CityJurisdiction.city_name.ilike(request.city_name),
                CityJurisdiction.state == request.state.upper(),
            )
        ).first()

        if not city:
            # Create new city if jurisdiction info provided
            if request.jurisdiction_info:
                city = CityJurisdiction(
                    city_name=request.city_name,
                    state=request.state.upper(),
                    **request.jurisdiction_info,
                    data_source=request.data_source,
                    last_verified=request.verification_date,
                )
                db.add(city)
                db.commit()
                db.refresh(city)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"City not found and no jurisdiction info provided: {request.city_name}, {request.state}",
                )

        # Import regulations
        regulations_imported = 0
        for reg_data in request.regulations:
            try:
                # Check if regulation already exists
                existing = db.query(CityRegulation).filter(
                    and_(
                        CityRegulation.city_id == city.id,
                        CityRegulation.regulation_type == reg_data.get("regulation_type"),
                        CityRegulation.title == reg_data.get("title"),
                    )
                ).first()

                if existing:
                    # Update existing regulation
                    for key, value in reg_data.items():
                        setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                    existing.last_verified = request.verification_date
                    warnings.append(f"Updated existing regulation: {reg_data.get('title')}")
                else:
                    # Create new regulation
                    regulation = CityRegulation(
                        city_id=city.id,
                        **reg_data,
                        data_source=request.data_source,
                        last_verified=request.verification_date,
                    )
                    db.add(regulation)

                regulations_imported += 1

            except Exception as e:
                errors.append(f"Failed to import regulation {reg_data.get('title')}: {str(e)}")

        # Import insurance requirements
        insurance_imported = 0
        if request.insurance_requirements:
            for ins_data in request.insurance_requirements:
                try:
                    # Check if requirement already exists
                    existing = db.query(CityInsuranceRequirement).filter(
                        and_(
                            CityInsuranceRequirement.city_id == city.id,
                            CityInsuranceRequirement.insurance_type == ins_data.get("insurance_type"),
                        )
                    ).first()

                    if existing:
                        # Update existing requirement
                        for key, value in ins_data.items():
                            setattr(existing, key, value)
                        existing.updated_at = datetime.utcnow()
                        warnings.append(f"Updated existing insurance requirement: {ins_data.get('coverage_name')}")
                    else:
                        # Create new requirement
                        insurance_req = CityInsuranceRequirement(
                            city_id=city.id,
                            **ins_data,
                        )
                        db.add(insurance_req)

                    insurance_imported += 1

                except Exception as e:
                    errors.append(f"Failed to import insurance requirement {ins_data.get('coverage_name')}: {str(e)}")

        # Commit all changes
        db.commit()

        return DataIngestionResponse(
            success=len(errors) == 0,
            city_id=city.id,
            regulations_imported=regulations_imported,
            insurance_requirements_imported=insurance_imported,
            errors=errors if errors else None,
            warnings=warnings if warnings else None,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Data ingestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data ingestion failed: {str(e)}")


# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Starting City Regulatory Service...")
    engine = get_engine()
    init_database(engine)
    logger.info("City Regulatory Service started successfully!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down City Regulatory Service...")


# ============================================================================
# MAIN
# Pydantic Models
# ============================================================================

class JurisdictionResponse(BaseModel):
    """Jurisdiction information."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    city: str
    state: str
    county: Optional[str] = None
    population: Optional[int] = None
    food_code_version: Optional[str] = None
    portal_url: Optional[str] = None
    business_license_url: Optional[str] = None
    health_department_url: Optional[str] = None


class AgencyResponse(BaseModel):
    """Agency information."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    agency_type: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    portal_link: Optional[str] = None


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
    application_url: Optional[str] = None
    inspection_required: bool
    renewal_frequency: str
    fee_amount: Optional[float] = None
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
    business_type: Optional[str] = Field(None, description="Business type filter (e.g., 'restaurant', 'food_truck')")
    requirement_type: Optional[str] = Field(None, description="Requirement type filter (e.g., 'business_license', 'health_permit')")


class ComplianceQueryResponse(BaseModel):
    """Response with compliance requirements."""

    jurisdiction: str
    business_type: Optional[str]
    requirement_count: int
    requirements: list[RequirementResponse]
    estimated_total_cost: Optional[float] = None


class ETLRunRequest(BaseModel):
    """Request to trigger ETL run."""

    city: Optional[str] = Field(None, description="Specific city to run ETL for, or None for all cities")


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
    jurisdiction: Optional[str] = Query(None, description="Filter by city name"),
    business_type: Optional[str] = Query(None, description="Filter by business type"),
    requirement_type: Optional[str] = Query(None, description="Filter by requirement type"),
    db: Session = Depends(get_db),
) -> list[RequirementResponse]:
    """
    List compliance requirements with optional filters.

    Supports filtering by jurisdiction, business type, and requirement type.
    """
    query = db.query(
        CityRequirement,
        CityJurisdiction,
        CityAgency,
    ).join(
        CityJurisdiction,
        CityRequirement.jurisdiction_id == CityJurisdiction.id,
    ).join(
        CityAgency,
        CityRequirement.agency_id == CityAgency.id,
    ).filter(
        CityRequirement.is_active == True
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

    return [
        format_requirement_response(req, juris, agency)
        for req, juris, agency in results
    ]


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
    query = db.query(
        CityRequirement,
        CityJurisdiction,
        CityAgency,
    ).join(
        CityJurisdiction,
        CityRequirement.jurisdiction_id == CityJurisdiction.id,
    ).join(
        CityAgency,
        CityRequirement.agency_id == CityAgency.id,
    ).filter(
        CityRequirement.jurisdiction_id == jurisdiction.id,
        CityRequirement.is_active == True,
    )

    if request.requirement_type:
        query = query.filter(CityRequirement.requirement_type == request.requirement_type)

    results = query.all()

    # Filter by business type if specified
    if request.business_type:
        filtered_results = []
        for req, juris, agency in results:
            applies_to = req.applies_to or []
            if request.business_type.lower() in [bt.lower() for bt in applies_to] or "all" in applies_to:
                filtered_results.append((req, juris, agency))
        results = filtered_results

    # Calculate total cost estimate
    total_cost = 0.0
    for req, _, _ in results:
        if req.fee_amount:
            total_cost += float(req.fee_amount)

    requirements = [
        format_requirement_response(req, juris, agency)
        for req, juris, agency in results
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
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info",
    )
    uvicorn.run(app, host="0.0.0.0", port=8002)
