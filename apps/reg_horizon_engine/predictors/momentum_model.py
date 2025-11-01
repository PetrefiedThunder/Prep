"""Predictive models used by the Regulatory Horizon Engine."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import BaseModel


class PredictionResult(BaseModel):
    """Model output describing expected passage probability and timeline."""

    relevance: float
    prob_pass: float
    eta_enactment: date | None
    summary: str


@dataclass
class MomentumModel:
    """Wrapper around the core momentum and passage probability model."""

    model_path: str | None = None

    async def predict(self, features: dict[str, Any]) -> PredictionResult:
        """Generate a prediction from structured features."""

        _ = (features,)
        return PredictionResult(
            relevance=0.5,
            prob_pass=0.5,
            eta_enactment=None,
            summary="Model scaffolding pending training pipeline integration.",
        )

    async def backfill(self, session, *, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist the prediction in the database for downstream use."""

        record = {
            "municipality_id": payload.get("municipality_id", "unknown"),
            "bill_id": payload.get("bill_id"),
            "status": payload.get("status", "predicted"),
            "relevance": payload.get("relevance", 0.0),
            "prob_pass": payload.get("prob_pass", 0.0),
            "eta_enactment": payload.get("eta_enactment"),
            "summary": payload.get("summary", ""),
            "change_diff": payload.get("change_diff", {}),
        }
        if hasattr(session, "execute"):
            from sqlalchemy import insert

            from ..models import RHEPrediction

            await session.execute(insert(RHEPrediction).values(record))
        return record
