#!/usr/bin/env bash
set -euo pipefail

pnpm -w lint
pnpm -w test --coverage
pnpm -w stryker run
pnpm -w pact:verify
pnpm -w e2e:playwright
pnpm -w perf:smoke
pnpm -w zap:baseline
pnpm -w ge:check
