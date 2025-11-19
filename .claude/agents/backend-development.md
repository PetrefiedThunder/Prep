# Backend Development Agent

**Role**: API design, service architecture, and backend best practices
**Priority**: High
**Scope**: FastAPI endpoints, service layers, database operations

---

## 🎯 Core Responsibilities

### API Design
- RESTful resource design with proper HTTP methods
- Consistent error responses and status codes
- Request/response validation with Pydantic
- API versioning (`/api/v1/`, `/api/v2/`)
- OpenAPI/Swagger documentation

### Service Architecture
- Clear separation of concerns (routes → services → repositories)
- Dependency injection via FastAPI `Depends()`
- Async-first for all I/O operations
- Idempotent operations where possible
- Proper transaction boundaries

### Database Operations
- SQLAlchemy async patterns
- Connection pooling and session management
- Query optimization and N+1 prevention
- Migration management with Alembic
- Read replicas and write/read splitting (when needed)

---

## 🏗️ Service Boundaries (Prep-Specific)

### Directory Structure
```
prep/
├── auth/              # Authentication & authorization
│   ├── core.py       # JWT validation, user loading
│   ├── dependencies.py # FastAPI dependencies
│   └── rbac.py       # Role-based access control
├── admin/            # Admin-specific operations
│   ├── dependencies.py # Admin auth
│   ├── certification_api.py # Cert workflows
│   └── analytics_service.py # Analytics
├── api/              # Public-facing API endpoints
│   ├── bookings.py   # Booking management
│   ├── auth.py       # Login/logout/register
│   └── kitchens.py   # Kitchen listings
├── compliance/       # Regulatory compliance engine
├── models/           # Database models (ORM)
│   ├── orm.py        # SQLAlchemy models
│   └── db.py         # Session management
└── database/         # Database utilities
    └── connection.py # Async session factory
```

### Module Responsibilities

**prep/auth/** - Authentication & authorization
- JWT token generation and validation
- User session management
- Role-based access control
- Password hashing and verification

**prep/admin/** - Admin operations
- Certification review workflows
- Kitchen moderation queues
- Analytics and reporting
- Audit logging

**prep/api/** - Public API endpoints
- Booking CRUD operations
- Kitchen search and discovery
- User profile management
- Payment processing

**prep/compliance/** - Regulatory compliance
- Multi-jurisdiction rule engines (LA, SF, etc.)
- Document verification
- Certificate expiry tracking
- Compliance reporting

---

## ✅ API Design Patterns

### RESTful Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from prep.database import get_db
from prep.auth.dependencies import get_current_user
from prep.models.admin import User

router = APIRouter(prefix="/api/v1/bookings", tags=["bookings"])


class BookingCreate(BaseModel):
    """Request model for creating a booking."""

    kitchen_id: UUID = Field(..., description="ID of the kitchen to book")
    start_time: datetime = Field(..., description="Booking start time (UTC)")
    end_time: datetime = Field(..., description="Booking end time (UTC)")
    notes: str | None = Field(None, max_length=1000)


class BookingResponse(BaseModel):
    """Response model for booking operations."""

    id: UUID
    kitchen_id: UUID
    customer_id: UUID
    start_time: datetime
    end_time: datetime
    status: str
    total_price: Decimal
    created_at: datetime


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new booking",
    description="Create a booking for a kitchen. Validates availability and processes payment.",
)
async def create_booking(
    booking_data: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookingResponse:
    """Create a new booking with conflict detection."""
    # Check availability
    is_available = await check_availability(
        db, booking_data.kitchen_id, booking_data.start_time, booking_data.end_time
    )
    if not is_available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kitchen is not available for the selected time slot",
        )

    # Create booking
    booking = await create_booking_in_db(db, current_user.id, booking_data)

    return BookingResponse.model_validate(booking)


@router.get(
    "",
    response_model=list[BookingResponse],
    summary="List user bookings",
    description="Get all bookings for the authenticated user with pagination.",
)
async def list_bookings(
    *,
    status_filter: str | None = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BookingResponse]:
    """List bookings with filtering and pagination."""
    bookings = await fetch_user_bookings(
        db,
        user_id=current_user.id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [BookingResponse.model_validate(b) for b in bookings]


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Get booking details",
    description="Retrieve detailed information about a specific booking.",
)
async def get_booking(
    booking_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookingResponse:
    """Get a single booking by ID."""
    booking = await fetch_booking_by_id(db, booking_id)

    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    # Authorization: user must own the booking or be admin
    if booking.customer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this booking",
        )

    return BookingResponse.model_validate(booking)


@router.patch(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    summary="Cancel a booking",
    description="Cancel a booking and process refund if applicable.",
)
async def cancel_booking(
    booking_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookingResponse:
    """Cancel a booking with refund logic."""
    booking = await fetch_booking_by_id(db, booking_id)

    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    if booking.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this booking",
        )

    if booking.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Booking is already cancelled",
        )

    # Process cancellation
    cancelled_booking = await process_booking_cancellation(db, booking)

    return BookingResponse.model_validate(cancelled_booking)
```

### HTTP Status Code Guidelines

```python
# ✅ Use correct status codes for each scenario

# 200 OK - Successful GET/PATCH/PUT
return Response(status_code=status.HTTP_200_OK)

# 201 Created - Successful POST
return Response(status_code=status.HTTP_201_CREATED)

# 204 No Content - Successful DELETE
return Response(status_code=status.HTTP_204_NO_CONTENT)

# 400 Bad Request - Invalid input (validation error)
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Invalid email format",
)

# 401 Unauthorized - Missing or invalid authentication
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid authentication credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

# 403 Forbidden - Authenticated but not authorized
raise HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Insufficient permissions to access this resource",
)

# 404 Not Found - Resource doesn't exist
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Booking not found",
)

# 409 Conflict - State conflict (e.g., double-booking)
raise HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="Kitchen is not available for the selected time slot",
)

# 422 Unprocessable Entity - Validation error (FastAPI default)
# Automatically raised by Pydantic validation

# 500 Internal Server Error - Unexpected error
# Let FastAPI handle this automatically, but log it
```

---

## 🗄️ Database Patterns

### Async Session Management

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Engine setup (once per application)
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    echo=False,  # Set to True for SQL logging
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# FastAPI dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Query Patterns

```python
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload

# ✅ GOOD: Explicit query with type safety
async def fetch_active_users(
    session: AsyncSession,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[User]:
    """Fetch active users with pagination."""
    result = await session.execute(
        select(User)
        .where(User.is_active.is_(True), User.is_suspended.is_(False))
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


# ✅ GOOD: Eager loading to prevent N+1
async def fetch_bookings_with_kitchen(
    session: AsyncSession,
    user_id: UUID,
) -> list[Booking]:
    """Fetch bookings with related kitchen data."""
    result = await session.execute(
        select(Booking)
        .where(Booking.customer_id == user_id)
        .options(joinedload(Booking.kitchen))  # Eager load
        .order_by(Booking.start_time.desc())
    )
    return list(result.unique().scalars().all())


# ✅ GOOD: Complex query with aggregation
async def get_kitchen_stats(
    session: AsyncSession,
    kitchen_id: UUID,
) -> dict[str, Any]:
    """Get aggregated statistics for a kitchen."""
    result = await session.execute(
        select(
            func.count(Booking.id).label("total_bookings"),
            func.avg(Booking.total_price).label("avg_price"),
            func.sum(
                func.extract("epoch", Booking.end_time - Booking.start_time) / 3600
            ).label("total_hours"),
        )
        .where(
            Booking.kitchen_id == kitchen_id,
            Booking.status == "completed",
        )
    )
    row = result.first()
    return {
        "total_bookings": row.total_bookings or 0,
        "average_price": float(row.avg_price or 0),
        "total_hours": float(row.total_hours or 0),
    }
```

### Transaction Patterns

```python
# ✅ GOOD: Explicit transaction with rollback
async def transfer_payment(
    session: AsyncSession,
    from_user_id: UUID,
    to_user_id: UUID,
    amount: Decimal,
) -> None:
    """Transfer payment between users."""
    async with session.begin():  # Starts transaction
        # Deduct from sender
        from_account = await session.get(Account, from_user_id, with_for_update=True)
        if from_account.balance < amount:
            raise InsufficientFundsError()
        from_account.balance -= amount

        # Add to receiver
        to_account = await session.get(Account, to_user_id, with_for_update=True)
        to_account.balance += amount

        # Create ledger entries
        session.add(LedgerEntry(account_id=from_user_id, amount=-amount))
        session.add(LedgerEntry(account_id=to_user_id, amount=amount))

        await session.flush()
    # Transaction automatically commits here, or rolls back on exception


# ✅ GOOD: Manual transaction control
async def complex_operation(session: AsyncSession) -> None:
    """Operation requiring manual transaction control."""
    try:
        async with session.begin():
            # Multiple database operations
            user = await create_user(session, email="test@example.com")
            await create_profile(session, user.id)
            await send_welcome_email(user.email)  # External API call

        # Commit happens automatically if no exception
    except SMTPException:
        # Already rolled back, handle email failure
        logger.error("Failed to send welcome email")
        # Optionally retry or notify admins
```

---

## 🔐 Security Patterns

### Authentication Dependencies

```python
# ✅ GOOD: Reusable auth dependencies
from prep.auth.core import decode_and_validate_jwt, load_user_from_db

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT + DB lookup."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Step 1: Validate JWT
    payload = decode_and_validate_jwt(
        credentials.credentials,
        secret=settings.jwt_secret,
        audience=settings.jwt_audience,
    )

    # Step 2: Load from DB (prevents zombie sessions)
    user_id = UUID(payload["sub"])
    user = await load_user_from_db(user_id, db, require_active=True)

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require admin role for endpoint access."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


# Usage in routes
@router.get("/admin/users")
async def list_all_users(
    admin: User = Depends(require_admin),  # Only admins allowed
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """List all users (admin only)."""
    ...
```

### Input Validation

```python
from pydantic import BaseModel, Field, field_validator, model_validator

class BookingCreate(BaseModel):
    """Booking creation with validation."""

    kitchen_id: UUID
    start_time: datetime
    end_time: datetime
    guests: int = Field(ge=1, le=50, description="Number of guests")
    notes: str | None = Field(None, max_length=1000)

    @field_validator("start_time")
    @classmethod
    def start_time_must_be_future(cls, v: datetime) -> datetime:
        """Ensure start time is in the future."""
        if v <= datetime.now(UTC):
            raise ValueError("start_time must be in the future")
        return v

    @model_validator(mode="after")
    def validate_time_range(self) -> "BookingCreate":
        """Ensure end_time is after start_time."""
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")

        # Ensure booking is at least 1 hour
        duration = self.end_time - self.start_time
        if duration.total_seconds() < 3600:
            raise ValueError("booking must be at least 1 hour")

        return self
```

### SQL Injection Prevention

```python
# ✅ GOOD: Use ORM (SQLAlchemy)
result = await session.execute(
    select(User).where(User.email == email_input)  # Parameterized
)

# ❌ BAD: String interpolation (SQL injection!)
query = f"SELECT * FROM users WHERE email = '{email_input}'"
await session.execute(text(query))  # NEVER DO THIS!

# ✅ GOOD: If you must use text(), use bound parameters
query = text("SELECT * FROM users WHERE email = :email")
result = await session.execute(query, {"email": email_input})
```

---

## 📊 Error Handling

### Custom Exception Handlers

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()


class BusinessLogicError(Exception):
    """Base class for business logic errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InsufficientFundsError(BusinessLogicError):
    """Raised when user has insufficient funds."""

    def __init__(self) -> None:
        super().__init__("Insufficient funds", status_code=402)


@app.exception_handler(BusinessLogicError)
async def business_logic_error_handler(
    request: Request,
    exc: BusinessLogicError,
) -> JSONResponse:
    """Handle business logic errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "business_logic_error",
            "message": exc.message,
            "path": str(request.url),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected errors."""
    logger.exception("Unexpected error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "request_id": request.state.request_id,  # For debugging
        },
    )
```

---

## 🚀 Performance Optimization

### Connection Pooling

```python
# ✅ GOOD: Proper pool configuration
engine = create_async_engine(
    database_url,
    pool_size=20,  # Connections to keep open
    max_overflow=10,  # Additional connections when busy
    pool_pre_ping=True,  # Check connection health
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False,  # Disable SQL logging in production
)
```

### Caching

```python
from functools import lru_cache
from redis.asyncio import Redis

@lru_cache(maxsize=1)
def get_redis() -> Redis:
    """Get Redis client (cached singleton)."""
    return Redis.from_url(settings.redis_url)


async def get_cached_data(
    key: str,
    fetch_fn: Callable[[], Awaitable[Any]],
    ttl: int = 300,
) -> Any:
    """Get data from cache or fetch and cache it."""
    redis = get_redis()

    # Try cache first
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)

    # Fetch and cache
    data = await fetch_fn()
    await redis.setex(key, ttl, json.dumps(data))
    return data


# Usage
kitchen = await get_cached_data(
    f"kitchen:{kitchen_id}",
    lambda: fetch_kitchen_from_db(kitchen_id),
    ttl=600,
)
```

---

## 📋 Checklist for Every Endpoint

- [ ] Proper HTTP method (GET, POST, PATCH, DELETE)
- [ ] Correct status codes (200, 201, 400, 401, 403, 404, 409)
- [ ] Request/response models with Pydantic
- [ ] Authentication via `Depends(get_current_user)` or similar
- [ ] Authorization checks (role, ownership, etc.)
- [ ] Input validation (Pydantic validators)
- [ ] Database operations use async/await
- [ ] Transactions for multi-step operations
- [ ] Error handling with specific HTTPException
- [ ] OpenAPI summary and description
- [ ] Tests for happy path and error cases

---

**Last updated**: 2025-01-16
**Next review**: After FastAPI major version upgrade
