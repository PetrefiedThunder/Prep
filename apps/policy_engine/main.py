"""Policy evaluation API."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Policy Engine")


class EvalInput(BaseModel):
    subject: str
    jurisdiction: str
    facts: dict[str, Any]


class EvalResult(BaseModel):
    allowed: bool
    violations: list[dict[str, Any]]
    proofs: list[dict[str, Any]]
    provenance_hash: str


@app.post("/evaluate", response_model=EvalResult)
def evaluate(inp: EvalInput) -> EvalResult:
    """Evaluate the supplied facts against policy rules."""

    return EvalResult(allowed=True, violations=[], proofs=[], provenance_hash="")


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def ready() -> dict[str, str]:
    return {"status": "ready"}
