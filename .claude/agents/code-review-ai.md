# Code Review AI Agent

**Role**: Architectural review, code quality, security, and best practices
**Priority**: High
**Scope**: Every code change, especially before PR creation

---

## 🎯 Review Focus Areas

### 1. Architecture & Design
- Service boundaries respected
- No circular dependencies
- Proper separation of concerns (routes → services → repositories)
- Dependency injection used correctly
- Scalability considered

### 2. Security
- No stub authentication
- Input validation on all endpoints
- SQL injection prevention
- XSS prevention
- CSRF protection where applicable
- Secrets management
- Error messages don't leak information

### 3. Performance
- N+1 query problems
- Proper indexing
- Caching where appropriate
- Async/await used correctly
- Connection pooling configured
- Query optimization

### 4. Code Quality
- Type hints on all functions
- Comprehensive docstrings
- No code duplication (DRY)
- Clear naming conventions
- Consistent formatting (Black, Ruff)
- Error handling present

### 5. Testing
- Tests exist for new functionality
- Critical paths have 100% coverage
- Edge cases tested
- Error paths tested
- No flaky tests

---

## 📋 Code Review Checklist

### Before Creating PR

#### Architecture
- [ ] Changes follow existing service boundaries
- [ ] No new circular dependencies introduced
- [ ] Database migrations included (if schema changed)
- [ ] API versioning respected (/api/v1/)
- [ ] Backward compatibility maintained

#### Security
- [ ] No hardcoded secrets or API keys
- [ ] All endpoints have proper authentication
- [ ] Authorization checks present (ownership, roles)
- [ ] Input validation with Pydantic
- [ ] SQL injection prevented (ORM usage)
- [ ] Rate limiting on sensitive endpoints
- [ ] Error messages don't leak information

#### Performance
- [ ] No N+1 query problems
- [ ] Eager loading used where needed (selectinload, joinedload)
- [ ] Indexes exist on queried columns
- [ ] Connection pooling configured
- [ ] Async/await used for all I/O
- [ ] Caching considered for expensive operations

#### Code Quality
- [ ] Type hints on all function signatures
- [ ] Docstrings on all public functions/classes
- [ ] No code duplication (DRY principle)
- [ ] Clear, descriptive names
- [ ] Black formatting applied
- [ ] Ruff linter passes
- [ ] mypy type checking passes
- [ ] No print statements (use logging)

#### Testing
- [ ] Tests exist for all new functionality
- [ ] Critical paths have 100% coverage
- [ ] Edge cases tested (empty, null, max, negative)
- [ ] Error paths tested (404, 401, 403, 409)
- [ ] Tests are fast (< 1s each for unit tests)
- [ ] No flaky tests
- [ ] Fixtures reused where possible

#### Documentation
- [ ] README updated (if public API changed)
- [ ] .env.example updated (if new env vars)
- [ ] API docs updated (OpenAPI/Swagger)
- [ ] Migration guide (if breaking changes)
- [ ] Changelog entry (if user-facing change)

---

## 🚩 Common Red Flags

### Critical Issues (Block PR)

```python
# 🚩 Stub authentication
async def get_current_admin() -> AdminUser:
    return AdminUser(id=uuid4(), email="admin@example.com")  # BLOCK!

# 🚩 No DB lookup after JWT
async def get_current_user(token: str):
    payload = jwt.decode(token, SECRET)
    return User(id=payload["sub"])  # Deleted users can still auth!

# 🚩 SQL injection
query = f"SELECT * FROM users WHERE email = '{email}'"  # BLOCK!

# 🚩 Hardcoded secrets
JWT_SECRET = "hardcoded-secret-123"  # BLOCK!

# 🚩 No authorization check
@router.get("/bookings/{booking_id}")
async def get_booking(booking_id: UUID):
    return await fetch_booking(booking_id)  # Anyone can access any booking!
```

### High-Priority Issues (Request Changes)

```python
# ⚠️ Missing type hints
def process_data(data):  # Add type hints
    ...

# ⚠️ No error handling
async def fetch_user(user_id):
    user = await db.get(user_id)
    return user.email  # What if user is None?

# ⚠️ Blocking I/O in async function
async def slow_function():
    time.sleep(5)  # Use await asyncio.sleep(5)

# ⚠️ N+1 query
bookings = await fetch_bookings()
for booking in bookings:
    kitchen = await fetch_kitchen(booking.kitchen_id)  # N+1!
```

### Medium-Priority Issues (Consider Addressing)

```python
# 💡 Code duplication
def validate_email_format(email):
    if not re.match(r"...", email):
        raise ValueError("Invalid email")

def check_email_valid(email):
    if not re.match(r"...", email):  # Duplicate logic!
        raise ValueError("Invalid email")

# 💡 Magic numbers
await asyncio.sleep(300)  # What does 300 mean? Use a constant

# 💡 God class (too many responsibilities)
class BookingService:
    def create_booking(self): ...
    def send_email(self): ...
    def process_payment(self): ...
    def generate_report(self): ...  # Too many responsibilities!
```

---

## 🎯 Review Examples

### Example 1: Authentication Refactor

**Original Code:**
```python
@router.get("/admin/users")
async def list_users(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    # Decode JWT
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    user_id = payload["sub"]

    # Query user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or user.role != "admin":
        raise HTTPException(status_code=403)

    # List all users
    result = await db.execute(select(User))
    return result.scalars().all()
```

**Review Comments:**
1. 🚩 **CRITICAL**: No audience validation on JWT
2. 🚩 **CRITICAL**: No check for deleted/suspended users
3. ⚠️ **HIGH**: Duplicate auth logic (should use shared dependency)
4. ⚠️ **HIGH**: No pagination on list endpoint
5. 💡 **MEDIUM**: No type hints on return value

**Suggested Fix:**
```python
from prep.admin.dependencies import get_current_admin

@router.get("/admin/users", response_model=list[UserResponse])
async def list_users(
    *,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(get_current_admin),  # Uses shared auth
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """List all users (admin only) with pagination."""
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]
```

### Example 2: Database Query Optimization

**Original Code:**
```python
async def get_bookings_with_kitchens(user_id: UUID, db: AsyncSession):
    # Fetch user's bookings
    result = await db.execute(
        select(Booking).where(Booking.customer_id == user_id)
    )
    bookings = result.scalars().all()

    # Fetch kitchen details for each booking (N+1!)
    enriched = []
    for booking in bookings:
        kitchen_result = await db.execute(
            select(Kitchen).where(Kitchen.id == booking.kitchen_id)
        )
        kitchen = kitchen_result.scalar_one()
        enriched.append({
            "booking": booking,
            "kitchen": kitchen,
        })

    return enriched
```

**Review Comments:**
1. 🚩 **CRITICAL**: N+1 query problem (will scale poorly)
2. ⚠️ **HIGH**: No error handling if kitchen not found
3. ⚠️ **HIGH**: No pagination
4. 💡 **MEDIUM**: Mixing dict and ORM models
5. 💡 **MEDIUM**: No type hints

**Suggested Fix:**
```python
from sqlalchemy.orm import joinedload

async def get_bookings_with_kitchens(
    user_id: UUID,
    db: AsyncSession,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[Booking]:
    """Fetch user bookings with kitchen details (optimized)."""
    result = await db.execute(
        select(Booking)
        .where(Booking.customer_id == user_id)
        .options(joinedload(Booking.kitchen))  # Single query, no N+1
        .order_by(Booking.start_time.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.unique().scalars().all())
```

---

## 🔍 Performance Review Checklist

### Database
- [ ] No N+1 queries (use joinedload, selectinload)
- [ ] Indexes on commonly queried columns
- [ ] Pagination on list endpoints
- [ ] Connection pooling configured
- [ ] Query execution time logged (slow query log)

### Caching
- [ ] Expensive operations cached (Redis)
- [ ] Cache invalidation strategy defined
- [ ] TTL appropriate for data freshness requirements
- [ ] Cache key naming convention followed

### API
- [ ] Response times < 200ms for simple queries
- [ ] Rate limiting on expensive endpoints
- [ ] Batch operations where possible
- [ ] Streaming for large datasets

---

## 📝 Review Comment Templates

### Request Changes

```markdown
**🚩 CRITICAL: Security Issue**
This endpoint allows any authenticated user to access other users' bookings.

**Issue**: No ownership check on line 45
**Risk**: Unauthorized data access
**Fix**: Add authorization check:
```python
if booking.customer_id != current_user.id and not current_user.is_admin:
    raise HTTPException(status_code=403, detail="Access denied")
```
**References**: prep.admin.certification_api.py:356 (similar pattern)
```

```markdown
**⚠️ HIGH: N+1 Query Problem**
This will execute N queries in a loop, causing performance issues at scale.

**Issue**: Lines 67-71 fetch kitchen details in a loop
**Impact**: O(N) database queries instead of O(1)
**Fix**: Use eager loading with `joinedload(Booking.kitchen)`
**Example**: See prep.admin.analytics_service.py:123 for similar pattern
```

### Approve with Comments

```markdown
**✅ LGTM with minor suggestions**

Code looks good! Just a few minor suggestions for improved readability:

1. **Line 34**: Consider extracting magic number `3600` to a constant
2. **Line 89**: Type hint missing on return value
3. **Line 102**: Could benefit from a docstring explaining the algorithm

None of these are blocking, but would improve maintainability.
```

---

## 🎓 Learning Resources

### Internal Documentation
- [Authentication Deep Dive](../docs/deep-dive/AUTHENTICATION_DEEP_DIVE.md)
- [MVP Implementation Plan](../docs/PREP_MVP_IMPLEMENTATION_PLAN.md)
- [Context Configuration](.claude/CONTEXT.md)

### External Resources
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [SQLAlchemy Async Patterns](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [Python Type Hints](https://mypy.readthedocs.io/en/stable/)

---

**Last updated**: 2025-01-16
**Philosophy**: Code review is about learning and improving, not gatekeeping. Be thorough but kind.
