# Contributing to Prep

Thank you for your interest in contributing to Prep! This document provides guidelines and best practices for contributing to this enterprise-grade compliance platform.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [Development Workflow](#development-workflow)
4. [Code Quality Standards](#code-quality-standards)
5. [Testing Requirements](#testing-requirements)
6. [Pull Request Process](#pull-request-process)
7. [Reporting Issues](#reporting-issues)
8. [Community Guidelines](#community-guidelines)

---

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+** with pip
- **Node.js 20+** with npm
- **Docker 24+** and Docker Compose 2+
- **Git** with pre-commit hooks support
- **PostgreSQL 15+** (or use Docker)
- **Redis 7+** (or use Docker)

### Quick Setup

The fastest way to get started is using our bootstrap command:

```bash
# Clone the repository
git clone https://github.com/your-username/Prep.git
cd Prep

# Bootstrap the entire environment
make bootstrap

# Install pre-commit hooks
pre-commit install

# Verify setup
make health
```

---

## Development Setup

### Python Projects

1. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -e .
   pip install -e .[dev]  # Install development dependencies
   ```

3. **Run the tests:**
   ```bash
   pytest
   pytest --cov=prep --cov-report=html  # With coverage
   ```

### Node.js Projects

1. **Install dependencies:**
   ```bash
   cd prepchef
   npm install
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your settings (never commit secrets!)
   ```

3. **Run the tests:**
   ```bash
   npm test
   npm run test:e2e  # End-to-end tests
   ```

### Docker Development

```bash
# Start all services
make up

# View logs
make logs

# Stop services
make down

# Clean environment (removes volumes!)
make clean
```

---

## Development Workflow

### 1. Create a Feature Branch

Follow our branch naming conventions:

```bash
git checkout -b <type>/<description>
```

Branch types:
- `feature/` – New features
- `fix/` – Bug fixes
- `docs/` – Documentation updates
- `refactor/` – Code refactoring
- `test/` – Test additions/improvements
- `security/` – Security fixes
- `perf/` – Performance improvements

**Example:**
```bash
git checkout -b feature/add-jwt-refresh-tokens
```

### 2. Make Your Changes

- Write clean, maintainable code following our style guides
- Add tests for new functionality
- Update documentation as needed
- Follow [Conventional Commits](https://www.conventionalcommits.org/) format

**Commit Message Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Example:**
```bash
git commit -m "feat(auth): add JWT refresh token rotation

- Implement refresh token mechanism
- Add token rotation on usage
- Update auth middleware to handle refresh
- Add tests for token rotation

Closes #123"
```

### 3. Run Quality Checks

Before pushing, ensure all checks pass:

```bash
# Run all linters
make lint

# Run type checking
make typecheck

# Run tests
make test

# Run pre-commit hooks manually
pre-commit run --all-files

# Format code
make format
```

### 4. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub using our PR template.

---

## Code Quality Standards

### Python

#### Style Guide
- Follow **PEP 8** style guide
- Use **type hints** for all function signatures
- Document with **docstrings** (Google style)
- Maximum line length: **100 characters**

#### Tools
- **Linting:** `ruff check .`
- **Formatting:** `ruff format .`
- **Type checking:** `mypy .`
- **Security scanning:** `bandit -r .`

#### Best Practices
```python
# Good: Type hints and docstrings
def calculate_fee(amount: Decimal, rate: Decimal) -> Decimal:
    """Calculate platform fee for a given amount.

    Args:
        amount: The base amount in USD
        rate: The fee rate as a decimal (e.g., 0.15 for 15%)

    Returns:
        The calculated fee amount

    Raises:
        ValueError: If amount or rate is negative
    """
    if amount < 0 or rate < 0:
        raise ValueError("Amount and rate must be non-negative")
    return amount * rate

# Bad: No types, no documentation
def calculate_fee(amount, rate):
    return amount * rate
```

### TypeScript/Node.js

#### Style Guide
- Enable **strict mode** in tsconfig.json
- Use **interfaces** over types for object shapes
- Prefer **async/await** over promises
- Maximum line length: **100 characters**

#### Tools
- **Linting:** `npx eslint .`
- **Formatting:** `npx prettier --write .`
- **Type checking:** `npx tsc --noEmit`

#### Best Practices
```typescript
// Good: Interface with proper types
interface BookingRequest {
  kitchenId: string;
  startTime: Date;
  endTime: Date;
  userId: string;
}

async function createBooking(request: BookingRequest): Promise<Booking> {
  // Validate input
  if (request.startTime >= request.endTime) {
    throw new ValidationError('Start time must be before end time');
  }

  // Implementation
  return await bookingService.create(request);
}

// Bad: Any types, no validation
async function createBooking(request: any) {
  return await bookingService.create(request);
}
```

### Security Best Practices

⚠️ **CRITICAL:** Never commit secrets, API keys, or credentials

- Use environment variables for all secrets
- Use `secrets` module for cryptographic operations (not `random`)
- Validate and sanitize all user inputs
- Use parameterized queries to prevent SQL injection
- Implement proper error handling (don't expose internal errors)
- Follow principle of least privilege

```python
# Good: Secure random token
import secrets
token = secrets.token_urlsafe(32)

# Bad: Insecure random
import random
token = ''.join(random.choices(string.ascii_letters, k=32))
```

---

## Testing Requirements

### Test Coverage Goals
- **Minimum:** 70% coverage for new code
- **Target:** 80%+ coverage
- **Critical paths:** 95%+ coverage (auth, payments, compliance)

### Test Types

#### Unit Tests
```bash
# Python
pytest tests/unit/

# Node.js
npm run test:unit
```

#### Integration Tests
```bash
# Python
pytest tests/integration/ -m integration

# Node.js
npm run test:integration
```

#### E2E Tests
```bash
npm run test:e2e
```

### Writing Good Tests

```python
# Good: Clear, focused test
def test_booking_requires_valid_time_range():
    """Booking should fail when start time is after end time."""
    with pytest.raises(ValidationError) as exc:
        create_booking(
            kitchen_id="kitchen-1",
            start_time=datetime(2025, 11, 11, 14, 0),
            end_time=datetime(2025, 11, 11, 12, 0)
        )
    assert "Start time must be before end time" in str(exc.value)

# Bad: Unclear, tests too much
def test_bookings():
    booking = create_booking(...)
    assert booking is not None
    assert booking.id
```

---

## Pull Request Process

### 1. Before Submitting

- [ ] All tests pass locally
- [ ] Code is linted and formatted
- [ ] Type checking passes
- [ ] Pre-commit hooks pass
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (if applicable)
- [ ] Commit messages follow conventions

### 2. PR Description

Use the template in `PR_DESCRIPTION.md` and include:

- **Summary:** What does this PR do?
- **Motivation:** Why is this change needed?
- **Implementation:** How does it work?
- **Testing:** What testing was performed?
- **Screenshots:** For UI changes
- **Breaking Changes:** Any breaking changes?
- **Related Issues:** Link to issues

### 3. Review Process

1. **Automated CI checks** must pass (all 23 workflows)
2. **At least one maintainer approval** required
3. **Address review feedback** promptly
4. **Squash commits** before merge (if requested)

### 4. After Merge

- Delete your feature branch
- Update any dependent branches
- Close related issues

---

## Reporting Issues

### Bug Reports

Use the GitHub issue template and include:

- **Environment:** OS, Python/Node version, Docker version
- **Steps to reproduce:** Clear, minimal reproduction steps
- **Expected behavior:** What should happen
- **Actual behavior:** What actually happens
- **Error messages:** Full error messages and stack traces
- **Screenshots:** If applicable

### Feature Requests

- Describe the problem you're trying to solve
- Explain your proposed solution
- Provide use cases and examples
- Consider implementation complexity

### Security Issues

🔒 **Do NOT open public issues for security vulnerabilities**

Instead:
1. Email security contact (see [SECURITY.md](SECURITY.md))
2. Use GitHub Security Advisories
3. Provide detailed information privately

---

## Community Guidelines

### Code of Conduct

- **Be respectful and inclusive** to all contributors
- **Welcome newcomers** and help them get started
- **Give constructive feedback** in code reviews
- **Assume good intentions** from others
- **Respect different perspectives** and approaches

### Communication Channels

- **GitHub Issues:** Bug reports and feature requests
- **GitHub Discussions:** Questions, ideas, and architecture discussions
- **Pull Requests:** Code reviews and implementation discussions

### Getting Help

- Check [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) for setup help
- Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- Ask questions in GitHub Discussions
- Review existing issues and PRs

---

## Additional Resources

- **[README.md](README.md)** – Project overview and quick start
- **[DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md)** – Detailed setup guide
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** – Common issues and solutions
- **[SECURITY.md](SECURITY.md)** – Security policies and procedures
- **[docs/architecture.md](docs/architecture.md)** – System architecture
- **[CODE_QUALITY_FIXES.md](CODE_QUALITY_FIXES.md)** – Refactoring guide

---

Thank you for helping make Prep better! Your contributions are valued and appreciated. 🙏
