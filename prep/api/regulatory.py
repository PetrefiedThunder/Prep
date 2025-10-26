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
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return regulations for the provided jurisdiction."""

    regulations = await get_regulations_for_jurisdiction(db, state, city)
    return {"regulations": regulations}
"""FastAPI endpoints for regulatory data and compliance analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database.connection import AsyncSessionLocal, get_db
from prep.regulatory.analyzer import RegulatoryAnalyzer
from prep.regulatory.models import InsuranceRequirement, Regulation, RegulationSource
from prep.regulatory.scraper import RegulatoryScraper

router = APIRouter(prefix="/regulatory")


class ScrapeRequest(BaseModel):
    """Request body for initiating a scraping job."""

    states: List[str]
    cities: Optional[List[str]] = None
    force_refresh: bool = False


class ComplianceCheckRequest(BaseModel):
    """Request body for compliance checks."""

    kitchen_id: str
    state: str
    city: str
    kitchen_data: Dict


@router.post("/scrape")
async def scrape_regulations(
    request: ScrapeRequest, background_tasks: BackgroundTasks
) -> Dict:
    """Trigger regulatory data scraping."""

    background_tasks.add_task(run_scraping_task, request.states, request.cities)
    return {"status": "started", "message": f"Scraping regulations for {len(request.states)} states"}


@router.post("/compliance/check")
async def check_compliance(
    request: ComplianceCheckRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """Check kitchen compliance with regulations."""

    analyzer = RegulatoryAnalyzer()
    regulations = await get_regulations_for_jurisdiction(db, request.state, request.city)
    analysis = await analyzer.analyze_kitchen_compliance(request.kitchen_data, regulations)

    return {
        "kitchen_id": request.kitchen_id,
        "compliance_level": analysis.overall_compliance.value,
        "risk_score": analysis.risk_score,
        "missing_requirements": analysis.missing_requirements,
        "recommendations": analysis.recommendations,
        "last_analyzed": analysis.last_analyzed.isoformat(),
    }


@router.get("/regulations/{state}")
async def get_regulations(
    state: str,
    city: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """Get regulations for a specific state/city."""

    regulations = await get_regulations_for_jurisdiction(db, state, city)
    return {"state": state, "city": city, "regulations": regulations}


@router.get("/insurance/{state}")
async def get_insurance_requirements(state: str, city: Optional[str] = None) -> Dict:
    """Get insurance requirements for a state/city."""

    async with RegulatoryScraper() as scraper:
        requirements = await scraper.scrape_insurance_requirements(state)

    return {"state": state, "city": city, "requirements": requirements}


async def run_scraping_task(
    states: Iterable[str], cities: Optional[Iterable[Optional[str]]] = None
) -> None:
    """Background task for regulatory scraping."""

    async with RegulatoryScraper() as scraper:
        for state in states:
            health_regs = await scraper.scrape_health_department(state)
            insurance_reqs = await scraper.scrape_insurance_requirements(state)

            target_cities: Iterable[Optional[str]] = cities or [None]
            for city in target_cities:
                zoning_regs = await scraper.scrape_zoning_regulations(city, state)
                async with AsyncSessionLocal() as session:
                    await save_regulations_to_db(session, health_regs + zoning_regs, state, city)
                    await save_insurance_requirements(session, insurance_reqs, state, city)


async def get_regulations_for_jurisdiction(
    db: AsyncSession, state: str, city: Optional[str] = None
) -> List[Dict]:
    """Get regulations from database for a jurisdiction."""

    query = select(Regulation).where(Regulation.jurisdiction == (city or state))
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
            "citation": regulation.citation,
        }
        for regulation in regulations
    ]


async def save_regulations_to_db(
    db: AsyncSession, regulations: List[Dict], state: str, city: Optional[str]
) -> None:
    """Persist regulation entries to the database."""

    if not regulations:
        return

    for data in regulations:
        source_url = data.get("source_url") or "unknown"
        source_type = data.get("source_type")
        source_query = select(RegulationSource).where(
            RegulationSource.state == state,
            RegulationSource.city == city,
            RegulationSource.source_url == source_url,
        )
        source_result = await db.execute(source_query)
        source = source_result.scalars().first()

        if not source:
            source = RegulationSource(
                state=state,
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
                citation=data.get("citation"),
            )
            db.add(regulation)

    await db.commit()


async def save_insurance_requirements(
    db: AsyncSession, requirements: Dict, state: str, city: Optional[str]
) -> None:
    """Persist insurance requirements to the database."""

    query = select(InsuranceRequirement).where(
        InsuranceRequirement.state == state,
        InsuranceRequirement.city == city,
    )
    result = await db.execute(query)
    record = result.scalars().first()

    if record:
        record.minimum_coverage = requirements.get("minimum_coverage")
        record.required_policies = requirements.get("required_policies")
        record.special_requirements = requirements.get("special_requirements")
        record.notes = requirements.get("notes")
        record.source_url = requirements.get("source_url")
    else:
        record = InsuranceRequirement(
            state=state,
            city=city,
            minimum_coverage=requirements.get("minimum_coverage"),
            required_policies=requirements.get("required_policies"),
            special_requirements=requirements.get("special_requirements"),
            notes=requirements.get("notes"),
            source_url=requirements.get("source_url"),
        )
        db.add(record)

    await db.commit()


__all__ = [
    "router",
    "scrape_regulations",
    "check_compliance",
    "get_regulations",
    "get_insurance_requirements",
]
