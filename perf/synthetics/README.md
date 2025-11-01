# Synthetic Regulatory Monitoring

This directory contains a lightweight synthetic monitoring harness that targets
the city regulatory service endpoints for San Francisco and Joshua Tree. The
script issues repeated requests against the requirements listing and estimate
calculation APIs and verifies that the p95 latency remains below 200 ms.

## Running locally

```bash
export SYNTHETIC_BASE_URL="https://regulatory.prepchef.com"
python perf/synthetics/run_synthetics.py --output perf/synthetics/out/latest.json
```

Environment variables allow you to point the probes at staging or production and
tune sampling depth:

- `SYNTHETIC_BASE_URL` (required): Base URL of the regulatory service
- `SYNTHETIC_JURISDICTIONS`: Comma separated list of jurisdiction slugs
  (default: `san_francisco,joshua_tree`)
- `SYNTHETIC_ITERATIONS`: Number of samples per endpoint (default: `5`)
- `SYNTHETIC_THRESHOLD_MS`: Latency threshold in milliseconds (default: `200`)
- `SYNTHETIC_IDEMPOTENCY`: Optional idempotency key for estimate calls
- `SYNTHETIC_SCENARIOS`: JSON blob overriding the default request payloads

The script prints a JSON summary to stdout and optionally writes it to the path
provided via `--output`.
