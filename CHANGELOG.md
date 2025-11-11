# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Canonical error envelope with request identifiers across platform, payments, and admin APIs
- Idempotency middleware requiring Idempotency-Key headers on POST/PUT requests
- Cursor-based pagination for review and admin listing endpoints with metadata responses
- Comprehensive testing infrastructure with smoke tests and CI workflows
- Developer tooling and defensive error handling

### Changed
- Standardized API error envelopes with request identifiers
- Modernized type annotations across Python codebase
- Updated dependencies: FastAPI 0.121.1, WeasyPrint 66.0, prometheus-client 0.23.1, alembic 1.17.1
- Refreshed OpenAPI versioning guidance

### Fixed
- Critical bug in City Regulatory Service main.py (restored from corruption)
- Python dependency conflicts (boto3/botocore/aiobotocore compatibility)
- HarborHomes Node.js dependency installation issues
- ORM duplicate classes and invalid type annotations
- Dynamic import safety and error handling

### Security
- Docker security hardening with multi-stage builds and non-root users
- Secret scanning with Gitleaks pre-commit hooks and GitHub Actions
- RIC test harness for compliance engine regression testing
- Pre-commit hooks (Ruff, Black, Bandit, MyPy, Hadolint, yamllint)
- Weekly and monthly security audit automation

## [v1.0.0] - 2025-08-14

- Initial project structure and core modules
- Early prototypes for accessibility and kitchen booking
