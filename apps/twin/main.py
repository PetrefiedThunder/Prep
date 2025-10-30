"""Digital twin simulation service."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Digital Twin Service")


class TwinInput(BaseModel):
    obligations: list[dict[str, Any]]
    workflow: dict[str, Any]


@app.post("/simulate")
def simulate(inp: TwinInput) -> dict[str, Any]:
    _ = inp
    return {
        "time_to_compliance": 0,
        "affected_steps": [],
        "expected_violation_rate": 0.0,
    }


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def ready() -> dict[str, str]:
    return {"status": "ready"}
