"""Ingestion service API stubs."""
from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

app = FastAPI(title="Ingestion Service")


class Source(BaseModel):
    """Definition for an ingestion source."""

    id: str
    name: str
    jurisdiction: str
    type: Literal["html", "pdf", "rss", "api"]
    url: HttpUrl
    cadence_cron: str


def _registry() -> dict[str, Source]:
    if not hasattr(app.state, "sources"):
        app.state.sources = {}
    return app.state.sources


@app.post("/sources", response_model=Source)
def register_source(src: Source) -> Source:
    """Register or replace a source definition."""

    sources = _registry()
    sources[src.id] = src
    return src


@app.get("/sources", response_model=list[Source])
def list_sources() -> list[Source]:
    """Return all registered sources."""

    return list(_registry().values())


@app.get("/sources/{source_id}", response_model=Source)
def get_source(source_id: str) -> Source:
    """Fetch a specific source by identifier."""

    try:
        return _registry()[source_id]
    except KeyError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=404, detail="source not found") from exc


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def ready() -> dict[str, str]:
    return {"status": "ready"}
