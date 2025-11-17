# Claude Code Configuration for Prep

**Quick reference for starting productive development sessions with Claude Code**

---

## 🚀 Quick Start

### Starting a New Session

**Option 1: Use the setup command** (Recommended)
```
/prep-setup
```

**Option 2: Manual context loading**
```
Read .claude/CONTEXT.md
Read .claude/agents/python-development.md
Read .claude/agents/backend-development.md
Read .claude/agents/security-scanning.md
```

### Session Template

Copy this into Claude Code to start a session:

```
Repository: Prep (~/projects/Prep)
Context: Read .claude/CONTEXT.md

Active Agent Profiles:
- python-development: Modern Python 3.11+ patterns
- backend-development: FastAPI, async/await, database patterns
- security-scanning: OWASP, auth validation, security auditing
- testing-tdd: pytest, coverage, test-first development
- code-review-ai: Architecture, performance, code quality

Workflow: ContextKit 4-Phase (Plan → Implement → Test → Report)

Tools:
- cc-sessions: Session management
- ccstatusline: Status HUD in Warp
- claude-code-mcp-enhanced: Quality gates

Goal: [Describe your goal here]

Current branch: [Your branch]
Working on: [Feature/bug/refactor]

Please:
1. Analyze the current state
2. Propose a small, testable approach
3. Implement with tests
4. Report results
```

---

## 📂 Configuration Structure

```
.claude/
├── CONTEXT.md                    # Master configuration (read this first)
├── agents/                       # Agent profiles
│   ├── python-development.md    # Python patterns & best practices
│   ├── backend-development.md   # API design & database patterns
│   ├── security-scanning.md     # Security auditing & OWASP
│   ├── testing-tdd.md          # Test-driven development
│   └── code-review-ai.md       # Code quality & architecture review
├── commands/                    # Custom slash commands
│   └── prep-setup.md           # Repository setup command
└── workflows/                   # Workflow templates
    └── auth-consolidation.md   # Auth hardening workflow example
```

---

## 🎯 Common Workflows

### Feature Development

```
Context: Read .claude/CONTEXT.md
Agents: python-development, backend-development, testing-tdd
Workflow: ContextKit 4-Phase

Feature: [Describe feature]

Phase 1 (Plan):
- Break down into small tasks
- Identify affected modules
- List security considerations
- Define success criteria

Phase 2 (Implement):
- Write tests first (TDD)
- Implement minimal code
- Follow agent patterns

Phase 3 (Test):
- Run: pytest tests/path/to/tests -xvs
- Ensure coverage: pytest --cov=prep.module
- Fix any failing tests

Phase 4 (Report):
- Show diffs
- Display test results
- List next steps
```

### Bug Fix

```
Context: Read .claude/CONTEXT.md
Agents: backend-development, testing-tdd, security-scanning

Bug: [Describe bug]
Reproduction: [Steps to reproduce]

Steps:
1. Write a failing test that reproduces the bug
2. Fix the bug with minimal changes
3. Verify test now passes
4. Run regression tests
5. Report fix and affected areas
```

### Security Review

```
Context: Read .claude/CONTEXT.md
Agent: security-scanning

Review scope: [Files or modules to review]

Checklist:
- Authentication & authorization
- Input validation
- SQL injection prevention
- Secrets management
- Error handling
- OWASP Top 10 compliance

Output: Security report with priority levels (P0, P1, P2)
```

### Code Review

```
Context: Read .claude/CONTEXT.md
Agent: code-review-ai

PR: [PR number or branch]

Review:
1. Architecture & design
2. Security issues
3. Performance concerns
4. Code quality
5. Testing coverage

Output: Review comments categorized by severity
```

---

## 🔑 Key Commands

### Testing
```bash
# Run all tests
pytest tests/ -xvs

# Run specific module tests
pytest tests/auth/ -xvs

# Run with coverage
pytest tests/ --cov=prep --cov-report=html

# Run only failed tests
pytest tests/ --lf
```

### Code Quality
```bash
# Format code
black prep/ tests/

# Lint code
ruff check prep/ tests/

# Type check
mypy prep/ --strict

# Security scan
pip-audit
bandit -r prep/ -ll
```

### Development
```bash
# Activate virtual environment
source .venv/bin/activate

# Start dev server
uvicorn prep.main:app --reload --port 8000

# Run database migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

---

## 📋 Agent Quick Reference

### Python Development
- Modern Python 3.11+ features
- Type hints required
- Async/await patterns
- Pathlib for file operations
- UTC timestamps only

### Backend Development
- RESTful API design
- FastAPI best practices
- SQLAlchemy async patterns
- Proper HTTP status codes
- Transaction management

### Security Scanning
- OWASP Top 10 compliance
- Auth validation (JWT + DB)
- Input sanitization
- SQL injection prevention
- Secrets management

### Testing TDD
- Test-first development
- 100% coverage for security-critical paths
- pytest patterns
- Fixtures and parametrization
- Mocking external services

### Code Review AI
- Architecture review
- Performance analysis
- Security audit
- Code quality check
- Testing completeness

---

## 🔒 Security Guardrails

These are **non-negotiable** and will be flagged immediately:

❌ **NEVER**:
- Stub/mock authentication in production code
- Hardcoded secrets or API keys
- SQL string interpolation (use ORM)
- JWT validation without DB lookup
- Missing authorization checks

✅ **ALWAYS**:
- Use `prep.auth.core` helpers for JWT validation
- Perform DB lookup after JWT decode
- Check `is_active=True` and `is_suspended=False`
- Validate all user inputs with Pydantic
- Use specific HTTPException status codes

---

## 📚 Documentation

### Internal Docs
- **Master Config**: `.claude/CONTEXT.md`
- **Auth Deep Dive**: `docs/deep-dive/AUTHENTICATION_DEEP_DIVE.md`
- **MVP Plan**: `docs/PREP_MVP_IMPLEMENTATION_PLAN.md`
- **Golden Path**: `docs/GOLDEN_PATH_DEMO.md`

### Agent Profiles
- `.claude/agents/python-development.md`
- `.claude/agents/backend-development.md`
- `.claude/agents/security-scanning.md`
- `.claude/agents/testing-tdd.md`
- `.claude/agents/code-review-ai.md`

### Workflows
- `.claude/workflows/auth-consolidation.md`

---

## 🎓 Learning & Reference

### Python
- [Python 3.11 Docs](https://docs.python.org/3.11/)
- [Type Hints (mypy)](https://mypy.readthedocs.io/)
- [Async/Await](https://docs.python.org/3/library/asyncio.html)

### FastAPI & SQLAlchemy
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pydantic](https://docs.pydantic.dev/)

### Security
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [Python Security](https://python.readthedocs.io/en/stable/library/security_warnings.html)

### Testing
- [pytest](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

## 🆘 Troubleshooting

### "Module not found" errors
```bash
source .venv/bin/activate
pip install -e .
```

### "Database connection failed"
```bash
# Check PostgreSQL is running
pg_isready

# Verify DATABASE_URL in .env
cat .env | grep DATABASE_URL
```

### "Tests failing with ORM errors"
Known issue with `BusinessPermit/BusinessProfile` relationship.
See: `.claude/CONTEXT.md` → Troubleshooting section

### "Type checking fails"
```bash
mypy prep/ --show-error-codes
# Fix reported issues or add # type: ignore comments with explanation
```

---

## 📞 Getting Help

1. **Check Configuration**:
   - Read `.claude/CONTEXT.md` for repo overview
   - Review relevant agent profile (`.claude/agents/`)
   - Check workflow template (`.claude/workflows/`)

2. **Search Docs**:
   - `docs/` directory for architecture docs
   - Agent profiles for code patterns
   - `tests/` for testing examples

3. **Ask Claude Code**:
   ```
   Context: Read .claude/CONTEXT.md
   Question: [Your question]

   Please explain with examples from this codebase.
   ```

---

## 🔄 Updating This Configuration

When making significant changes to:
- Architecture or patterns → Update `.claude/CONTEXT.md`
- Language features → Update `.claude/agents/python-development.md`
- API design → Update `.claude/agents/backend-development.md`
- Security rules → Update `.claude/agents/security-scanning.md`
- Testing patterns → Update `.claude/agents/testing-tdd.md`
- Review process → Update `.claude/agents/code-review-ai.md`

Commit these changes along with your code changes.

---

**Version**: 1.0
**Last Updated**: 2025-01-16
**Maintainer**: Christopher Sellers
**Repository**: https://github.com/PetrefiedThunder/Prep

---

## Example: Starting Auth Work

```
Repository: Prep (~/projects/Prep)
Context: Read .claude/CONTEXT.md
Workflow: Read .claude/workflows/auth-consolidation.md

Active Agents:
- python-development
- backend-development
- security-scanning
- testing-tdd

Branch: claude/auth-hardening-phase1

Goal: Continue auth hardening work
- Fix any remaining stub authentication
- Add refresh token support
- Ensure 100% test coverage on auth paths

Current state:
- PR #497 created (auth hardening phase 1)
- 7/7 JWT tests passing
- DB tests blocked by ORM issue

Next steps:
1. Review current auth implementation
2. Identify gaps or improvements
3. Propose small, testable changes
4. Implement with tests first
5. Report results

Ready to proceed.
```

---

*This configuration enables Claude Code to work efficiently within Prep's architecture, security requirements, and development standards. Update as the codebase evolves.*
