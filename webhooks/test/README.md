# Webhook receiver test utilities

This package contains utilities for exercising the Prep webhook receiver both
via automated tests and manual smoke checks.

## Automated tests

The `test_server.py` module uses `pytest` and FastAPI's `TestClient` to verify
signature validation, timestamp skew enforcement, and event routing logic. Run
the suite with:

```bash
pytest webhooks/test/test_server.py
```

## Manual webhook invocation

`send_webhook.py` mirrors the behaviour used in the automated tests. Export the
`PREP_WEBHOOK_SECRET` environment variable used by the running webhook server
and invoke:

```bash
python -m webhooks.test.send_webhook --url http://127.0.0.1:8787/webhooks/prep
```

Use the `--payload` flag to point at a JSON file when you want to send
different event bodies.
# Webhook integration tests

This folder contains utilities for exercising the Prep webhook server locally.

## Running the server

1. Export the webhook secret before starting the server:

   ```bash
   export PREP_WEBHOOK_SECRET="dev_secret"
   uvicorn webhooks.server.main:app --reload
   ```

2. The server exposes three endpoints:

   - `POST /webhooks/fees.updated`
   - `POST /webhooks/requirements.updated`
   - `POST /webhooks/policy.decision`

   Each endpoint expects a JSON body with a `type` field matching the endpoint name.

## Sending a signed webhook

Use the `send_webhook.py` script to deliver a signed request to the running server. The
script handles payload generation and signature calculation so it matches the server's
expectations.

```bash
python webhooks/test/send_webhook.py --event fees.updated --secret "$PREP_WEBHOOK_SECRET"
```

Optional arguments:

- `--url` – Base URL for the server (defaults to `http://localhost:8000`).
- `--payload` – Path to a JSON file to use instead of the generated sample payload.
- `--timestamp` – Override the signing timestamp (useful for exercising skew failures).

The script prints the HTTP status code and response body from the server, making it easy
to confirm that the webhook was accepted.
