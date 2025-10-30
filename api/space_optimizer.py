"""FastAPI router exposing the space optimizer prediction endpoint."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.bookings import BookingHistoryRepository
from apps.logistics import DeliveryLogRepository
from modules.ml.space_optimizer import SpaceOptimizerDataPipeline, SpaceOptimizerModel

router = APIRouter(prefix="/space-optimizer", tags=["space-optimizer"])
_MODEL_PATH = Path("modules/ml/space_optimizer/model_state.json")
_pipeline = SpaceOptimizerDataPipeline(
    booking_repo=BookingHistoryRepository(), logistics_repo=DeliveryLogRepository()
)
_model_cache: SpaceOptimizerModel | None = None


class PredictionWindow(BaseModel):
    kitchen_id: str = Field(..., description="Kitchen identifier")
    window_start: datetime = Field(..., description="Candidate idle window start time")
    window_end: datetime = Field(..., description="Candidate idle window end time")

    def ensure_valid(self) -> None:
        if self.window_end <= self.window_start:
            raise HTTPException(status_code=400, detail="window_end must be after window_start")


class PredictionResponse(BaseModel):
    kitchen_id: str
    probability: float
    is_idle_window: bool
    features: dict[str, float]


class PredictionRequest(BaseModel):
    windows: List[PredictionWindow]

    def ensure_non_empty(self) -> None:
        if not self.windows:
            raise HTTPException(status_code=400, detail="At least one window must be provided")
        for window in self.windows:
            window.ensure_valid()


def _load_model() -> SpaceOptimizerModel:
    global _model_cache
    if _model_cache is not None:
        return _model_cache

    if _MODEL_PATH.exists():
        _model_cache = SpaceOptimizerModel.load(_MODEL_PATH)
        return _model_cache

    training_set = _pipeline.prepare_training_data()
    model = SpaceOptimizerModel()
    model.fit(training_set.features, training_set.labels)
    model.save(_MODEL_PATH)
    _model_cache = model
    return model


@router.post("/predict", response_model=List[PredictionResponse])
def predict_idle_windows(request: PredictionRequest) -> List[PredictionResponse]:
    """Return idle window probabilities for the provided windows."""

    request.ensure_non_empty()
    model = _load_model()

    responses: List[PredictionResponse] = []
    for window in request.windows:
        features = _pipeline.build_features_for_window(
            kitchen_id=window.kitchen_id,
            window_start=window.window_start,
            window_end=window.window_end,
        )
        probability = model.predict_proba([features])[0]
        feature_map = {name: float(value) for name, value in zip(_pipeline.feature_names, features)}
        responses.append(
            PredictionResponse(
                kitchen_id=window.kitchen_id,
                probability=probability,
                is_idle_window=probability >= 0.5,
                features=feature_map,
            )
        )

    return responses


__all__ = ["router"]
