"""Monitoring service stubs."""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Monitor Service")


@app.get("/monitor/status")
def status() -> dict[str, str]:
    return {"status": "idle"}


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def ready() -> dict[str, str]:
    return {"status": "ready"}
