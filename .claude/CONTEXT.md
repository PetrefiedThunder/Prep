# Prep Repository - Claude Code Configuration

**Version:** 1.0
**Last Updated:** 2025-01-16
**Owner:** Christopher Sellers

---

## 🎯 Repository Overview

**Prep** (formerly PrepChef) is a commercial kitchen rental marketplace platform connecting certified kitchens with food entrepreneurs. The platform handles:

- Kitchen rental bookings with compliance verification
- Multi-jurisdiction regulatory compliance (LA, SF, etc.)
- Payment processing via Stripe Connect
- Host and renter management
- Admin certification workflows
- Real-time availability management

---

## 🛠️ Active Tooling Stack

### Core Development Tools
- **Session Management**: `cc-sessions` - Track work sessions per repo
- **Status Line**: `ccstatusline` - Real-time HUD in Warp terminal
- **MCP Enhanced**: `claude-code-mcp-enhanced` - Quality, tests, security hooks
- **Workflow Framework**: `ContextKit` - Structured 4-phase workflow

### Agent Profiles (from .claude/agents/)
- **`python-development`**: Modern Python patterns, testing, UV, packaging
- **`backend-development`**: API design, service boundaries, FastAPI patterns
- **`testing-tdd`**: Test-first development, pytest patterns, coverage
- **`code-review-ai`**: Security, concurrency, architectural review
- **`security-scanning`**: Auth, OWASP Top 10, dependency scanning

### Output Styles
- **`ccoutputstyles`**: Reusable personas (terse engineer, detailed architect, etc.)

---

## 📚 Repository Context

### Tech Stack
- **Language**: Python 3.11+
- **Web Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 15 with SQLAlchemy (async)
- **Authentication**: JWT with DB-backed validation
- **Payment Processing**: Stripe Connect
- **Testing**: pytest + pytest-asyncio + httpx
- **Task Queue**: (Planned: Celery or BullMQ)
- **Caching**: Redis (for sessions and availability)

### Key Domains
1. **Authentication & Authorization** (`prep/auth/`)
   - JWT validation with signature, expiry, audience checks
   - DB-backed user loading (prevents zombie sessions)
   - Role-based access control (ADMIN, HOST, CUSTOMER, etc.)
   - Real-time suspension enforcement

2. **Booking System** (`prep/api/bookings.py`, `prep/models/`)
   - Kitchen availability management
   - Conflict detection with buffer times
   - Recurring booking templates
   - Dynamic pricing with utilization metrics

3. **Compliance & Regulatory** (`prep/compliance/`, `prep/regulatory/`)
   - Multi-jurisdiction compliance rules (LA, SF)
   - Document verification workflows
   - Health certificates, business licenses, insurance
   - Certification expiry tracking

4. **Admin Operations** (`prep/admin/`)
   - Certification review queue
   - Kitchen moderation
   - Analytics and reporting
   - Audit logging

5. **Payment Processing** (Planned)
   - Stripe Connect onboarding
   - Payment intents and capture
   - Payout automation
   - Ledger tracking

### Architecture Pattern
- **Microservices-ish Monolith**: Modular codebase with clear service boundaries, deployable as a monolith for MVP
- **Async-First**: All I/O operations use `async/await`
- **Repository Pattern**: Database operations abstracted behind service layers
- **Dependency Injection**: FastAPI's `Depends()` for all shared resources

---

## 🔄 Default Workflow (ContextKit 4-Phase)

Every task should follow this pattern:

### Phase 1: PLAN 📋
- Break down task into small, testable chunks (< 100 lines per change)
- Identify affected modules and dependencies
- List security considerations
- Define success criteria and test cases
- Estimate complexity (S/M/L)

### Phase 2: IMPLEMENT 💻
- Write code with security and concurrency in mind
- Follow Python and backend development agent guidelines
- Add comprehensive docstrings
- Use type hints on all functions
- Keep changes small and focused

### Phase 3: TEST 🧪
- Write tests FIRST when possible (TDD)
- Ensure all security-critical paths have tests
- Run: `pytest tests/path/to/tests -xvs`
- Verify coverage on changed code
- Fix any failing tests before proceeding

### Phase 4: REPORT 📊
- Show unified diffs (`git diff`)
- Display test results (passed/failed/skipped)
- List files changed and line counts
- Document any breaking changes
- Suggest next steps or follow-up tasks

---

## 🔒 Security Requirements (Non-Negotiable)

### Authentication & Authorization
- ✅ All admin endpoints MUST use `Depends(get_current_admin)` from `prep.admin.dependencies`
- ✅ All user endpoints MUST perform DB lookup (no JWT-only auth)
- ✅ JWT validation MUST check: signature, expiry, audience
- ✅ DB queries MUST enforce: `is_active=True`, `is_suspended=False`
- ❌ NO stub/mock authentication functions in production code
- ❌ NO hardcoded secrets or API keys

### Database Operations
- ✅ Use SQLAlchemy ORM (no raw SQL string interpolation)
- ✅ Use `AsyncSession` for all DB operations
- ✅ Check for `None` after all `.scalar_one_or_none()` queries
- ✅ Use transactions (`async with session.begin()`) for multi-step operations
- ❌ NO SQL injection vulnerabilities

### Error Handling
- ✅ Use specific `HTTPException` with correct status codes (401 vs 403)
- ✅ Generic error messages to prevent user enumeration
- ✅ Log detailed errors server-side, return generic errors client-side
- ❌ NO sensitive data in error responses (user IDs, email addresses, etc.)

### Dependencies & Secrets
- ✅ All secrets MUST come from environment variables
- ✅ Document required env vars in `.env.example`
- ✅ Pin dependency versions in `requirements.txt`
- ✅ Run `pip-audit` or `safety check` before deploying
- ❌ NO `.env` files committed to git

---

## 📝 Code Standards

### Python Style
- **Formatter**: Black (line length: 100)
- **Linter**: Ruff (with default rules)
- **Type Checker**: mypy (strict mode)
- **Import Order**: isort (Black-compatible)

### Required Patterns
```python
# ✅ GOOD: Modern Python with type hints
from __future__ import annotations

from uuid import UUID
from datetime import UTC, datetime

async def load_user(user_id: UUID, session: AsyncSession) -> User | None:
    """Load a user by ID with active status check.

    Args:
        user_id: The user's unique identifier
        session: Active database session

    Returns:
        User instance if found and active, None otherwise
    """
    result = await session.execute(
        select(User).where(User.id == user_id, User.is_active.is_(True))
    )
    return result.scalar_one_or_none()
```

### Anti-Patterns to Avoid
```python
# ❌ BAD: No type hints
def load_user(user_id, session):
    ...

# ❌ BAD: Naive datetime
created_at = datetime.now()  # Use datetime.now(UTC) instead

# ❌ BAD: String paths
with open("prep/data/file.txt") as f:  # Use pathlib.Path instead
    ...

# ❌ BAD: Blocking I/O in async function
async def fetch_data():
    time.sleep(1)  # Use await asyncio.sleep(1) instead
```

---

## 🧪 Testing Standards

### Test Organization
```
tests/
├── auth/              # Authentication tests
├── admin/             # Admin API tests
├── api/               # Public API tests
├── compliance/        # Compliance engine tests
├── models/            # ORM model tests
└── conftest.py        # Shared fixtures
```

### Test Naming Convention
- Test files: `test_<module_name>.py`
- Test functions: `test_<what>_<scenario>`
- Example: `test_load_user_suspended_returns_none`

### Required Test Coverage
- ✅ All authentication paths (100% coverage)
- ✅ All admin authorization checks (100% coverage)
- ✅ All payment processing logic (100% coverage)
- ✅ Compliance validation rules (100% coverage)
- ✅ Booking conflict detection (100% coverage)
- 🎯 Overall target: 80%+ coverage

### Test Patterns
```python
# ✅ GOOD: Async test with fixtures
@pytest.mark.anyio
async def test_load_suspended_user_fails(db_session: AsyncSession, suspended_user: User):
    """Test that suspended users cannot be loaded."""
    with pytest.raises(HTTPException) as exc_info:
        await load_user_from_db(suspended_user.id, db_session, require_active=True)

    assert exc_info.value.status_code == 403
```

---

## 🚀 Quick Start Commands

### Start a New Session
```bash
# In Claude Code
/prep-setup

# Or manually:
Read .claude/CONTEXT.md
Read .claude/agents/python-development.md
Read .claude/agents/backend-development.md
Read .claude/agents/security-scanning.md
```

### Common Development Tasks
```bash
# Run tests
source .venv/bin/activate
pytest tests/ -xvs

# Run specific test file
pytest tests/auth/test_core_helpers.py -xvs

# Check code quality
black prep/ tests/
ruff check prep/ tests/
mypy prep/

# Run security scan
pip-audit
bandit -r prep/ -ll

# Start dev server
uvicorn prep.main:app --reload --port 8000
```

---

## 📂 Key File Locations

### Configuration
- **Environment**: `.env` (gitignored), `.env.example` (committed)
- **Dependencies**: `requirements.txt`, `requirements-dev.txt`
- **Database**: `alembic.ini`, `alembic/versions/`
- **Tests**: `pytest.ini`, `tests/conftest.py`

### Core Modules
- **Auth Core**: `prep/auth/core.py` (JWT validation, user loading)
- **Admin Auth**: `prep/admin/dependencies.py` (admin-specific auth)
- **Database**: `prep/database/connection.py`, `prep/models/`
- **Settings**: `prep/settings.py` (environment config)

### Documentation
- **API Docs**: `/docs` (FastAPI auto-generated)
- **Architecture**: `docs/deep-dive/AUTHENTICATION_DEEP_DIVE.md`
- **Planning**: `docs/PREP_MVP_IMPLEMENTATION_PLAN.md`
- **GitHub Issues**: `docs/GITHUB_ISSUES_MASTER.md`

---

## 🎨 Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`

**Examples**:
```
feat(auth): add JWT refresh token support

- Implement refresh token generation and validation
- Add /api/v1/auth/refresh endpoint
- Update tests for refresh flow

Closes #123
```

```
fix(admin): remove stub authentication from certification API (P0 security)

🚨 CRITICAL: Previously allowed unauthenticated admin access
- Import real get_current_admin from prep.admin.dependencies
- Remove stub functions at lines 289-296, 321-329
- All endpoints now require valid JWT + DB lookup

Security impact: Prevents unauthorized access to admin endpoints
```

---

## 🔗 Related Documentation

- [Authentication Deep Dive](../docs/deep-dive/AUTHENTICATION_DEEP_DIVE.md)
- [MVP Implementation Plan](../docs/PREP_MVP_IMPLEMENTATION_PLAN.md)
- [Golden Path Demo](../docs/GOLDEN_PATH_DEMO.md)
- [GitHub Issues Master](../docs/GITHUB_ISSUES_MASTER.md)

---

## 🆘 Troubleshooting

### Common Issues

**ORM Relationship Errors**
```
sqlalchemy.exc.ArgumentError: reverse_property 'permits' on relationship
BusinessPermit.business references relationship BusinessProfile.permits
```
**Solution**: This is a known issue in `prep/models/orm.py`. DB tests are blocked until this is fixed.

**JWT Validation Failures**
```
HTTPException 401: Invalid authentication credentials
```
**Solution**: Ensure `ADMIN_JWT_SECRET` is set and matches the secret used to sign tokens.

**Async Test Failures**
```
RuntimeError: asyncio.run() cannot be called from a running event loop
```
**Solution**: Use `@pytest.mark.anyio` instead of `@pytest.mark.asyncio`.

---

## 📞 Support

- **Repository Issues**: https://github.com/PetrefiedThunder/Prep/issues
- **Owner**: Christopher Sellers
- **Primary Development Tool**: Claude Code in Warp

---

**Last updated**: 2025-01-16 by Claude Code
**Next review**: After major architecture changes
