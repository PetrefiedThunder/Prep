"""API routes for relationship extraction."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ...parser import extract_relationships_from_akn
from ...store.akn_repo import AKNRepo

router = APIRouter()


async def get_repo() -> AKNRepo | None:
    """Resolve the configured AKN repository instance."""

    return None


@router.get("/extract")
async def extract(eli: str = Query(..., description="Source document ELI")) -> dict:
    repo = await get_repo()
    if repo is None:
        raise HTTPException(status_code=501, detail="AKN repository not configured")
    xml = repo.get_xml(eli)
    relationships = extract_relationships_from_akn(eli, xml, jurisdiction_hint="eu")
    return {
        "eli": eli,
        "count": len(relationships),
        "rels": [r.__dict__ for r in relationships],
    }


__all__ = ["router"]
