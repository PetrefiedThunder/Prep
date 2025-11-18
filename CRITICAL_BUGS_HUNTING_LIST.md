# Critical Bugs Hunting List

**Status**: Active Bug Hunt in Progress
**Last Updated**: 2025-11-15
**Total Issues**: 17 (3 Critical, 5 High, 9 Medium)
**Document Purpose**: Comprehensive technical bug list for active hunting and remediation

---

## Executive Summary

This document provides a detailed technical specification for all identified bugs that are blocking production readiness. Each issue includes:
- Exact code location with line numbers
- Reproduction steps and conditions
- Proof of concept demonstrating the issue
- Technical impact and failure modes
- Recommended fix with code examples
- Test cases to validate the fix

**Priority Ranking**:
- 🔴 **CRITICAL**: Data loss, security breaches, silent failures
- 🔴 **HIGH**: Feature breakage, resource leaks, validation bypasses
- 🟡 **MEDIUM**: Performance issues, partial functionality, code quality

---

## 🔴 CRITICAL Bugs

### BUG-001: Duplicate Function Definition Causes Endpoint Failure

**Location**: `prep/admin/certification_api.py:289, 321`
**Severity**: CRITICAL
**Category**: Code Correctness / Type Safety

#### Description

Two `async def get_current_admin()` functions are defined in the same file. The second definition (line 321) completely shadows/overrides the first definition (line 289), making the first implementation inaccessible and potentially breaking endpoints that depend on the first definition's field structure.

#### Code Location

```python
# prep/admin/certification_api.py

# First definition (line 289-296)
async def get_current_admin() -> AdminUser:
    """First implementation"""
    return AdminUser(
        id=user.id,
        email=user.email,
        name=user.full_name,
    )

# Second definition (line 321-329) - OVERRIDES FIRST
async def get_current_admin() -> AdminUser:
    """Second implementation with different fields"""
    return AdminUser(
        id=admin.id,
        email=admin.email,
        full_name=admin.full_name,  # Different field name!
        permissions=admin.permissions,
    )
```

#### Impact

- Any dependency injection using `Depends(get_current_admin)` will use the second definition
- If first definition is referenced anywhere, it will fail at runtime with `NameError` or wrong field names
- Type mismatch between code expecting `name` vs `full_name` field
- Inconsistent behavior depending on call order

#### Reproduction Steps

1. Start API server
2. Call endpoint that uses `get_current_admin` dependency
3. Observe which implementation is actually called
4. Check if response contains `name` or `full_name` field

#### Root Cause

Duplicate function definition - Python's default behavior is to use the last definition when multiple functions with same name exist in same scope.

#### Fix Approach

**Option A: Consolidate into single definition**
```python
async def get_current_admin(
    session: Session = Depends(get_session),
    claims: TokenClaims = Depends(validate_jwt),
) -> AdminUser:
    """Single authoritative implementation"""
    admin = await session.get(Admin, claims.sub)
    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found")

    return AdminUser(
        id=admin.id,
        email=admin.email,
        name=admin.full_name,  # Choose consistent field names
        permissions=admin.permissions,
    )
```

**Option B: Separate by purpose**
```python
@app.get("/api/admin/me")
async def get_current_admin_info(
    admin: AdminUser = Depends(get_current_admin),
) -> AdminResponse:
    """Get current admin's own information"""
    return AdminResponse.from_model(admin)

@app.get("/api/admin/{admin_id}")
async def get_admin_by_id(
    admin_id: UUID,
    session: Session = Depends(get_session),
) -> AdminResponse:
    """Get specific admin by ID"""
    admin = await session.get(Admin, admin_id)
    return AdminResponse.from_model(admin)
```

#### Testing Strategy

```python
def test_get_current_admin_returns_correct_fields():
    """Verify correct fields are returned"""
    admin = await get_current_admin(session, claims)
    assert hasattr(admin, "name")  # Not full_name
    assert admin.name == "John Doe"

def test_get_current_admin_in_dependency():
    """Verify dependency injection works"""
    client = TestClient(app)
    response = client.get(
        "/api/admin/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "name" in response.json()
```

---

### BUG-002: Race Condition in Idempotency Middleware

**Location**: `prep/api/middleware/idempotency.py:55-71`
**Severity**: CRITICAL
**Category**: Concurrency / Distributed Systems

#### Description

The idempotency middleware uses a non-atomic check-then-set pattern for Redis operations, creating a race condition window where concurrent requests with identical idempotency keys can both pass the check and proceed to create duplicate operations.

#### Code Location

```python
# prep/api/middleware/idempotency.py (lines 55-71)

async def idempotency_middleware(request: Request, call_next):
    idempotency_key = request.headers.get("Idempotency-Key")

    if not idempotency_key:
        return await call_next(request)

    # LINE 55: CHECK - Not atomic!
    cached_response = redis.get(f"idempotency:{idempotency_key}")

    if cached_response:
        # Return cached response
        return parse_cached_response(cached_response)

    # LINE 61-64: Request processing - can be interrupted here!
    response = await call_next(request)

    # LINE 71: SET - Separate Redis call!
    redis.set(
        f"idempotency:{idempotency_key}",
        serialize_response(response),
        ex=3600,  # 1 hour TTL
    )

    return response
```

#### Race Condition Window

**Timeline of concurrent requests with same idempotency key**:

```
Time  | Request A                          | Request B
------|------------------------------------|---------------------------------
T0    | get("idempotency:key123")         |
T1    | returns None ✓ proceed            |
T2    |                                    | get("idempotency:key123")
T3    |                                    | returns None ✓ proceed (RACE!)
T4    | Processing... booking.create()    |
T5    |                                    | Processing... booking.create()
T6    | Charge $100 ✓                     |
T7    |                                    | Charge $100 ✓ (DUPLICATE!)
T8    | set("idempotency:key123", ...)    |
T9    |                                    | set("idempotency:key123", ...)
```

#### Impact

- **Financial**: Duplicate charges for payment operations
- **Inventory**: Double booking of same time slot
- **Data Integrity**: Multiple entries created for single user action
- **Compliance**: Audit trail shows duplicates as separate operations

#### Reproduction Steps

1. Set up test client to send two concurrent requests with identical Idempotency-Key header
2. Configure network delay/latency between requests (simulates T0-T3 window)
3. Make concurrent POST requests to payment endpoint
4. Observe both requests proceed past idempotency check
5. Verify two charges created instead of one cached response

```python
async def test_idempotency_race_condition():
    """Reproduce race condition"""
    idempotency_key = str(uuid4())

    async def make_request():
        return client.post(
            "/api/bookings",
            headers={"Idempotency-Key": idempotency_key},
            json={"kitchen_id": kitchen_id, "hours": 2},
        )

    # Send two concurrent requests
    responses = await asyncio.gather(
        make_request(),
        make_request(),
    )

    # Both succeed - proves race condition
    assert responses[0].status_code == 200
    assert responses[1].status_code == 200

    # Check if duplicate booking created
    bookings = await session.query(Booking).filter_by(
        idempotency_key=idempotency_key
    ).all()

    assert len(bookings) == 2  # FAILS - shows race condition
```

#### Fix Approach

**Use Redis Lua script for atomic check-set**:

```python
# Redis Lua script for atomic idempotency check
IDEMPOTENCY_SCRIPT = """
-- Check if key exists and return cached value
local cached = redis.call("GET", KEYS[1])
if cached then
    return {"cached", cached}
end

-- Set a processing marker to prevent duplicates
redis.call("SET", KEYS[1], ARGV[1], "EX", ARGV[2])
return {"proceed", ""}
"""

async def idempotency_middleware(request: Request, call_next):
    idempotency_key = request.headers.get("Idempotency-Key")

    if not idempotency_key:
        return await call_next(request)

    # ATOMIC: Check and set processing marker in single Redis command
    redis_key = f"idempotency:{idempotency_key}"
    processing_marker = f"processing:{time.time()}:{uuid4()}"

    result = redis.eval(
        IDEMPOTENCY_SCRIPT,
        1,
        redis_key,
        processing_marker,
        "3600",  # TTL in seconds
    )

    if result[0] == "cached":
        # Return cached response immediately
        return Response(
            content=result[1],
            status_code=200,
            headers={"X-Idempotency-Cached": "true"},
        )

    # Process request
    response = await call_next(request)

    # Update cache with actual response
    redis.set(
        redis_key,
        serialize_response(response),
        ex=3600,
    )

    return response
```

#### Testing Strategy

```python
async def test_idempotency_prevents_duplicates():
    """Verify atomic idempotency check prevents duplicates"""
    idempotency_key = str(uuid4())

    # Send two rapid concurrent requests
    tasks = [
        client.post(
            "/api/payments",
            headers={"Idempotency-Key": idempotency_key},
            json={"amount": 10000},
        )
        for _ in range(2)
    ]

    responses = await asyncio.gather(*tasks)

    # First should process, second should return cached
    assert responses[0].status_code == 200
    assert responses[1].status_code == 200

    # Verify only one charge created
    charges = await stripe.Charge.list(limit=10)
    idempotency_charges = [
        c for c in charges if c.idempotency_key == idempotency_key
    ]
    assert len(idempotency_charges) == 1, "Race condition prevented ✓"
```

---

### BUG-003: Thread-Unsafe Global Stripe API Key

**Location**: `prep/payments/service.py:70`
**Severity**: CRITICAL
**Category**: Concurrency / Security

#### Description

The Stripe API key is set as a module-level global variable inside an async method, creating a race condition where concurrent payment operations with different API keys (e.g., test vs. live keys) can overwrite each other's keys, causing payments to be processed with the wrong account.

#### Code Location

```python
# prep/payments/service.py (line 70)

class PaymentsService:
    async def process_payment(
        self,
        amount: int,
        customer_id: str,
        stripe_api_key: str,
    ) -> PaymentResult:
        """Process payment with Stripe"""

        # LINE 70: UNSAFE! Global module state in async context
        stripe.api_key = stripe_api_key  # ❌ RACE CONDITION

        # Another concurrent request can change stripe.api_key here!

        try:
            charge = stripe.Charge.create(
                amount=amount,
                customer=customer_id,
                currency="usd",
            )
            return PaymentResult(success=True, charge_id=charge.id)
        except stripe.error.CardError as e:
            return PaymentResult(success=False, error=str(e))
```

#### Race Condition Window

**Timeline with two concurrent requests**:

```
Time | Request A (Test Key)              | Request B (Live Key)
-----|-----------------------------------|-----------------------
T0   | stripe.api_key = test_sk_123      |
T1   |                                    | stripe.api_key = live_sk_456
T2   |                                    | (overwrites Test key!)
T3   | stripe.Charge.create(...)         |
T4   | Uses live_sk_456 instead of test! |
T5   | Charge goes to wrong account!     |
```

#### Impact

**Financial & Security**:
- Payments charged to wrong Stripe account
- Cross-contamination between test and production environments
- Potential data breach if test keys used in production
- Audit trail shows charges from different accounts
- PCI-DSS compliance violation (insufficient access controls)

#### Reproduction Steps

```python
async def test_stripe_key_race_condition():
    """Reproduce stripe key race condition"""
    service = PaymentsService()

    results = await asyncio.gather(
        # Request A: Use test key
        service.process_payment(
            amount=10000,
            customer_id="cus_test_123",
            stripe_api_key="sk_test_abc123",
        ),
        # Request B: Use live key (concurrent)
        service.process_payment(
            amount=50000,
            customer_id="cus_live_456",
            stripe_api_key="sk_live_xyz789",
        ),
    )

    # Request A might have used wrong key
    # Check which Stripe account actually received the charge
    # If test_cus_123 charged to live account -> race condition confirmed
```

#### Fix Approach

**Pass API key per-request instead of setting globally**:

```python
# Fixed approach using Stripe client instances

class PaymentsService:
    async def process_payment(
        self,
        amount: int,
        customer_id: str,
        stripe_api_key: str,
    ) -> PaymentResult:
        """Process payment with Stripe - thread-safe"""

        try:
            # ✅ Create per-request Stripe client with explicit API key
            # (Stripe SDK supports per-request configuration)
            charge = stripe.Charge.create(
                amount=amount,
                customer=customer_id,
                currency="usd",
                api_key=stripe_api_key,  # ✅ Pass explicitly, no global state
            )
            return PaymentResult(success=True, charge_id=charge.id)
        except stripe.error.CardError as e:
            return PaymentResult(success=False, error=str(e))

# Alternative: Use context variable for async context isolation

import contextvars

_stripe_api_key_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "stripe_api_key"
)

class PaymentsService:
    async def process_payment(
        self,
        amount: int,
        customer_id: str,
        stripe_api_key: str,
    ) -> PaymentResult:
        """Process payment - thread-safe with ContextVar"""

        # ✅ Set API key in async context (not global scope)
        token = _stripe_api_key_ctx.set(stripe_api_key)

        try:
            # ✅ Each async task has isolated context
            api_key = _stripe_api_key_ctx.get()

            charge = stripe.Charge.create(
                amount=amount,
                customer=customer_id,
                currency="usd",
                api_key=api_key,
            )
            return PaymentResult(success=True, charge_id=charge.id)
        except stripe.error.CardError as e:
            return PaymentResult(success=False, error=str(e))
        finally:
            # ✅ Reset context
            _stripe_api_key_ctx.reset(token)
```

#### Testing Strategy

```python
@pytest.mark.asyncio
async def test_concurrent_payments_use_correct_keys():
    """Verify concurrent payments use correct Stripe keys"""
    service = PaymentsService()

    # Mock Stripe to track which key was used
    with patch("stripe.Charge.create") as mock_create:
        mock_create.return_value = MagicMock(id="ch_123")

        await asyncio.gather(
            service.process_payment(10000, "cus_test", "sk_test_123"),
            service.process_payment(20000, "cus_live", "sk_live_456"),
            service.process_payment(15000, "cus_test", "sk_test_789"),
        )

        # Verify each call used correct API key
        calls = mock_create.call_args_list
        assert calls[0][1]["api_key"] == "sk_test_123"
        assert calls[1][1]["api_key"] == "sk_live_456"
        assert calls[2][1]["api_key"] == "sk_test_789"
```

---

## 🔴 HIGH Severity Issues

### BUG-004: CORS Origin Whitespace Not Stripped

**Location**: `api/index.py:193-195`
**Severity**: HIGH
**Category**: Configuration / API Security

#### Description

CORS allowed origins are split by comma without stripping whitespace, causing origins with spaces in the environment variable to fail validation even though they are valid.

#### Code

```python
# api/index.py lines 193-195
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000"
).split(",")  # ❌ No strip() call!
```

#### Problem Scenario

```
Environment variable:
ALLOWED_ORIGINS="http://localhost:3000, http://localhost:8000"
                                       ^ space here

Result after split:
["http://localhost:3000", " http://localhost:8000"]
                         ^ leading space!

CORS validation:
request origin = "http://localhost:8000"
allowed = [" http://localhost:8000"]  # Leading space!
match = False  # CORS rejected!
```

#### Impact

- Frontend requests from valid origins rejected with CORS error
- Users see "blocked by CORS policy" in browser console
- Application unusable from valid frontend origins
- Difficult to debug since environment variable looks correct

#### Fix

```python
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000"
    ).split(",")
    if origin.strip()  # Also filter empty strings
]
```

---

### BUG-005: Unsafe Falsy Checks on Stripe Response Fields

**Location**: `prep/payments/service.py:77, 114`
**Severity**: HIGH
**Category**: Error Handling / Data Validation

#### Description

Code checks truthiness of Stripe response fields instead of explicitly checking `is None`. Valid Stripe responses with falsy ID values (empty string, `0`, `False`) incorrectly trigger error handling.

#### Code

```python
# prep/payments/service.py line 77
account_id = getattr(account, "id", None)
if not account_id:  # ❌ Falsy check!
    raise PaymentsError("Invalid account ID")

# More robust:
if account_id is None:  # ✅ Explicit None check
    raise PaymentsError("Invalid account ID")
```

---

### BUG-006: Incomplete DAG Implementation (NotImplementedError)

**Location**: `dags/foodcode_ingest.py:18, 32, 46`
**Severity**: HIGH
**Category**: Pipeline / ETL

#### Description

Three critical DAG tasks raise `NotImplementedError`, making the entire ETL pipeline non-functional.

#### Code

```python
# dags/foodcode_ingest.py

def _fetch_raw() -> pd.DataFrame:
    """Fetch raw foodcode data"""
    raise NotImplementedError("Implement FoodCode API fetching")

def _parse_docs() -> pd.DataFrame:
    """Parse documentation"""
    raise NotImplementedError("Implement parsing logic")

def _load_postgres() -> None:
    """Load into PostgreSQL"""
    raise NotImplementedError("Implement database loading")
```

#### Impact

- ETL pipeline fails immediately if executed
- Regulatory data not updated
- Compliance engine uses stale data
- Production deployment blocked

#### Fix

Implement the three functions or remove the incomplete DAG from the scheduled workflows.

---

### BUG-007: Silent Exception Handling in Audit Logger

**Location**: `middleware/audit_logger.py:61-63`
**Severity**: HIGH
**Category**: Security / Observability

#### Description

Bare `except:` block silently swallows all exceptions including system errors, preventing audit logging failures from being detected.

#### Code

```python
# middleware/audit_logger.py lines 61-63
except Exception:
    # The audit trail must never impact the customer request.
    pass  # ❌ Silent failure - no logging or metrics!
```

#### Fix

```python
except Exception as exc:
    # Log audit failure for investigation
    logger.warning(
        "Audit logging failed",
        exc_info=exc,
        extra={"path": path, "user_id": user_id},
    )
    # Emit metric for alerting
    metrics.increment("audit.logging.failure")
    # Don't block user request, but ensure visibility
```

---

### BUG-008: Stripe Webhook Idempotency Not Enforced

**Location**: `prep/payments/service.py` (webhook handler)
**Severity**: HIGH
**Category**: Payment Processing / Reliability

#### Description

Webhook handlers don't enforce idempotency, allowing duplicate Stripe webhook deliveries to create multiple database entries or charges.

#### Impact

- Duplicate booking confirmations
- Double charges if webhook retried
- Confusing audit trails with duplicate entries

#### Fix

Store webhook event IDs and check for duplicates before processing.

---

## 🟡 MEDIUM Severity Issues

### BUG-009: Potential N+1 Queries in Reconciliation

**Location**: `jobs/reconciliation_engine.py:102, 125, 149`
**Severity**: MEDIUM
**Category**: Performance

#### Description

Iterating over result sets without eager loading relationships may cause N+1 query patterns with large datasets.

#### Recommendation

Use `selectinload()` or `joinedload()` for any accessed relationships.

---

### BUG-010: Race Condition in Global Cache Initialization

**Location**: `prep/cache.py:79-102`
**Severity**: MEDIUM
**Category**: Concurrency

#### Description

Global `_CACHE_CLIENT` initialization lacks synchronization, allowing multiple async tasks to simultaneously initialize the cache client.

#### Fix

```python
import asyncio

_cache_client = None
_cache_init_lock = asyncio.Lock()

async def get_cache_client():
    global _cache_client

    if _cache_client is not None:
        return _cache_client

    # ✅ Use lock for thread-safe initialization
    async with _cache_init_lock:
        if _cache_client is None:
            _cache_client = await _MemoryRedis().connect()

    return _cache_client
```

---

### BUG-011: Configuration Whitespace Normalization Inconsistent

**Location**: `prep/settings.py:271, 301, 325`
**Severity**: MEDIUM
**Category**: Security / Configuration

#### Description

Configuration lists like `IP_ALLOWLIST` and `DEVICE_ALLOWLIST` depend on exact string matching, but whitespace normalization is inconsistent across different config values.

#### Impact

Security controls (IP/device allowlists) could be bypassed or incorrectly applied.

---

### BUG-012: Token Validation Error Lacks Diagnostic Logging

**Location**: `prep/auth/rbac.py:116-120`
**Severity**: MEDIUM
**Category**: Observability

#### Description

Token validation failures swallow the original exception, making debugging difficult.

#### Fix

```python
except Exception as exc:
    logger.error(
        "Token validation failed",
        exc_info=exc,  # ✅ Include full traceback
        extra={"token_prefix": token[:20] + "..."},
    )
    raise HTTPException(
        status_code=401,
        detail="Invalid authorization token",
    ) from exc  # ✅ Chain exception
```

---

### BUG-013: Audit Logger Silently Skips When Session Unavailable

**Location**: `middleware/audit_logger.py:35-36`
**Severity**: MEDIUM
**Category**: Logging / Compliance

#### Description

When session factory is unavailable, audit logging is silently skipped without notification.

#### Fix

Log a warning when session unavailable and implement fallback audit mechanism.

---

### BUG-014: Session Cache Validation Not Atomic

**Location**: `prep/auth/dependencies.py:57-71`
**Severity**: MEDIUM
**Category**: Concurrency / Security

#### Description

Session validation checks Redis cache but doesn't use atomic operations, allowing window where revoked sessions could still be used.

#### Fix

Include session version/timestamp in validation or use atomic Redis operations.

---

### BUG-015: Duplicate AdminUser Model Definitions

**Location**: `prep/admin/certification_api.py:289-296, 321-329`
**Severity**: MEDIUM
**Category**: Type Safety

#### Description

Two `AdminUser` model definitions with inconsistent field names (`name` vs `full_name`).

#### Fix

Use single consistent model or rename models for clarity.

---

### BUG-016: Missing Validation for Critical Stripe Configuration

**Location**: `prep/settings.py:84, 116-117`
**Severity**: MEDIUM
**Category**: Configuration

#### Description

Optional Stripe fields lack validation that required combinations are present.

#### Impact

Silent failures when Stripe features used without configuration.

#### Fix

Add conditional validators checking related settings together.

---

### BUG-017: Response Schema Validation Doesn't Fail Requests

**Location**: `prep/api/middleware/schema_validation.py:199-204`
**Severity**: MEDIUM
**Category**: API Contract

#### Description

Response schema validation logs errors but doesn't prevent invalid responses from being served.

#### Fix

At minimum log at WARNING level; consider failing in non-production environments.

---

## Summary by Category

| Category | Count | Criticality |
|----------|-------|-------------|
| **Concurrency** | 5 | Critical/High |
| **Data Integrity** | 4 | Critical |
| **Error Handling** | 4 | High/Medium |
| **Configuration** | 3 | Medium |
| **Performance** | 1 | Medium |

## Next Steps

1. **Immediate (This Sprint)**
   - [ ] Fix BUG-001 (Duplicate functions)
   - [ ] Fix BUG-002 (Idempotency race condition)
   - [ ] Fix BUG-003 (Stripe key thread safety)

2. **Short-term (Next Sprint)**
   - [ ] Fix remaining HIGH severity issues (BUG-004 through BUG-008)
   - [ ] Add comprehensive concurrency tests

3. **Medium-term (Month 2)**
   - [ ] Address all MEDIUM severity issues
   - [ ] Increase test coverage to 85%
   - [ ] Performance optimization

## References

- [README.md - Known Issues](README.md#known-issues--active-bugs)
- [REMAINING_ISSUES_REPORT.md](REMAINING_ISSUES_REPORT.md)
- [COMPREHENSIVE_BUG_HUNT_REPORT_2025-11-11.md](COMPREHENSIVE_BUG_HUNT_REPORT_2025-11-11.md)
