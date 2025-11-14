"""FastAPI application that receives Prep webhook events."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from collections.abc import Generator

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from prometheus_client import Counter
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

LOGGER = logging.getLogger("prep.integrations.webhooks")
logging.basicConfig(level=logging.INFO)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./webhooks.db")
SECRET_ENV_NAME = "PREP_WEBHOOK_SECRET"

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
Base = declarative_base()


class Envelope(Base):
    """SQLAlchemy model storing webhook envelopes."""

    __tablename__ = "envelopes"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(255), nullable=True)
    signature = Column(String(256), nullable=False)
    payload = Column(Text, nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


Base.metadata.create_all(bind=engine)

ACK_COUNTER = Counter(
    "prep_webhook_envelopes_ack_total",
    "Number of Prep webhook envelopes acknowledged.",
)
DUP_COUNTER = Counter(
    "prep_webhook_envelopes_duplicate_total",
    "Number of duplicate Prep webhook envelopes ignored.",
)

app = FastAPI(title="Prep Webhook Receiver", version="1.0.0")


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session tied to the current request."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _load_secret() -> str:
    try:
        secret = os.environ[SECRET_ENV_NAME]
    except KeyError as exc:  # pragma: no cover - misconfiguration guard
        LOGGER.error("Webhook secret environment variable %s not set", SECRET_ENV_NAME)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured.",
        ) from exc

    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured.",
        )

    return secret


def _normalize_signature(signature: str) -> str:
    if signature.startswith("sha256="):
        return signature.split("=", 1)[1]
    return signature


def _verify_signature(*, payload: bytes, provided_signature: str) -> None:
    secret = _load_secret()
    normalized_signature = _normalize_signature(provided_signature)
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(digest, normalized_signature):
        LOGGER.warning("Invalid webhook signature received.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")


@app.post("/webhooks/prep")
async def handle_prep_webhook(
    request: Request,
    x_prep_signature: str = Header(..., alias="X-Prep-Signature"),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Handle Prep webhook callbacks."""

    payload_bytes = await request.body()
    _verify_signature(payload=payload_bytes, provided_signature=x_prep_signature)

    try:
        payload_text = payload_bytes.decode("utf-8")
        payload_json = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        LOGGER.warning("Webhook payload is not valid JSON: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    event_id = payload_json.get("event_id")
    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing event_id"
        )

    envelope = Envelope(
        event_id=str(event_id),
        event_type=payload_json.get("event_type"),
        signature=_normalize_signature(x_prep_signature),
        payload=payload_text,
    )

    try:
        db.add(envelope)
        db.commit()
    except IntegrityError:
        db.rollback()
        DUP_COUNTER.inc()
        LOGGER.info("Duplicate webhook ignored (event_id=%s)", envelope.event_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "accepted", "event_id": envelope.event_id, "duplicate": True},
        )
    except Exception:  # pragma: no cover - unexpected persistence issue
        db.rollback()
        LOGGER.exception("Failed to persist webhook envelope (event_id=%s)", envelope.event_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to persist envelope"
        )

    ACK_COUNTER.inc()
    LOGGER.info(
        "Webhook acknowledged (event_id=%s, event_type=%s)", envelope.event_id, envelope.event_type
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "accepted", "event_id": envelope.event_id},
    )
