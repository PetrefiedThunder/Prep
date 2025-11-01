# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

- Expanded main README with architecture and setup
- Added CONTRIBUTING.md for contributor onboarding
- Added issue and PR templates under .github/
- Added CHANGELOG.md
- Standardized API error envelopes with request identifiers across platform, payments, and admin routers
- Added Redis-backed idempotency middleware enforcing Idempotency-Key validation for POST and PUT requests
- Switched review and admin collection endpoints to cursor-based pagination and refreshed OpenAPI versioning guidance

## [v1.0.0] - 2025-08-14

- Initial project structure and core modules
- Early prototypes for accessibility and kitchen booking
