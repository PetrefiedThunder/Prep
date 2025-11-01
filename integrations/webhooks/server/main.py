from __future__ import annotations
import hmac, hashlib, time, os
from typing import Dict, Any
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

app = FastAPI(title="Prep Webhook Receiver", version="0.1.0")
WEBHOOK_SECRET = os.environ.get("PREP_WEBHOOK_SECRET", "changeme")
MAX_SKEW_SECONDS = int(os.environ.get("PREP_WEBHOOK_MAX_SKEW", "300"))

class Envelope(BaseModel):
    type: str
    id: str
    created_at: str
    data: Dict[str, Any]

def verify_signature(secret: str, body: bytes, signature_header: str | None) -> None:
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing Prep-Signature")
    try:
        parts = dict(kv.split("=", 1) for kv in signature_header.split(","))
        ts = int(parts.get("t", "0")); sig_v1 = parts.get("v1", "")
    except Exception:
        raise HTTPException(status_code=401, detail="Malformed Prep-Signature")
    now = int(time.time())
    if abs(now - ts) > MAX_SKEW_SECONDS:
        raise HTTPException(status_code=401, detail="Signature timestamp skew too large")
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig_v1):
        raise HTTPException(status_code=401, detail="Invalid signature")

@app.post("/webhooks/prep")
async def receive_prep_webhook(
    request: Request,
    prep_event: str | None = Header(default=None, alias="Prep-Event"),
    prep_event_id: str | None = Header(default=None, alias="Prep-Event-Id"),
    prep_signature: str | None = Header(default=None, alias="Prep-Signature"),
):
    raw = await request.body()
    verify_signature(WEBHOOK_SECRET, raw, prep_signature)
    try:
        env = Envelope.model_validate_json(raw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")
    if env.type == "fees.updated":
        pass
    elif env.type == "requirements.updated":
        pass
    elif env.type == "policy.decision":
        pass
    return {"ok": True, "id": prep_event_id or env.id, "type": prep_event or env.type}
