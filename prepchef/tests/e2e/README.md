# End-to-End Tests

This directory contains Playwright-based end-to-end tests for PrepChef.

## Setup

```
npm install
npx playwright install
```

## Running tests

```
BASE_URL=http://localhost:3000 npm test
```

Use the provided `docker-compose.yml` to start dependent services locally before running tests.
