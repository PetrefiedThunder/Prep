# Python Development Agent

**Role**: Modern Python 3.11+ development patterns and best practices
**Priority**: High
**Scope**: All Python code in the repository

---

## 🎯 Core Responsibilities

### Language Features
- Use Python 3.11+ features (match/case, exception groups, task groups)
- Type hints on ALL function signatures and class attributes
- Modern async/await patterns for I/O operations
- Dataclasses or Pydantic models for structured data
- Context managers (`with`, `async with`) for resource management

### Package Management
- Use `uv` for fast package resolution when available
- Pin exact versions in `requirements.txt` for production
- Use `requirements-dev.txt` for development dependencies
- Document optional dependencies with extras (e.g., `pip install -e ".[dev,test]"`)

### Code Organization
- One class or related functions per module
- Keep modules under 500 lines (split if larger)
- Use `__all__` to define public API
- Organize imports: stdlib → third-party → local

---

## ✅ Required Patterns

### Modern Python Syntax

```python
from __future__ import annotations  # REQUIRED: Always first import

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class User(BaseModel):
    """User model with validation."""

    id: UUID = Field(default_factory=uuid4)
    email: str = Field(..., min_length=3, max_length=255)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = True


async def load_users(
    *,
    limit: int = 100,
    offset: int = 0,
    active_only: bool = True,
) -> Sequence[User]:
    """Load users with pagination.

    Args:
        limit: Maximum number of users to return
        offset: Number of users to skip
        active_only: If True, return only active users

    Returns:
        Sequence of User instances

    Raises:
        ValueError: If limit is negative or zero
    """
    if limit <= 0:
        raise ValueError("limit must be positive")

    # Implementation...
```

### Async/Await Patterns

```python
# ✅ GOOD: Proper async patterns
import asyncio
from collections.abc import AsyncIterator

async def fetch_data(url: str) -> dict[str, Any]:
    """Fetch data asynchronously."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def process_batch(items: list[str]) -> list[dict]:
    """Process multiple items concurrently."""
    tasks = [fetch_data(item) for item in items]
    return await asyncio.gather(*tasks, return_exceptions=True)


async def stream_results() -> AsyncIterator[dict]:
    """Stream results as they arrive."""
    async for item in fetch_paginated_data():
        yield process_item(item)
```

### Error Handling

```python
# ✅ GOOD: Specific exceptions with context
class UserNotFoundError(Exception):
    """Raised when a user cannot be found."""

    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        super().__init__(f"User {user_id} not found")


async def get_user(user_id: UUID) -> User:
    """Get user by ID.

    Raises:
        UserNotFoundError: If user does not exist
        DatabaseError: If database query fails
    """
    try:
        return await db.query(User).where(User.id == user_id).one()
    except NoResultFound as exc:
        raise UserNotFoundError(user_id) from exc
```

### Resource Management

```python
# ✅ GOOD: Context managers for cleanup
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

@asynccontextmanager
async def database_session() -> AsyncIterator[AsyncSession]:
    """Provide a transactional database session."""
    session = SessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# Usage
async with database_session() as session:
    user = await load_user(session, user_id)
    user.email = new_email
    # Automatically commits on success, rolls back on error
```

---

## ❌ Anti-Patterns to Avoid

### Type Hints

```python
# ❌ BAD: No type hints
def process_data(data):
    return data.get("value")

# ✅ GOOD: Full type hints
def process_data(data: dict[str, Any]) -> Any:
    return data.get("value")
```

### Datetime Handling

```python
# ❌ BAD: Naive datetime
from datetime import datetime
now = datetime.now()  # Timezone-naive!

# ✅ GOOD: Timezone-aware
from datetime import UTC, datetime
now = datetime.now(UTC)
```

### Path Handling

```python
# ❌ BAD: String manipulation
import os
path = os.path.join("prep", "data", "file.txt")
if os.path.exists(path):
    with open(path) as f:
        ...

# ✅ GOOD: pathlib
from pathlib import Path
path = Path("prep") / "data" / "file.txt"
if path.exists():
    with path.open() as f:
        ...
```

### Blocking I/O in Async

```python
# ❌ BAD: Blocking call in async function
async def slow_function():
    time.sleep(5)  # Blocks entire event loop!
    return data

# ✅ GOOD: Non-blocking
async def fast_function():
    await asyncio.sleep(5)  # Allows other tasks to run
    return data
```

### Mutability Pitfalls

```python
# ❌ BAD: Mutable default arguments
def add_item(item: str, items: list[str] = []) -> list[str]:
    items.append(item)
    return items

# ✅ GOOD: None with conditional initialization
def add_item(item: str, items: list[str] | None = None) -> list[str]:
    if items is None:
        items = []
    items.append(item)
    return items
```

---

## 🧪 Testing Standards

### Pytest Patterns

```python
import pytest
from collections.abc import AsyncGenerator
from uuid import uuid4

# ✅ GOOD: Fixtures with proper typing
@pytest.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.anyio
async def test_user_creation(db_session: AsyncSession):
    """Test that users can be created."""
    user = User(email="test@example.com")
    db_session.add(user)
    await db_session.flush()

    assert user.id is not None
    assert user.created_at is not None
```

### Parametrized Tests

```python
@pytest.mark.parametrize(
    "email,expected_valid",
    [
        ("user@example.com", True),
        ("invalid-email", False),
        ("", False),
        ("a" * 256 + "@example.com", False),
    ],
)
def test_email_validation(email: str, expected_valid: bool):
    """Test email validation with various inputs."""
    if expected_valid:
        User(email=email)  # Should not raise
    else:
        with pytest.raises(ValidationError):
            User(email=email)
```

---

## 📚 Documentation Standards

### Docstring Format (Google Style)

```python
def complex_function(
    param1: str,
    param2: int,
    *,
    optional: bool = False,
) -> dict[str, Any]:
    """One-line summary of the function.

    More detailed explanation of what the function does,
    including any important implementation details or caveats.

    Args:
        param1: Description of param1
        param2: Description of param2
        optional: Whether to enable optional behavior. Defaults to False.

    Returns:
        Dictionary containing the results with the following keys:
        - "status": Operation status ("success" or "error")
        - "data": The processed data

    Raises:
        ValueError: If param2 is negative
        TypeError: If param1 is not a string

    Examples:
        >>> result = complex_function("test", 42)
        >>> result["status"]
        'success'
    """
```

### Module-Level Documentation

```python
"""User management utilities.

This module provides functions for creating, retrieving, updating,
and deleting users in the system. All operations are async and
require a database session.

Typical usage:
    async with database_session() as session:
        user = await create_user(session, email="user@example.com")
        await update_user(session, user.id, {"is_active": False})
"""

from __future__ import annotations

# ... rest of module
```

---

## 🔧 Tools Integration

### Black Formatting
```bash
# Format all Python files
black prep/ tests/ --line-length 100

# Check without modifying
black prep/ tests/ --check
```

### Ruff Linting
```bash
# Run all checks
ruff check prep/ tests/

# Auto-fix safe issues
ruff check prep/ tests/ --fix
```

### Mypy Type Checking
```bash
# Type check with strict mode
mypy prep/ --strict --show-error-codes
```

### Import Sorting
```bash
# Sort imports (Black-compatible)
isort prep/ tests/ --profile black
```

---

## 🚀 Performance Considerations

### Async Concurrency

```python
# ✅ GOOD: Concurrent execution
async def fetch_all_data(user_ids: list[UUID]) -> list[User]:
    """Fetch multiple users concurrently."""
    tasks = [fetch_user(uid) for uid in user_ids]
    return await asyncio.gather(*tasks)

# ❌ BAD: Sequential execution
async def fetch_all_data_slow(user_ids: list[UUID]) -> list[User]:
    """Fetch users one by one (slow!)."""
    results = []
    for uid in user_ids:
        user = await fetch_user(uid)
        results.append(user)
    return results
```

### Generator Expressions

```python
# ✅ GOOD: Memory-efficient
def process_large_file(path: Path) -> int:
    """Count lines without loading entire file."""
    return sum(1 for _ in path.open())

# ❌ BAD: Memory-intensive
def process_large_file_slow(path: Path) -> int:
    """Load entire file into memory."""
    return len(path.read_text().splitlines())
```

---

## 📋 Checklist for Every Change

- [ ] `from __future__ import annotations` is first import
- [ ] All functions have type hints
- [ ] All public functions have docstrings
- [ ] Using `datetime.now(UTC)` not `datetime.now()`
- [ ] Using `pathlib.Path` not string paths
- [ ] Async functions use `await` not blocking calls
- [ ] Context managers used for resource cleanup
- [ ] Proper exception handling with specific types
- [ ] Tests written and passing
- [ ] Code formatted with Black
- [ ] Linter (Ruff) passes
- [ ] Type checker (mypy) passes

---

**Last updated**: 2025-01-16
**Next review**: After Python 3.12+ migration
