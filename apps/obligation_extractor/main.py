"""Obligation extraction service."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Obligation Extractor")


class ExtractRequest(BaseModel):
    doc_id: str
    jurisdiction: str
    sections: list[dict[str, Any]]


@app.post("/extract")
def extract_obligations(req: ExtractRequest) -> list[dict[str, Any]]:
    """Extract obligations from a normalized document."""

    _ = req
    return []


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def ready() -> dict[str, str]:
    return {"status": "ready"}
