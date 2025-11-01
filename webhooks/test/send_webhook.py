"""Utility script to send signed webhook payloads to the local server."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from typing import Any, Dict

import requests

from webhooks.server.main import SIGNATURE_HEADER, compute_signature

DEFAULT_EVENT = "fees.updated"
EVENT_PATHS = {
    "fees.updated": "/webhooks/fees.updated",
    "requirements.updated": "/webhooks/requirements.updated",
    "policy.decision": "/webhooks/policy.decision",
}


def build_sample_payload(event_type: str) -> Dict[str, Any]:
    """Return a minimal payload for the provided event."""

    data = {
        "fees.updated": {"application_id": "app_123", "total_due": "120.50"},
        "requirements.updated": {
            "application_id": "app_456",
            "missing_documents": ["proof_of_identity", "financial_statement"],
        },
        "policy.decision": {"application_id": "app_789", "decision": "approved"},
    }
    return {"id": str(uuid.uuid4()), "type": event_type, "data": data[event_type]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a signed Prep webhook event")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL for the webhook server (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--event",
        choices=sorted(EVENT_PATHS.keys()),
        default=DEFAULT_EVENT,
        help="Webhook event type to send",
    )
    parser.add_argument(
        "--payload",
        help="Path to a JSON file containing the payload to send. Defaults to a generated sample payload.",
    )
    parser.add_argument(
        "--secret",
        default=os.getenv("PREP_WEBHOOK_SECRET"),
        help="Webhook signing secret. Defaults to the PREP_WEBHOOK_SECRET environment variable.",
    )
    parser.add_argument(
        "--timestamp",
        type=int,
        default=None,
        help="Override the timestamp used when signing the request.",
    )
    return parser.parse_args()


def load_payload(path: str | None, event_type: str) -> Dict[str, Any]:
    if not path:
        return build_sample_payload(event_type)

    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if payload.get("type") != event_type:
        raise ValueError("Payload type does not match the selected event")
    return payload


def main() -> int:
    args = parse_args()

    if not args.secret:
        print("Webhook secret must be provided via --secret or PREP_WEBHOOK_SECRET", file=sys.stderr)
        return 1

    payload = load_payload(args.payload, args.event)
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    timestamp = str(args.timestamp or int(time.time()))
    signature = compute_signature(args.secret, timestamp, body)
    signature_header = f"t={timestamp},v1={signature}"

    url = args.url.rstrip("/") + EVENT_PATHS[args.event]
    response = requests.post(
        url,
        data=body,
        headers={
            "content-type": "application/json",
            SIGNATURE_HEADER: signature_header,
        },
        timeout=10,
    )
    print(f"Response status: {response.status_code}")
    print(response.text)
    return 0 if response.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
