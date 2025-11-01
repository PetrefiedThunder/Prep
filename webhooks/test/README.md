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
