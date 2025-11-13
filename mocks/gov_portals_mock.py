#!/usr/bin/env python3
"""
Mock Government Portals API Server

Mock implementations of LA County and SF Planning portals for local development.

Run with: python mocks/gov_portals_mock.py
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# Create two separate apps for LA and SF
la_app = FastAPI(title="Mock LA County Portal", version="1.0.0")
sf_app = FastAPI(title="Mock SF Planning Portal", version="1.0.0")


# Models
class PermitApplication(BaseModel):
    property_address: str
    owner_name: str
    contact_email: str
    property_type: str


class PermitStatus(BaseModel):
    permit_number: str
    status: str
    issued_date: Optional[str]
    expiration_date: Optional[str]
    conditions: list[str]


# Mock database
LA_PERMITS = {}
SF_PERMITS = {}


# LA County Portal
@la_app.get("/")
async def la_root():
    return {"portal": "LA County STR Portal", "version": "1.0", "mock": True}


@la_app.get("/health")
async def la_health():
    return {"status": "healthy"}


@la_app.post("/api/v1/permits/apply")
async def la_apply_permit(application: PermitApplication):
    """Submit a permit application"""

    permit_number = f"LA-{datetime.now().year}-{secrets.token_hex(4).upper()}"

    permit = {
        "permit_number": permit_number,
        "status": "pending_review",
        "application_date": datetime.now().isoformat(),
        "property_address": application.property_address,
        "owner_name": application.owner_name,
        "estimated_review_time": "14-21 business days",
    }

    LA_PERMITS[permit_number] = permit

    return {
        "permit_number": permit_number,
        "status": "submitted",
        "message": "Application received. You will receive an email when review is complete.",
    }


@la_app.get("/api/v1/permits/{permit_number}")
async def la_get_permit(permit_number: str):
    """Get permit status"""

    if permit_number not in LA_PERMITS:
        raise HTTPException(status_code=404, detail="Permit not found")

    return LA_PERMITS[permit_number]


@la_app.get("/api/v1/permits/search")
async def la_search_permits(address: str = Query(...)):
    """Search permits by address"""

    results = [p for p in LA_PERMITS.values() if address.lower() in p["property_address"].lower()]

    return {"count": len(results), "results": results}


@la_app.post("/api/v1/permits/{permit_number}/approve")
async def la_approve_permit(permit_number: str):
    """Approve a permit (internal use)"""

    if permit_number not in LA_PERMITS:
        raise HTTPException(status_code=404, detail="Permit not found")

    permit = LA_PERMITS[permit_number]
    permit["status"] = "approved"
    permit["issued_date"] = datetime.now().isoformat()
    permit["expiration_date"] = (datetime.now() + timedelta(days=365)).isoformat()

    return permit


# San Francisco Portal
@sf_app.get("/")
async def sf_root():
    return {"portal": "SF Planning Portal", "version": "1.0", "mock": True}


@sf_app.get("/health")
async def sf_health():
    return {"status": "healthy"}


@sf_app.post("/api/v1/str/register")
async def sf_register_str(application: PermitApplication):
    """Register a short-term rental"""

    registration_number = f"SF-STR-{datetime.now().year}-{secrets.token_hex(3).upper()}"

    registration = {
        "registration_number": registration_number,
        "status": "pending_review",
        "submission_date": datetime.now().isoformat(),
        "property_address": application.property_address,
        "host_name": application.owner_name,
        "business_license_required": True,
        "tob_permit_required": True,
        "estimated_processing_time": "30-45 days",
    }

    SF_PERMITS[registration_number] = registration

    return {
        "registration_number": registration_number,
        "status": "submitted",
        "message": "Registration submitted. Please complete business license and TOB requirements.",
        "next_steps": [
            "Obtain Business Registration Certificate",
            "Complete Transient Occupancy Registration",
            "Schedule fire safety inspection",
        ],
    }


@sf_app.get("/api/v1/str/{registration_number}")
async def sf_get_registration(registration_number: str):
    """Get registration status"""

    if registration_number not in SF_PERMITS:
        raise HTTPException(status_code=404, detail="Registration not found")

    return SF_PERMITS[registration_number]


@sf_app.get("/api/v1/str/lookup")
async def sf_lookup_str(address: str = Query(...)):
    """Lookup STR by address"""

    results = [p for p in SF_PERMITS.values() if address.lower() in p["property_address"].lower()]

    return {"count": len(results), "registrations": results}


@sf_app.post("/api/v1/str/{registration_number}/approve")
async def sf_approve_registration(registration_number: str):
    """Approve a registration (internal use)"""

    if registration_number not in SF_PERMITS:
        raise HTTPException(status_code=404, detail="Registration not found")

    registration = SF_PERMITS[registration_number]
    registration["status"] = "active"
    registration["approval_date"] = datetime.now().isoformat()
    registration["renewal_date"] = (datetime.now() + timedelta(days=365)).isoformat()

    return registration


@sf_app.get("/api/v1/requirements")
async def sf_get_requirements(property_type: str = Query("entire_home")):
    """Get STR requirements"""

    requirements = {
        "property_type": property_type,
        "requirements": [
            {"name": "Business Registration Certificate", "required": True, "fee": "$91"},
            {"name": "Transient Occupancy Registration", "required": True, "fee": "$50"},
            {"name": "Fire Safety Inspection", "required": True, "fee": "$150"},
            {"name": "Planning Code Compliance", "required": True, "fee": "$0"},
        ],
        "total_fees": "$291",
        "processing_time": "30-45 days",
    }

    return requirements


# Debug endpoints
@la_app.get("/debug/permits")
async def la_debug_permits():
    return {"permits": list(LA_PERMITS.values())}


@la_app.delete("/debug/reset")
async def la_debug_reset():
    LA_PERMITS.clear()
    return {"status": "reset complete"}


@sf_app.get("/debug/registrations")
async def sf_debug_registrations():
    return {"registrations": list(SF_PERMITS.values())}


@sf_app.delete("/debug/reset")
async def sf_debug_reset():
    SF_PERMITS.clear()
    return {"status": "reset complete"}


if __name__ == "__main__":
    import asyncio
    import uvicorn

    print("🏛️  Starting Mock Government Portals...")
    print("📍 LA County Portal: http://localhost:8002")
    print("📍 SF Planning Portal: http://localhost:8003")

    async def run_servers():
        la_config = uvicorn.Config(la_app, host="0.0.0.0", port=8002, log_level="info")
        sf_config = uvicorn.Config(sf_app, host="0.0.0.0", port=8003, log_level="info")

        la_server = uvicorn.Server(la_config)
        sf_server = uvicorn.Server(sf_config)

        await asyncio.gather(la_server.serve(), sf_server.serve())

    asyncio.run(run_servers())
