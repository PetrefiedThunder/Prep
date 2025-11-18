#!/usr/bin/env python3
"""
Mock Stripe API Server

A lightweight mock implementation of Stripe API for local development and testing.
Implements key endpoints needed for Prep platform.

Run with: python mocks/stripe_mock.py
"""

import os
import secrets
import time
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

app = FastAPI(title="Mock Stripe API", version="1.0.0")

# In-memory storage
ACCOUNTS: dict[str, dict[str, Any]] = {}
PAYMENT_INTENTS: dict[str, dict[str, Any]] = {}
TRANSFERS: dict[str, dict[str, Any]] = {}
WEBHOOKS: list[dict[str, Any]] = []


# Models
class CreateAccountRequest(BaseModel):
    type: str
    country: str
    email: str
    business_type: str = None
    metadata: dict[str, str] = {}


class CreatePaymentIntentRequest(BaseModel):
    amount: int
    currency: str
    application_fee_amount: int = None
    transfer_data: dict[str, str] = None
    metadata: dict[str, str] = {}
    description: str = None
    statement_descriptor: str = None


class CreateTransferRequest(BaseModel):
    amount: int
    currency: str
    destination: str
    metadata: dict[str, str] = {}


# Helper functions
def generate_id(prefix: str) -> str:
    """Generate a Stripe-like ID"""
    return f"{prefix}_{secrets.token_urlsafe(16)}"


def create_timestamp() -> int:
    """Get current Unix timestamp"""
    return int(time.time())


# Endpoints
@app.get("/")
async def root():
    """API root - return mock Stripe info"""
    return {
        "object": "mock_stripe_api",
        "version": "2023-10-16",
        "mock": True,
        "message": "This is a mock Stripe API for local development",
    }


@app.post("/v1/accounts")
async def create_account(
    request: CreateAccountRequest,
    authorization: str = Header(None),
):
    """Create a Connect account"""

    if not authorization or not authorization.startswith("Bearer sk_test_"):
        raise HTTPException(status_code=401, detail="Invalid API key")

    account_id = generate_id("acct")
    account = {
        "id": account_id,
        "object": "account",
        "type": request.type,
        "country": request.country,
        "email": request.email,
        "business_type": request.business_type,
        "metadata": request.metadata,
        "created": create_timestamp(),
        "charges_enabled": True,
        "payouts_enabled": True,
        "details_submitted": True,
    }

    ACCOUNTS[account_id] = account
    return account


@app.get("/v1/accounts/{account_id}")
async def get_account(
    account_id: str,
    authorization: str = Header(None),
):
    """Get account details"""

    if account_id not in ACCOUNTS:
        raise HTTPException(status_code=404, detail="No such account")

    return ACCOUNTS[account_id]


@app.post("/v1/payment_intents")
async def create_payment_intent(
    request: CreatePaymentIntentRequest,
    authorization: str = Header(None),
):
    """Create a payment intent"""

    if not authorization or not authorization.startswith("Bearer sk_test_"):
        raise HTTPException(status_code=401, detail="Invalid API key")

    intent_id = generate_id("pi")
    client_secret = f"{intent_id}_secret_{secrets.token_urlsafe(16)}"

    intent = {
        "id": intent_id,
        "object": "payment_intent",
        "amount": request.amount,
        "currency": request.currency,
        "status": "requires_payment_method",
        "client_secret": client_secret,
        "created": create_timestamp(),
        "metadata": request.metadata,
        "description": request.description,
        "statement_descriptor": request.statement_descriptor,
        "application_fee_amount": request.application_fee_amount,
        "transfer_data": request.transfer_data,
        "next_action": None,
        "payment_method": None,
        "charges": {"object": "list", "data": [], "has_more": False},
    }

    PAYMENT_INTENTS[intent_id] = intent
    return intent


@app.post("/v1/payment_intents/{intent_id}/confirm")
async def confirm_payment_intent(
    intent_id: str,
    authorization: str = Header(None),
):
    """Confirm a payment intent (simulate successful payment)"""

    if intent_id not in PAYMENT_INTENTS:
        raise HTTPException(status_code=404, detail="No such payment intent")

    intent = PAYMENT_INTENTS[intent_id]
    intent["status"] = "succeeded"
    intent["payment_method"] = generate_id("pm")
    intent["charges"]["data"] = [
        {
            "id": generate_id("ch"),
            "object": "charge",
            "amount": intent["amount"],
            "currency": intent["currency"],
            "status": "succeeded",
            "paid": True,
            "created": create_timestamp(),
        }
    ]

    # Create transfer if transfer_data exists
    if intent.get("transfer_data"):
        transfer_id = generate_id("tr")
        transfer = {
            "id": transfer_id,
            "object": "transfer",
            "amount": intent["amount"] - (intent.get("application_fee_amount", 0) or 0),
            "currency": intent["currency"],
            "destination": intent["transfer_data"]["destination"],
            "created": create_timestamp(),
            "metadata": intent["metadata"],
        }
        TRANSFERS[transfer_id] = transfer

    # Trigger webhook
    _trigger_webhook("payment_intent.succeeded", intent)

    return intent


@app.get("/v1/payment_intents/{intent_id}")
async def get_payment_intent(
    intent_id: str,
    authorization: str = Header(None),
):
    """Get payment intent details"""

    if intent_id not in PAYMENT_INTENTS:
        raise HTTPException(status_code=404, detail="No such payment intent")

    return PAYMENT_INTENTS[intent_id]


@app.post("/v1/transfers")
async def create_transfer(
    request: CreateTransferRequest,
    authorization: str = Header(None),
):
    """Create a transfer to Connect account"""

    if not authorization or not authorization.startswith("Bearer sk_test_"):
        raise HTTPException(status_code=401, detail="Invalid API key")

    if request.destination not in ACCOUNTS:
        raise HTTPException(status_code=400, detail="Invalid destination account")

    transfer_id = generate_id("tr")
    transfer = {
        "id": transfer_id,
        "object": "transfer",
        "amount": request.amount,
        "currency": request.currency,
        "destination": request.destination,
        "metadata": request.metadata,
        "created": create_timestamp(),
        "reversed": False,
    }

    TRANSFERS[transfer_id] = transfer

    # Trigger webhook
    _trigger_webhook("transfer.created", transfer)

    return transfer


@app.get("/v1/transfers/{transfer_id}")
async def get_transfer(
    transfer_id: str,
    authorization: str = Header(None),
):
    """Get transfer details"""

    if transfer_id not in TRANSFERS:
        raise HTTPException(status_code=404, detail="No such transfer")

    return TRANSFERS[transfer_id]


@app.get("/v1/balance_transactions")
async def list_balance_transactions(
    created: str = None,
    authorization: str = Header(None),
):
    """List balance transactions (simplified)"""

    # Return mock transactions based on payment intents
    transactions = []
    for intent in PAYMENT_INTENTS.values():
        if intent["status"] == "succeeded":
            transactions.append(
                {
                    "id": generate_id("txn"),
                    "object": "balance_transaction",
                    "amount": intent["amount"],
                    "currency": intent["currency"],
                    "type": "charge",
                    "source": intent["charges"]["data"][0]["id"]
                    if intent["charges"]["data"]
                    else None,
                    "created": intent["created"],
                }
            )

    return {"object": "list", "data": transactions, "has_more": False}


@app.post("/v1/webhook_endpoints")
async def register_webhook(request: Request, authorization: str = Header(None)):
    """Register a webhook endpoint"""

    data = await request.json()
    webhook_id = generate_id("we")

    webhook = {
        "id": webhook_id,
        "object": "webhook_endpoint",
        "url": data.get("url"),
        "enabled_events": data.get("enabled_events", ["*"]),
        "created": create_timestamp(),
    }

    return webhook


# Internal webhook helper
def _trigger_webhook(event_type: str, data: dict[str, Any]):
    """Simulate webhook delivery"""

    event = {
        "id": generate_id("evt"),
        "object": "event",
        "type": event_type,
        "created": create_timestamp(),
        "data": {"object": data},
    }

    WEBHOOKS.append(event)

    # In a real implementation, we'd POST to registered webhook URLs
    # For now, just log it
    print(f"📤 Webhook triggered: {event_type}")


# Debug endpoints
@app.get("/debug/accounts")
async def debug_accounts():
    """Get all accounts (debug only)"""
    return {"accounts": list(ACCOUNTS.values())}


@app.get("/debug/payment_intents")
async def debug_payment_intents():
    """Get all payment intents (debug only)"""
    return {"payment_intents": list(PAYMENT_INTENTS.values())}


@app.get("/debug/transfers")
async def debug_transfers():
    """Get all transfers (debug only)"""
    return {"transfers": list(TRANSFERS.values())}


@app.get("/debug/webhooks")
async def debug_webhooks():
    """Get all webhooks (debug only)"""
    return {"webhooks": WEBHOOKS}


@app.delete("/debug/reset")
async def debug_reset():
    """Reset all data (debug only)"""
    ACCOUNTS.clear()
    PAYMENT_INTENTS.clear()
    TRANSFERS.clear()
    WEBHOOKS.clear()
    return {"status": "reset complete"}


if __name__ == "__main__":
    import uvicorn

    print("🎭 Starting Mock Stripe API Server...")
    print("📍 Listening on http://localhost:8001")
    print("🔑 Use any API key starting with 'sk_test_'")
    print("🐛 Debug endpoints available at /debug/*")

    # Bind to localhost by default for security; allow override via environment variable
    host = os.getenv("BIND_HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=8001)
