# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Canonical error envelope with request identifiers across platform, payments, and admin APIs
- Idempotency middleware requiring Idempotency-Key headers on POST/PUT requests
- Cursor-based pagination for review and admin listing endpoints with metadata responses
- Comprehensive testing infrastructure with smoke tests and CI workflows
- Developer tooling and defensive error handling
- Comprehensive bug hunt reports and security vulnerability analysis
- Code quality analysis and actionable refactoring guides
- **[2025-11-19]** Claude Code configuration (.claude/ directory) with agent profiles and workflows
- **[2025-11-19]** Vendor verification service (apps/vendor_verification)
- **[2025-11-19]** SECURITY_FIXES_2025-11-19.md comprehensive security documentation
- **[2025-11-19]** Component status tracking in README (MVP completion: 25-35%)
- **[2025-11-19]** PR_DESCRIPTION_README_SECURITY.md for comprehensive change tracking

### Changed
- Standardized API error envelopes with request identifiers
- Modernized type annotations across Python codebase
- Updated dependencies: FastAPI 0.121.2, WeasyPrint 66.0, prometheus-client 0.23.1, alembic 1.17.2
- Refreshed OpenAPI versioning guidance
- Improved Docker configurations with security best practices
- Enhanced error handling and input validation across services
- **[2025-11-19]** README.md completely rewritten (805 → 579 lines, more focused and accurate)
- **[2025-11-19]** Security dependencies: cryptography 41.0.7 → 46.0.3, setuptools 68.1.2 → 80.9.0, pip 24.0 → 25.3

### Fixed
- **78 bugs identified and resolved** across the codebase (9 critical, 9 high severity)
- Critical bug in City Regulatory Service main.py (restored from corruption)
- Python dependency conflicts (boto3/botocore/aiobotocore compatibility)
- HarborHomes Node.js dependency installation issues
- ORM duplicate classes and invalid type annotations
- Dynamic import safety and error handling
- Duplicate function definitions in api/index.py (create_app)
- Duplicate middleware registrations (RBACMiddleware)
- Duplicate router definitions causing route conflicts
- SQL injection vulnerabilities in dynamic queries
- Weak cryptographic randomness for security tokens
- Hardcoded secrets in production code paths
- Missing error boundaries in React components
- Type mismatches and annotation errors across Python codebase
- Database connection leaks and resource management issues
- ETL crawler error handling and data validation
- JWT token generation security issues
- **[2025-11-19]** 7 critical Python dependency vulnerabilities (3 HIGH, 4 MEDIUM severity)
  - PYSEC-2024-225: cryptography NULL pointer dereference (DoS)
  - GHSA-3ww4-gg4f-jr7f: cryptography RSA TLS decryption vulnerability
  - GHSA-9v9h-cgj8-h64p: cryptography PKCS12 malformed file DoS
  - GHSA-h4gh-qq45-vh27: cryptography bundled OpenSSL vulnerabilities
  - PYSEC-2025-49: setuptools path traversal (RCE risk)
  - GHSA-cx63-2mw6-8hw5: setuptools code injection via malicious URLs
  - GHSA-4xh5-x5gv-qwph: pip tarfile path traversal

### Security
- Docker security hardening with multi-stage builds and non-root users
- Secret scanning with Gitleaks pre-commit hooks and GitHub Actions
- RIC test harness for compliance engine regression testing
- Pre-commit hooks (Ruff, Black, Bandit, MyPy, Hadolint, yamllint)
- Weekly and monthly security audit automation
- Fixed Docker containers running as root across all Node services
- Implemented secure random token generation using secrets module
- Enhanced input validation and SQL injection prevention
- Removed hardcoded credentials and API keys from codebase
- **[2025-11-19]** pip-audit verification: 0 known Python vulnerabilities (down from 7)
- **[2025-11-19]** Upgraded cryptography to 46.0.3 (prevents RCE, TLS attacks, DoS)
- **[2025-11-19]** Upgraded setuptools to 80.9.0 (prevents path traversal RCE)
- **[2025-11-19]** Upgraded pip to 25.3 (prevents tarfile extraction attacks)

## [v1.0.0] - 2025-08-14

- Initial project structure and core modules
- Early prototypes for accessibility and kitchen booking
