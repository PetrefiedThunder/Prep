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
