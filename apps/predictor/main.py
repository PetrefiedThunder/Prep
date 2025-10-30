"""Predictor service stubs."""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Predictor Service")


class PredictRequest(BaseModel):
    jurisdiction: str
    topic: str


@app.post("/predict")
def predict_change(req: PredictRequest) -> dict[str, float]:
    _ = req
    return {"horizon_months": 6.0, "likelihood": 0.5}


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def ready() -> dict[str, str]:
    return {"status": "ready"}
