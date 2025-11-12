#!/usr/bin/env python3
"""Utility script to send signed webhook requests to the local server."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from pathlib import Path

import requests

DEFAULT_URL = "http://127.0.0.1:8000/webhooks/prep"
SECRET_ENV_NAME = "PREP_WEBHOOK_SECRET"


def _load_payload(path: Path | None, event_id: str, event_type: str) -> dict[str, object]:
    if path is None:
        return {
            "event_id": event_id,
            "event_type": event_type,
            "sent_at": int(time.time()),
            "data": {"message": "Hello from Prep webhooks!"},
        }

    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:  # pragma: no cover - CLI utility
        raise SystemExit(f"Payload file is not valid JSON: {exc}")

    if "event_id" not in payload:
        payload["event_id"] = event_id
    if "event_type" not in payload:
        payload["event_type"] = event_type

    return payload


def _load_secret(cli_secret: str | None) -> str:
    secret = cli_secret or os.getenv(SECRET_ENV_NAME)
    if not secret:
        raise SystemExit(
            "A webhook secret must be provided via --secret or the PREP_WEBHOOK_SECRET environment variable."
        )
    return secret


def _sign_payload(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Send a signed webhook request to the Prep webhook server."
    )
    parser.add_argument(
        "--url", default=DEFAULT_URL, help="Webhook endpoint URL. Defaults to %(default)s"
    )
    parser.add_argument("--secret", help="Webhook signing secret. Overrides PREP_WEBHOOK_SECRET.")
    parser.add_argument(
        "--event-id", default=str(uuid.uuid4()), help="Event identifier for the payload."
    )
    parser.add_argument("--event-type", default="prep.test", help="Event type for the payload.")
    parser.add_argument(
        "--payload-file",
        type=Path,
        help="Optional JSON file containing the payload envelope. event_id/event_type will be injected if missing.",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout in seconds.")

    args = parser.parse_args(argv)

    secret = _load_secret(args.secret)
    payload_dict = _load_payload(args.payload_file, args.event_id, args.event_type)
    payload_bytes = json.dumps(payload_dict, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = _sign_payload(secret, payload_bytes)

    response = requests.post(
        args.url,
        data=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Prep-Signature": signature,
        },
        timeout=args.timeout,
    )

    print(f"Status: {response.status_code}")
    try:
        print("Response:", json.dumps(response.json(), indent=2))
    except ValueError:
        print("Raw response:", response.text)

    return 0 if response.ok else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main())
