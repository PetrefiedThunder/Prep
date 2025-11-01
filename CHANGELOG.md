# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

- Added canonical error envelope with request identifiers across platform, payments, and admin APIs
- Introduced idempotency middleware requiring Idempotency-Key headers on POST/PUT requests
- Converted review and admin listing endpoints to cursor-based pagination with metadata responses
- Documented new error schema, pagination semantics, and v1 version guidance in OpenAPI and gateway metadata
- Expanded main README with architecture and setup
- Added CONTRIBUTING.md for contributor onboarding
- Added issue and PR templates under .github/
- Added CHANGELOG.md

## [v1.0.0] - 2025-08-14

- Initial project structure and core modules
- Early prototypes for accessibility and kitchen booking
