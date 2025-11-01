"""API routes for the Regulatory Horizon Engine."""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, HttpUrl

from ..database import session_scope
from ..finders.agent_service import FinderAgent, PortalCandidate, record_candidates
from ..parsers.extract_pipeline import ExtractedDocument, ParserPipeline
from ..predictors.momentum_model import MomentumModel, PredictionResult
from reg_horizon_engine.api.routes.relationships import router as relationships_router

router = APIRouter()


class SourceDiscoveryRequest(BaseModel):
    municipality_id: str
    topic: str


class SourceDiscoveryResponse(BaseModel):
    sources: list[PortalCandidate]


class DocumentIngestRequest(BaseModel):
    source_id: str
    municipality_id: str
    document_url: HttpUrl


class DocumentIngestResponse(BaseModel):
    document: ExtractedDocument


class PredictionRequest(BaseModel):
    municipality_id: str
    bill_id: str | None = None
    features: dict[str, Any] = Field(default_factory=dict)


class PredictionResponse(BaseModel):
    prediction: PredictionResult


async def get_finder_agent() -> FinderAgent:
    return FinderAgent(search_backends=("brave", "serpapi"))


async def get_parser_pipeline() -> ParserPipeline:
    return ParserPipeline(storage_bucket=None)


async def get_momentum_model() -> MomentumModel:
    return MomentumModel(model_path=None)


@router.post("/sources/discover", response_model=SourceDiscoveryResponse)
async def discover_sources(
    payload: SourceDiscoveryRequest,
    agent: FinderAgent = Depends(get_finder_agent),
) -> SourceDiscoveryResponse:
    candidates = await agent.discover(payload.municipality_id, payload.topic)
    verified = await agent.verify(candidates)
    async with session_scope() as session:
        await record_candidates(session, verified)
    return SourceDiscoveryResponse(sources=verified)


@router.post("/documents/ingest", response_model=DocumentIngestResponse)
async def ingest_document(
    payload: DocumentIngestRequest,
    parser: ParserPipeline = Depends(get_parser_pipeline),
) -> DocumentIngestResponse:
    document = await parser.extract_document(payload.document_url)
    async with session_scope() as session:
        await parser.persist(
            session,
            document,
            metadata={
                "source_id": payload.source_id,
                "municipality_id": payload.municipality_id,
            },
        )
    return DocumentIngestResponse(document=document)


@router.post("/predictions", response_model=PredictionResponse)
async def create_prediction(
    payload: PredictionRequest,
    model: MomentumModel = Depends(get_momentum_model),
) -> PredictionResponse:
    prediction = await model.predict(payload.features)
    async with session_scope() as session:
        await model.backfill(
            session,
            payload={
                "municipality_id": payload.municipality_id,
                "bill_id": payload.bill_id,
                "status": "predicted",
                "relevance": prediction.relevance,
                "prob_pass": prediction.prob_pass,
                "eta_enactment": prediction.eta_enactment
                if isinstance(prediction.eta_enactment, date)
                else None,
                "summary": prediction.summary,
                "change_diff": {},
            },
        )
    return PredictionResponse(prediction=prediction)


router.include_router(relationships_router, prefix="/relationships", tags=["lkg"])
