"""Utility for exercising the local Prep webhook receiver."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from http import HTTPStatus
from typing import Any

import httpx

DEFAULT_EVENT = {
    "type": "fees.updated",
    "data": {
        "city": "san-francisco",
        "state": "CA",
        "fee": "2024 health permit renewal",
    },
}


def _build_signature(secret: str, timestamp: int, payload: str) -> str:
    message = f"{timestamp}.".encode("utf-8") + payload.encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _parse_payload(path: str | None) -> dict[str, Any]:
    if not path:
        return DEFAULT_EVENT

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def send_webhook(*, url: str, secret: str, payload: dict[str, Any]) -> int:
    timestamp = int(time.time())
    body = json.dumps(payload)
    headers = {
        "Prep-Signature": _build_signature(secret, timestamp, body),
        "Prep-Timestamp": str(timestamp),
        "Prep-Event-Id": str(uuid.uuid4()),
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=10.0) as client:
        response = client.post(url, headers=headers, content=body)

    print(f"\n⇢ Sent {payload['type']} to {url}")
    print(f"⇠ Response {response.status_code} {response.reason_phrase}")
    try:
        print(json.dumps(response.json(), indent=2))
    except ValueError:
        print(response.text)

    return response.status_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8787/webhooks/prep",
        help="Webhook receiver URL",
    )
    parser.add_argument(
        "--payload",
        help="Path to a JSON file containing the webhook payload",
    )
    args = parser.parse_args()

    secret = os.getenv("PREP_WEBHOOK_SECRET")
    if not secret:
        print("PREP_WEBHOOK_SECRET must be set", file=sys.stderr)
        return HTTPStatus.INTERNAL_SERVER_ERROR

    payload = _parse_payload(args.payload)
    return send_webhook(url=args.url, secret=secret, payload=payload)


if __name__ == "__main__":
    raise SystemExit(main())
