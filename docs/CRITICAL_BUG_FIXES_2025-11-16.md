# Critical Bug Fixes - 2025-11-16

## Summary

Fixed 4 critical security and correctness bugs identified in README.md:
- ✅ BUG-003: Thread-unsafe Stripe API key
- ✅ BUG-005: Unsafe falsy checks on Stripe fields
- ✅ BUG-001: Duplicate `get_current_admin()` function
- ✅ BUG-002: Race condition in idempotency middleware

---

## BUG-003: Thread-unsafe Stripe API key

**File**: `prep/payments/service.py`
**Lines**: 70 (original)
**Severity**: 🔴 CRITICAL
**Category**: Concurrency / Security

### Problem
```python
stripe.api_key = secret_key  # ❌ Sets global mutable state
account = await asyncio.to_thread(stripe.Account.create, type="custom")
```

**Impact**: In high-concurrency scenarios or multi-tenant deployments, concurrent requests could use the wrong API key, leading to:
- Cross-tenant data exposure
- Payment failures
- Incorrect account access

### Fix
```python
# Pass API key per-request to avoid thread-unsafe global state
account = await asyncio.to_thread(
    stripe.Account.create,
    type="custom",
    api_key=secret_key,  # ✅ Request-scoped API key
)

account_link = await asyncio.to_thread(
    stripe.AccountLink.create,
    account=account_id,
    refresh_url=str(self._settings.stripe_connect_refresh_url),
    return_url=str(self._settings.stripe_connect_return_url),
    type="account_onboarding",
    api_key=secret_key,  # ✅ Request-scoped API key
)
```

**Rationale**: Stripe's Python SDK supports per-request API keys via the `api_key` parameter, which is the recommended pattern for multi-tenant or concurrent applications. This eliminates global mutable state.

---

## BUG-005: Unsafe falsy checks on Stripe fields

**File**: `prep/payments/service.py`
**Lines**: 77, 114 (original)
**Severity**: 🟡 MEDIUM
**Category**: Correctness

### Problem
```python
account_id = getattr(account, "id", None)
if not account_id:  # ❌ Falsy check catches empty strings, 0, etc.
    raise PaymentsError("Stripe did not return an account id")

if not onboarding_url:  # ❌ Falsy check
    raise PaymentsError("Stripe did not return an onboarding link")
```

**Impact**: Stripe could theoretically return valid IDs or URLs that are falsy in Python (e.g., empty string, though unlikely). Using falsy checks instead of explicit `None` checks could cause false positives.

### Fix
```python
account_id = getattr(account, "id", None)
if account_id is None:  # ✅ Explicit None check
    raise PaymentsError("Stripe did not return an account id")

if onboarding_url is None:  # ✅ Explicit None check
    raise PaymentsError("Stripe did not return an onboarding link")
```

**Rationale**: Explicit `is None` checks are more precise and follow Python best practices for optional value validation.

---

## BUG-001: Duplicate `get_current_admin()` function

**File**: `prep/admin/certification_api.py`
**Lines**: 289, 321 (original)
**Severity**: 🔴 CRITICAL
**Category**: Correctness / Type Safety

### Problem
Two definitions of `get_current_admin()` existed in the same file:

```python
# First definition (line 289) - WRONG FIELD NAME
async def get_current_admin() -> AdminUser:
    return AdminUser(
        id=UUID("55555555-5555-5555-5555-555555555555"),
        email="admin@example.com",
        name="Prep Admin",  # ❌ Field is 'full_name', not 'name'
    )

# Second definition (line 321) - CORRECT
async def get_current_admin() -> AdminUser:
    return AdminUser(
        id=uuid4(),
        email="admin@example.com",
        full_name="Prep Admin",  # ✅ Correct field name
        permissions=["certifications:verify"],  # ✅ Includes permissions
    )
```

**Impact**: Python allows duplicate function definitions, and the second definition silently overrides the first. This causes:
- Confusing behavior (first definition is unreachable)
- Different UUIDs used (fixed vs random)
- Inconsistent field names vs the `AdminUser` model in `prep/models/admin.py`

**AdminUser Model** (`prep/models/admin.py`):
```python
class AdminUser(BaseModel):
    id: UUID
    email: str
    full_name: str  # ✅ Not 'name'
    permissions: list[str] = Field(default_factory=list)
```

### Fix
Removed the first duplicate definition and kept only the correct one:

```python
# Duplicate get_current_admin() function removed (BUG-001 fix)
# The correct definition is below at line ~321 with proper field names
```

**Rationale**: Keeping only one definition eliminates confusion, ensures type safety, and prevents runtime errors from mismatched field names.

---

## BUG-002: Race condition in idempotency middleware

**File**: `prep/api/middleware/idempotency.py`
**Lines**: 55-71 (original)
**Severity**: 🔴 CRITICAL
**Category**: Concurrency / Data Integrity

### Problem
Classic check-then-set race condition:

```python
# Step 1: Check if key exists (LINE 55)
cached_signature = await redis.get(cache_key)

# Step 2: If not exists, proceed (LINE 56-69)
if cached_signature is not None:
    # Handle conflicts/replay
    return error_response

# Step 3: Set the key (LINE 71)
await redis.setex(cache_key, self._ttl_seconds, signature)

# Step 4: Process request (LINE 73)
response = await call_next(request)
```

**Race Condition Timeline**:
```
Request A: Check Redis (key doesn't exist)
Request B: Check Redis (key doesn't exist)
Request A: Set key in Redis
Request B: Set key in Redis (overwrites A!)
Request A: Process request
Request B: Process request (DUPLICATE!)
```

**Impact**: Two concurrent requests with the same idempotency key could both:
1. Pass the existence check
2. Both set the cache
3. Both proceed to process the request
4. Result in duplicate charges, bookings, or other side effects

### Fix
Use Redis's atomic `SET ... NX` (set if not exists) operation:

```python
# BUG-002 fix: Use atomic SET NX to prevent race conditions
# Try to set the cache key atomically, only if it doesn't exist
was_set = await redis.set(cache_key, signature, ex=self._ttl_seconds, nx=True)

if not was_set:
    # Key already exists, check if it's the same signature
    cached_signature = await redis.get(cache_key)
    if cached_signature is not None and cached_signature != signature:
        return json_error_response(
            request,
            status_code=status.HTTP_409_CONFLICT,
            code="api.idempotency.payload_conflict",
            message="Idempotency key reuse detected with a different payload",
        )
    return json_error_response(
        request,
        status_code=status.HTTP_409_CONFLICT,
        code="api.idempotency.replayed",
        message="Request with this Idempotency-Key has already been processed",
    )
```

**Redis `SET ... NX` Operation**:
- `nx=True`: Only set the key if it doesn't already exist (atomic)
- `ex=self._ttl_seconds`: Set expiration time
- Returns `True` if set succeeded, `False` if key already existed

**Rationale**: The `SET ... NX` operation is atomic at the Redis level, preventing race conditions. Only one of the concurrent requests will successfully set the key; all others will receive `False` and can handle the replay appropriately.

---

## Testing Recommendations

### Unit Tests
1. **Stripe thread-safety**:
   - Mock `stripe.Account.create` to verify `api_key` parameter is passed
   - Verify no global `stripe.api_key` assignment occurs
   - Test concurrent requests with different API keys

2. **Idempotency middleware**:
   - Test concurrent requests with the same idempotency key
   - Verify only one request proceeds
   - Test payload conflict detection
   - Test TTL expiration

3. **AdminUser consistency**:
   - Verify `get_current_admin()` returns correct fields
   - Test that endpoints using the dependency work correctly

### Integration Tests
1. **End-to-end payment flow**:
   - Create Connect account
   - Verify no cross-tenant contamination
   - Test concurrent onboarding requests

2. **Idempotency flow**:
   - Submit identical requests rapidly
   - Verify duplicate detection
   - Test with different payloads (conflict)

### Load Tests
1. **Concurrency stress tests**:
   - 100+ concurrent payment requests
   - 1000+ concurrent idempotent POST requests
   - Monitor for race condition symptoms

---

## Deployment Checklist

- [ ] Deploy changes to staging environment
- [ ] Run full test suite (unit + integration + E2E)
- [ ] Verify Redis connectivity in staging
- [ ] Test Stripe integration with test API keys
- [ ] Monitor logs for any new errors
- [ ] Run load tests to verify concurrency fixes
- [ ] Deploy to production during low-traffic window
- [ ] Monitor error rates and latency metrics
- [ ] Verify no Stripe webhook processing errors

---

## Related Issues

- **README.md**: Updated bug status to "Fixed"
- **CRITICAL_BUGS_HUNTING_LIST.md**: Mark BUG-001, BUG-002, BUG-003, BUG-005 as resolved
- **IMPLEMENTATION_STATUS_2025-11-16.md**: Update bug fix status

---

## Files Modified

1. `prep/payments/service.py`
   - Fixed thread-unsafe Stripe API key (BUG-003)
   - Fixed unsafe falsy checks (BUG-005)

2. `prep/admin/certification_api.py`
   - Removed duplicate `get_current_admin()` function (BUG-001)

3. `prep/api/middleware/idempotency.py`
   - Fixed race condition with atomic Redis SET NX (BUG-002)

---

## Author

**Fixed By**: Claude (Anthropic AI)
**Date**: 2025-11-16
**Branch**: `claude/implement-mvp-flow-01LQLdv5QrRLu3XWgcLGuM1e`
**Review Status**: Pending human review

---

## Next Steps

1. ✅ Commit changes with descriptive message
2. ✅ Run existing test suite
3. ✅ Add new tests for fixed bugs
4. ✅ Update README.md to mark bugs as fixed
5. ✅ Proceed to Phase 2: Wire real database connectivity
