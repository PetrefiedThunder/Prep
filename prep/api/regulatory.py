"""Public regulatory endpoints used by the Prep client."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database.connection import get_db
from prep.regulatory.service import get_regulations_for_jurisdiction

router = APIRouter(prefix="/regulatory", tags=["regulatory"])


@router.get("/regulations/{state}")
async def list_regulations(
    state: str,
    city: Optional[str] = Query(default=None),
    country_code: str = Query(default="US", min_length=2, max_length=2),
    state_province: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return regulations for the provided jurisdiction."""

    regulations = await get_regulations_for_jurisdiction(
        db,
        state,
        city,
        country_code=country_code.upper(),
        state_province=state_province,
    )
    return {"regulations": regulations}
"""FastAPI endpoints for regulatory data and compliance analysis."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import httpx
import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.compliance.constants import BOOKING_COMPLIANCE_BANNER, BOOKING_PILOT_BANNER
from prep.database.connection import AsyncSessionLocal, get_db
from prep.pilot.utils import is_pilot_location
from prep.regulatory.analyzer import RegulatoryAnalyzer
from prep.regulatory.models import InsuranceRequirement, Regulation, RegulationSource
from prep.regulatory.scraper import RegulatoryScraper
from prep.settings import get_settings

router = APIRouter(prefix="/regulatory")

logger = logging.getLogger(__name__)

_ZIP_PATTERN = re.compile(r"\b\d{5}(?:-\d{4})?\b")

GRAPH_SERVICE_URL = os.getenv("GRAPH_SERVICE_URL")
POLICY_ENGINE_URL = os.getenv("POLICY_ENGINE_URL")
PROVENANCE_LEDGER_URL = os.getenv("PROVENANCE_LEDGER_URL")
ZK_PROOFS_URL = os.getenv("ZK_PROOFS_URL")


async def _service_request(
    method: str,
    base_url: str | None,
    path: str,
    *,
    json_body: Any | None = None,
    params: Dict[str, Any] | None = None,
    error_detail: str,
) -> Any | None:
    """Best-effort helper to talk to auxiliary services."""

    if not base_url:
        return None

    url = base_url.rstrip("/") + path
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.request(method, url, json=json_body, params=params)
            response.raise_for_status()
    except httpx.HTTPError as exc:  # pragma: no cover - network issues
        logger.exception("auxiliary service request failed", extra={"url": url})
        raise HTTPException(status_code=502, detail=error_detail) from exc

    if not response.content:
        return None
    return response.json()


class ScrapeRequest(BaseModel):
    """Request body for initiating a scraping job."""

    states: List[str]
    country_code: str = "US"
    cities: Optional[List[str]] = None
    force_refresh: bool = False


class ComplianceCheckRequest(BaseModel):
    """Request body for compliance checks."""

    kitchen_id: str
    state: str
    city: str
    country_code: str = "US"
    state_province: Optional[str] = None
    kitchen_data: Dict


@router.post("/scrape")
async def scrape_regulations(
    request: ScrapeRequest, background_tasks: BackgroundTasks
) -> Dict:
    """Trigger regulatory data scraping."""

    background_tasks.add_task(
        run_scraping_task,
        request.states,
        request.cities,
        request.country_code.upper(),
    )
    return {"status": "started", "message": f"Scraping regulations for {len(request.states)} states"}


@router.post("/compliance/check")
async def check_compliance(
    request: ComplianceCheckRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """Check kitchen compliance with regulations."""

    analyzer = RegulatoryAnalyzer()
    regulations = await get_regulations_for_jurisdiction(
        db,
        request.state,
        request.city,
        country_code=request.country_code.upper(),
        state_province=request.state_province,
    )
    kitchen_zip = request.kitchen_data.get("postal_code") or request.kitchen_data.get(
        "zip_code"
    )
    if not kitchen_zip:
        address = request.kitchen_data.get("address")
        if isinstance(address, str):
            match = _ZIP_PATTERN.search(address)
            if match:
                kitchen_zip = match.group(0)

    county = request.kitchen_data.get("county") or request.kitchen_data.get("county_name")
    pilot_mode = is_pilot_location(
        state=request.state,
        city=request.city,
        county=county,
        zip_code=kitchen_zip,
    )
    if pilot_mode:
        logger.debug(
            "Pilot mode enabled for regulatory compliance check",
            extra={
                "kitchen_id": request.kitchen_id,
                "zip_code": kitchen_zip,
                "county": county,
            },
        )

    analysis = await analyzer.analyze_kitchen_compliance(
        request.kitchen_data, regulations, pilot_mode=pilot_mode
    )

    settings = get_settings()
    banner: str | None = None
    if pilot_mode:
        banner = BOOKING_PILOT_BANNER
    elif settings.compliance_controls_enabled:
        banner = BOOKING_COMPLIANCE_BANNER
    if settings.compliance_controls_enabled:
        logger.info(
            "Compliance decision issued",
            extra={
                "kitchen_id": request.kitchen_id,
                "compliance_level": analysis.overall_compliance.value,
                "risk_score": analysis.risk_score,
            },
        )

    response = {
        "kitchen_id": request.kitchen_id,
        "compliance_level": analysis.overall_compliance.value,
        "risk_score": analysis.risk_score,
        "missing_requirements": analysis.missing_requirements,
        "recommendations": analysis.recommendations,
        "last_analyzed": analysis.last_analyzed.isoformat(),
        "pilot_mode": pilot_mode,
        "override_allowed": pilot_mode,
    }

    if banner:
        response["booking_restrictions_banner"] = banner

    return response


@router.get("/regulations/{state}")
async def get_regulations(
    state: str,
    city: Optional[str] = None,
    country_code: str = Query(default="US", min_length=2, max_length=2),
    state_province: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """Get regulations for a specific state/city."""

    regulations = await get_regulations_for_jurisdiction(
        db,
        state,
        city,
        country_code=country_code.upper(),
        state_province=state_province,
    )
    return {
        "state": state,
        "city": city,
        "state_province": state_province or state,
        "country_code": country_code.upper(),
        "regulations": regulations,
    }


@router.get("/insurance/{state}")
async def get_insurance_requirements(
    state: str,
    city: Optional[str] = None,
    country_code: str = Query(default="US", min_length=2, max_length=2),
    state_province: Optional[str] = Query(default=None),
) -> Dict:
    """Get insurance requirements for a state/city."""

    async with RegulatoryScraper() as scraper:
        requirements = await scraper.scrape_insurance_requirements(state)
    normalized_country = (country_code or "US").upper()
    province = state_province or state
    enriched_requirements = dict(requirements)
    enriched_requirements.setdefault("country_code", normalized_country)
    enriched_requirements.setdefault("state_province", province)

    return {
        "state": state,
        "city": city,
        "state_province": province,
        "country_code": normalized_country,
        "requirements": enriched_requirements,
    }


async def run_scraping_task(
    states: Iterable[str],
    cities: Optional[Iterable[Optional[str]]] = None,
    country_code: str = "US",
) -> None:
    """Background task for regulatory scraping."""

    async with RegulatoryScraper() as scraper:
        normalized_country = (country_code or "US").upper()
        for state in states:
            health_regs = await scraper.scrape_health_department(state)
            insurance_reqs = await scraper.scrape_insurance_requirements(state)

            target_cities: Iterable[Optional[str]] = cities or [None]
            for city in target_cities:
                zoning_regs = await scraper.scrape_zoning_regulations(city, state)
                async with AsyncSessionLocal() as session:
                    await save_regulations_to_db(
                        session,
                        health_regs + zoning_regs,
                        state,
                        city,
                        country_code=normalized_country,
                        state_province=state,
                    )
                    await save_insurance_requirements(
                        session,
                        insurance_reqs,
                        state,
                        city,
                        country_code=normalized_country,
                        state_province=state,
                    )


async def get_regulations_for_jurisdiction(
    db: AsyncSession,
    state: str,
    city: Optional[str] = None,
    *,
    country_code: str = "US",
    state_province: Optional[str] = None,
) -> List[Dict]:
    """Get regulations from database for a jurisdiction."""

    normalized_country = (country_code or "US").upper()
    province = state_province or state.upper()
    query = select(Regulation).where(
        Regulation.jurisdiction == (city or state),
        Regulation.country_code == normalized_country,
        Regulation.state_province == province,
    )
    result = await db.execute(query)
    regulations = result.scalars().all()
    return [
        {
            "id": str(regulation.id),
            "regulation_type": regulation.regulation_type,
            "title": regulation.title,
            "description": regulation.description,
            "requirements": regulation.requirements,
            "applicable_to": regulation.applicable_to,
            "jurisdiction": regulation.jurisdiction,
            "country_code": regulation.country_code,
            "state_province": regulation.state_province,
            "citation": regulation.citation,
        }
        for regulation in regulations
    ]


async def save_regulations_to_db(
    db: AsyncSession,
    regulations: List[Dict],
    state: str,
    city: Optional[str],
    *,
    country_code: str = "US",
    state_province: Optional[str] = None,
) -> None:
    """Persist regulation entries to the database."""

    if not regulations:
        return

    normalized_country = (country_code or "US").upper()
    state_code = state.upper()
    province = state_province or state_code

    for data in regulations:
        source_url = data.get("source_url") or "unknown"
        source_type = data.get("source_type")
        entry_country = (data.get("country_code") or normalized_country).upper()
        entry_province = data.get("state_province") or province
        source_query = select(RegulationSource).where(
            RegulationSource.country_code == entry_country,
            RegulationSource.state == state_code,
            RegulationSource.state_province == entry_province,
            RegulationSource.city == city,
            RegulationSource.source_url == source_url,
        )
        source_result = await db.execute(source_query)
        source = source_result.scalars().first()

        if not source:
            source = RegulationSource(
                country_code=entry_country,
                state=state_code,
                state_province=entry_province,
                city=city,
                source_url=source_url,
                source_type=source_type,
                last_scraped=datetime.utcnow(),
            )
            db.add(source)
            await db.flush()
        else:
            source.last_scraped = datetime.utcnow()

        regulation_query = select(Regulation).where(
            Regulation.source_id == source.id,
            Regulation.regulation_type == data.get("regulation_type"),
            Regulation.title == data.get("title"),
            Regulation.jurisdiction == data.get("jurisdiction"),
            Regulation.country_code == entry_country,
            Regulation.state_province == entry_province,
        )
        regulation_result = await db.execute(regulation_query)
        regulation = regulation_result.scalars().first()

        if regulation:
            regulation.description = data.get("description")
            regulation.requirements = data.get("requirements")
            regulation.applicable_to = data.get("applicable_to")
            regulation.effective_date = data.get("effective_date")
            regulation.expiration_date = data.get("expiration_date")
            regulation.citation = data.get("citation")
            regulation.country_code = entry_country
            regulation.state_province = entry_province
        else:
            regulation = Regulation(
                source_id=source.id,
                regulation_type=data.get("regulation_type"),
                title=data.get("title"),
                description=data.get("description"),
                requirements=data.get("requirements"),
                applicable_to=data.get("applicable_to"),
                effective_date=data.get("effective_date"),
                expiration_date=data.get("expiration_date"),
                jurisdiction=data.get("jurisdiction") or state,
                country_code=entry_country,
                state_province=entry_province,
                citation=data.get("citation"),
            )
            db.add(regulation)

    await db.commit()


async def save_insurance_requirements(
    db: AsyncSession,
    requirements: Dict,
    state: str,
    city: Optional[str],
    *,
    country_code: str = "US",
    state_province: Optional[str] = None,
) -> None:
    """Persist insurance requirements to the database."""

    country = (country_code or "US").upper()
    state_code = state.upper()
    province = state_province or state_code

    query = select(InsuranceRequirement).where(
        InsuranceRequirement.country_code == country,
        InsuranceRequirement.state == state_code,
        InsuranceRequirement.state_province == province,
        InsuranceRequirement.city == city,
    )
    result = await db.execute(query)
    record = result.scalars().first()

    if record:
        record.country_code = country
        record.state = state_code
        record.state_province = province
        record.minimum_coverage = requirements.get("minimum_coverage")
        record.required_policies = requirements.get("required_policies")
        record.special_requirements = requirements.get("special_requirements")
        record.notes = requirements.get("notes")
        record.source_url = requirements.get("source_url")
    else:
        record = InsuranceRequirement(
            country_code=country,
            state=state_code,
            state_province=province,
            city=city,
            minimum_coverage=requirements.get("minimum_coverage"),
            required_policies=requirements.get("required_policies"),
            special_requirements=requirements.get("special_requirements"),
            notes=requirements.get("notes"),
            source_url=requirements.get("source_url"),
        )
        db.add(record)

    await db.commit()


@router.get("/reg/obligations")
async def list_obligations(
    jurisdiction: str,
    subject: Optional[str] = None,
    type: Optional[str] = None,
) -> Dict[str, Any]:
    params = {"jurisdiction": jurisdiction}
    if subject:
        params["subject"] = subject
    if type:
        params["type"] = type

    response = await _service_request(
        "GET",
        GRAPH_SERVICE_URL,
        "/graph/obligations",
        params=params,
        error_detail="graph service unavailable",
    )

    if isinstance(response, list):
        obligations = response
    elif isinstance(response, dict) and "obligations" in response:
        obligations = response["obligations"]
    else:
        obligations = []

    return {"jurisdiction": jurisdiction, "obligations": obligations}


@router.post("/reg/evaluate")
async def evaluate_booking(payload: Dict[str, Any]) -> Dict[str, Any]:
    evaluation = await _service_request(
        "POST",
        POLICY_ENGINE_URL,
        "/evaluate",
        json_body=payload,
        error_detail="policy engine unavailable",
    )

    if not isinstance(evaluation, dict):
        evaluation = {
            "allowed": True,
            "violations": [],
            "proofs": [],
            "provenance_hash": "",
        }

    record_payload = {
        "type": "evaluation",
        "parent_hash": evaluation.get("provenance_hash"),
        "payload": evaluation,
    }
    await _service_request(
        "POST",
        PROVENANCE_LEDGER_URL,
        "/prov/record",
        json_body=record_payload,
        error_detail="provenance ledger unavailable",
    )

    return evaluation


@router.get("/reg/proof/{proof_id}")
async def get_proof(proof_id: str) -> Dict[str, Any]:
    record = await _service_request(
        "GET",
        PROVENANCE_LEDGER_URL,
        f"/prov/{proof_id}",
        error_detail="provenance ledger unavailable",
    )

    if not isinstance(record, dict):
        return {"proof_id": proof_id, "status": "unavailable"}
    return record


@router.get("/reg/provenance/{hash_value}")
async def get_provenance(hash_value: str) -> Dict[str, Any]:
    record = await _service_request(
        "GET",
        PROVENANCE_LEDGER_URL,
        f"/prov/{hash_value}",
        error_detail="provenance ledger unavailable",
    )

    if not isinstance(record, dict):
        return {"hash": hash_value, "status": "unknown"}
    return record


__all__ = [
    "router",
    "scrape_regulations",
    "check_compliance",
    "get_regulations",
    "get_insurance_requirements",
    "list_obligations",
    "evaluate_booking",
    "get_proof",
    "get_provenance",
]
