"""ZK proof service stubs."""
from __future__ import annotations

import base64
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="ZK Proofs Service")


class InsuranceClaim(BaseModel):
    threshold: int
    proof_blob: bytes


@app.post("/zk/prove")
def prove_insurance(policy_pdf_b64: str, threshold: int) -> dict[str, Any]:
    """Mock proof generation by hashing the inputs."""

    decoded = base64.b64decode(policy_pdf_b64)
    _ = decoded, threshold
    return {"proof_blob": base64.b64encode(b"proof").decode("utf-8")}


@app.post("/zk/verify")
def verify_insurance(claim: InsuranceClaim) -> dict[str, bool]:
    """Mock verification that always succeeds."""

    _ = claim
    return {"valid": True}


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def ready() -> dict[str, str]:
    return {"status": "ready"}
