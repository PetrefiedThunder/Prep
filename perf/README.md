# k6 Smoke Test

This directory contains the k6 smoke test used to continuously validate the core Prep APIs under a sustained but lightweight load.

## Scenario: `perf/smoke.js`

- **Virtual users:** 50 constant VUs
- **Duration:** 5 minutes
- **Endpoints:**
  - `GET /compliance/query`
  - `GET /bookings`
  - `GET /analytics/host/1`
- **Thresholds:**
  - `http_req_duration` p95 under 500 ms
  - `http_req_failed` rate under 0.1%
  - Per-endpoint success checks above 99%

## Running the test locally

1. Install [k6](https://k6.io/docs/get-started/installation/).
2. Export the base URL that the smoke test should exercise (defaults to `http://localhost:3000`). For example:

   ```bash
   export BASE_URL="https://staging.prep.example.com"
   ```

3. Execute the smoke scenario:

   ```bash
   k6 run perf/smoke.js
   ```

The test writes a machine-readable summary to `k6-smoke-summary.json` alongside the standard console output. This artifact can be uploaded in CI or used for historical comparisons.

## GitHub Actions integration

The repository contains a reusable workflow, `.github/workflows/perf-smoke.yml`, that installs k6, runs the smoke test, and uploads the summary artifact. The workflow expects a `PERF_BASE_URL` secret that points at the environment you want to exercise.

You can trigger the workflow manually from the GitHub Actions tab via the `Run smoke test` workflow dispatch event, or adapt it as needed for scheduled or pull request runs.
