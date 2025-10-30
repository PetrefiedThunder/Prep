"""FastAPI router exposing GAAP ledger operations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database import get_db

from .schemas import LedgerExportFormat
from .service import GAAPLedgerService

router = APIRouter(prefix="/ledger", tags=["ledger"])


async def get_ledger_service(session: AsyncSession = Depends(get_db)) -> GAAPLedgerService:
    """Dependency factory that provisions the GAAP ledger service."""

    return GAAPLedgerService(session)


@router.get("/export", summary="Export the GAAP ledger")
async def export_ledger(
    format: LedgerExportFormat = Query(default=LedgerExportFormat.JSON),
    service: GAAPLedgerService = Depends(get_ledger_service),
) -> Response:
    """Return the ledger in JSON or CSV form."""

    try:
        export = await service.export_ledger(format=format)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    media_type = "application/json" if export.format is LedgerExportFormat.JSON else "text/csv"
    return Response(content=export.content, media_type=media_type)


__all__ = ["router", "get_ledger_service"]
