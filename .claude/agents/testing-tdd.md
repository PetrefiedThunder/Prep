# Testing & TDD Agent

**Role**: Test-driven development, pytest patterns, coverage enforcement
**Priority**: High
**Scope**: All code changes should include tests

---

## 🎯 Testing Philosophy

### Test-First Development
1. **Write the test** for the feature/bugfix
2. **Watch it fail** (confirms test is actually testing something)
3. **Implement** the minimal code to make it pass
4. **Refactor** with confidence (tests catch regressions)

### Coverage Goals
- **Authentication/Authorization**: 100% coverage (non-negotiable)
- **Payment Processing**: 100% coverage (non-negotiable)
- **Compliance Logic**: 100% coverage (non-negotiable)
- **Business Logic**: 90%+ coverage
- **Overall**: 80%+ coverage

---

## 🧪 Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── auth/                    # Auth tests
│   ├── __init__.py
│   ├── test_core_helpers.py
│   └── test_jwt_validation.py
├── admin/                   # Admin tests
│   ├── test_dependencies.py
│   └── test_certification_api.py
├── api/                     # API endpoint tests
│   ├── test_bookings.py
│   ├── test_kitchens.py
│   └── test_auth_endpoints.py
├── models/                  # ORM model tests
│   └── test_user_model.py
└── compliance/              # Compliance engine tests
    ├── test_la_rules.py
    └── test_sf_rules.py
```

---

## ✅ Pytest Patterns

### Fixtures

```python
import pytest
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from prep.models.db import Base, User, UserRole

@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Use asyncio backend for async tests."""
    return "asyncio"


@pytest.fixture()
async def db_engine():
    """Create in-memory database engine for tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture()
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test."""
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback()  # Rollback any uncommitted changes


@pytest.fixture()
async def active_user(db_session: AsyncSession) -> User:
    """Create an active user for testing."""
    user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed",
        role=UserRole.CUSTOMER,
        is_active=True,
        is_suspended=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture()
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user for testing."""
    user = User(
        email="admin@example.com",
        full_name="Admin User",
        hashed_password="hashed",
        role=UserRole.ADMIN,
        is_active=True,
        is_suspended=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user
```

### Test Naming

```python
# ✅ GOOD: Descriptive test names
@pytest.mark.anyio
async def test_load_user_with_valid_id_returns_user(db_session, active_user):
    """Test that load_user returns user for valid ID."""
    ...

@pytest.mark.anyio
async def test_load_user_with_invalid_id_raises_404(db_session):
    """Test that load_user raises HTTPException for invalid ID."""
    ...

@pytest.mark.anyio
async def test_load_suspended_user_with_require_active_raises_403(db_session):
    """Test that suspended users cannot be loaded when require_active=True."""
    ...

# ❌ BAD: Vague test names
def test_user():
    ...

def test_error():
    ...
```

### Async Tests

```python
# ✅ GOOD: Async test with anyio
@pytest.mark.anyio
async def test_create_booking(db_session: AsyncSession):
    """Test booking creation."""
    booking = Booking(
        kitchen_id=uuid4(),
        customer_id=uuid4(),
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(hours=2),
    )
    db_session.add(booking)
    await db_session.flush()

    assert booking.id is not None
```

### Parametrized Tests

```python
@pytest.mark.parametrize(
    "email,expected_valid",
    [
        ("user@example.com", True),
        ("test.user+tag@example.co.uk", True),
        ("invalid-email", False),
        ("@example.com", False),
        ("", False),
        ("a" * 256 + "@example.com", False),  # Too long
    ],
)
def test_email_validation(email: str, expected_valid: bool):
    """Test email validation with various inputs."""
    if expected_valid:
        # Should not raise
        validated = EmailStr.validate(email)
        assert validated == email
    else:
        with pytest.raises(ValidationError):
            EmailStr.validate(email)
```

### Exception Testing

```python
# ✅ GOOD: Test exception type and message
@pytest.mark.anyio
async def test_load_nonexistent_user_raises_403(db_session):
    """Test that loading nonexistent user raises 403."""
    fake_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await load_user_from_db(fake_id, db_session)

    assert exc_info.value.status_code == 403
    assert "not authorized" in exc_info.value.detail.lower()
```

### Mocking External Services

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.anyio
async def test_send_email_success():
    """Test email sending with mocked SMTP."""
    with patch("prep.email.smtp_client.send") as mock_send:
        mock_send.return_value = AsyncMock(return_value=True)

        result = await send_welcome_email("user@example.com")

        assert result is True
        mock_send.assert_called_once_with(
            to="user@example.com",
            subject="Welcome to Prep",
            body=mock.ANY,
        )


@pytest.mark.anyio
async def test_stripe_payment_failure():
    """Test handling of Stripe payment failure."""
    with patch("stripe.PaymentIntent.create") as mock_create:
        mock_create.side_effect = stripe.error.CardError(
            "Card declined",
            param="card",
            code="card_declined",
        )

        with pytest.raises(PaymentFailedError):
            await process_payment(amount=100, currency="usd")
```

---

## 🎯 Test-Driven Development Workflow

### Example: Adding JWT Refresh Token Support

#### Step 1: Write the Test First

```python
@pytest.mark.anyio
async def test_refresh_token_returns_new_access_token():
    """Test that refresh token generates new access token."""
    # Arrange
    user = await create_test_user()
    refresh_token = create_refresh_token(user.id)

    # Act
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify new token is valid
    new_token = data["access_token"]
    payload = decode_jwt(new_token)
    assert payload["sub"] == str(user.id)


@pytest.mark.anyio
async def test_expired_refresh_token_returns_401():
    """Test that expired refresh token is rejected."""
    expired_token = create_refresh_token(uuid4(), expires_in=-3600)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": expired_token},
    )

    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()
```

#### Step 2: Run Test (Watch It Fail)

```bash
pytest tests/api/test_auth_endpoints.py::test_refresh_token_returns_new_access_token -xvs

# Expected: FAILED (endpoint doesn't exist yet)
```

#### Step 3: Implement Minimal Code

```python
@router.post("/auth/refresh")
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh access token using refresh token."""
    # Decode and validate refresh token
    try:
        payload = jwt.decode(
            refresh_request.refresh_token,
            settings.jwt_secret,
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Load user from DB
    user_id = UUID(payload["sub"])
    user = await load_user_from_db(user_id, db, require_active=True)

    # Generate new access token
    access_token = create_access_token(user.id)

    return TokenResponse(access_token=access_token, token_type="bearer")
```

#### Step 4: Run Test Again (Should Pass)

```bash
pytest tests/api/test_auth_endpoints.py::test_refresh_token_returns_new_access_token -xvs

# Expected: PASSED
```

#### Step 5: Refactor with Confidence

```python
# Extract JWT validation to shared helper
from prep.auth.core import decode_and_validate_jwt

@router.post("/auth/refresh")
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh access token using refresh token."""
    # Use shared helper (DRY)
    payload = decode_and_validate_jwt(
        refresh_request.refresh_token,
        settings.jwt_secret,
        audience="refresh",  # Different audience for refresh tokens
    )

    user_id = UUID(payload["sub"])
    user = await load_user_from_db(user_id, db, require_active=True)

    access_token = create_access_token(user.id)

    return TokenResponse(access_token=access_token, token_type="bearer")
```

#### Step 6: Run All Tests

```bash
pytest tests/api/test_auth_endpoints.py -xvs

# Ensure refactoring didn't break anything
```

---

## 📊 Coverage Reporting

### Generate Coverage Report

```bash
# Run tests with coverage
pytest tests/ --cov=prep --cov-report=html --cov-report=term-missing

# View coverage report
open htmlcov/index.html
```

### Required Coverage Levels

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
addopts = """
    --cov=prep
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=80
    --strict-markers
    -ra
"""

# Enforce 100% coverage on critical modules
[tool.coverage.report]
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]

[tool.coverage.run]
source = ["prep"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/venv/*",
]
```

---

## 🚀 Test Execution Commands

```bash
# Run all tests
pytest tests/ -xvs

# Run specific test file
pytest tests/auth/test_core_helpers.py -xvs

# Run specific test
pytest tests/auth/test_core_helpers.py::test_decode_valid_jwt -xvs

# Run tests matching pattern
pytest tests/ -k "jwt" -xvs

# Run tests with coverage
pytest tests/ --cov=prep --cov-report=term-missing

# Run only failed tests from last run
pytest tests/ --lf

# Run tests in parallel (with pytest-xdist)
pytest tests/ -n auto

# Stop on first failure
pytest tests/ -x

# Show print statements
pytest tests/ -s

# Extra verbose
pytest tests/ -vv
```

---

## 📋 Testing Checklist

Before committing any code:

- [ ] Tests written for new functionality
- [ ] Tests updated for modified functionality
- [ ] All tests passing locally
- [ ] Coverage meets threshold (80%+ overall, 100% for security-critical)
- [ ] Edge cases tested (empty input, null, max values, etc.)
- [ ] Error cases tested (404, 403, 401, 409, etc.)
- [ ] Async tests use `@pytest.mark.anyio`
- [ ] External services mocked
- [ ] Test names are descriptive
- [ ] No flaky tests (tests pass consistently)

---

**Last updated**: 2025-01-16
**Philosophy**: If it's not tested, it's broken. If it's security-critical, it needs 100% coverage.
