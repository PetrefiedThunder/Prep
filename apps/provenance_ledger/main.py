"""Provenance ledger API."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Provenance Ledger")


def _store() -> dict[str, dict[str, Any]]:
    if not hasattr(app.state, "records"):
        app.state.records = {}
    return app.state.records


class Record(BaseModel):
    type: str
    parent_hash: str | None = None
    payload: dict[str, Any]


@app.post("/prov/record")
def record(item: Record) -> dict[str, str]:
    payload_bytes = json.dumps(item.payload, sort_keys=True).encode("utf-8")
    hash_value = hashlib.sha256(payload_bytes).hexdigest()
    _store()[hash_value] = {"item": item.model_dump(), "hash": hash_value}
    return {"hash": hash_value}


@app.get("/prov/{hash_value}")
def fetch(hash_value: str) -> dict[str, Any]:
    try:
        return _store()[hash_value]
    except KeyError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=404, detail="record not found") from exc


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def ready() -> dict[str, str]:
    return {"status": "ready"}
