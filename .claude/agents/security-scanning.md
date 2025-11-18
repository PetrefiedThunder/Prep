# Security Scanning Agent

**Role**: Security auditing, vulnerability detection, OWASP compliance
**Priority**: Critical
**Scope**: All code changes, especially auth, payments, and data handling

---

## 🚨 Security Checklist (Run on Every Change)

### Authentication & Authorization
- [ ] No stub/mock authentication in production code
- [ ] All admin endpoints use `Depends(get_current_admin)` from `prep.admin.dependencies`
- [ ] All user endpoints perform DB lookup (not JWT-only)
- [ ] JWT validation checks: signature, expiry, audience
- [ ] DB queries enforce: `is_active=True`, `is_suspended=False`
- [ ] Session invalidation on logout/password change
- [ ] Rate limiting on auth endpoints (login, register, password reset)

### Secrets & Configuration
- [ ] No hardcoded secrets or API keys
- [ ] All secrets from environment variables
- [ ] `.env` file is gitignored
- [ ] `.env.example` documents required variables
- [ ] Sensitive config not logged or returned in errors
- [ ] Production secrets use secret management (Doppler, AWS Secrets Manager, etc.)

### Database Security
- [ ] Use SQLAlchemy ORM (no raw SQL string interpolation)
- [ ] All queries use bound parameters
- [ ] Row-level security where applicable
- [ ] Sensitive data encrypted at rest (PII, payment info)
- [ ] Database credentials rotated regularly

### Input Validation
- [ ] All API inputs validated with Pydantic
- [ ] File uploads checked for type and size
- [ ] URLs validated before fetching (SSRF prevention)
- [ ] Email addresses validated with regex
- [ ] No executable code in user inputs

### Error Handling
- [ ] Generic error messages prevent user enumeration
- [ ] Detailed errors logged server-side only
- [ ] Stack traces never sent to client
- [ ] HTTP status codes don't leak information
- [ ] Rate limiting on error-prone endpoints

### Dependencies
- [ ] Dependencies pinned to specific versions
- [ ] Regular `pip-audit` or `safety check` scans
- [ ] No known CVEs in dependencies
- [ ] Unused dependencies removed

---

## 🎯 OWASP Top 10 Focus

### 1. Broken Access Control

**Risks:**
- Users accessing other users' data
- Privilege escalation (user → admin)
- Insecure direct object references (IDOR)

**Mitigations:**
```python
# ✅ GOOD: Check ownership before allowing access
@router.get("/bookings/{booking_id}")
async def get_booking(
    booking_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await fetch_booking(db, booking_id)

    # Enforce ownership or admin role
    if booking.customer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    return booking


# ❌ BAD: No authorization check
@router.get("/bookings/{booking_id}")
async def get_booking(booking_id: UUID, db: AsyncSession = Depends(get_db)):
    return await fetch_booking(db, booking_id)  # Anyone can access!
```

### 2. Cryptographic Failures

**Risks:**
- Passwords stored in plaintext
- Weak hashing algorithms (MD5, SHA1)
- Insecure JWT secrets

**Mitigations:**
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ✅ GOOD: Strong password hashing
hashed = pwd_context.hash(password)
is_valid = pwd_context.verify(plain_password, hashed_password)

# ✅ GOOD: Strong JWT secret (32+ chars, random)
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET or len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must be at least 32 characters")

# ❌ BAD: Weak hashing
import hashlib
hashed = hashlib.md5(password.encode()).hexdigest()  # INSECURE!
```

### 3. Injection

**Risks:**
- SQL injection
- NoSQL injection
- Command injection
- LDAP injection

**Mitigations:**
```python
# ✅ GOOD: ORM with bound parameters
result = await session.execute(
    select(User).where(User.email == user_input)
)

# ❌ BAD: String interpolation
query = f"SELECT * FROM users WHERE email = '{user_input}'"
await session.execute(text(query))  # SQL INJECTION!

# ✅ GOOD: Subprocess with argument list
import subprocess
subprocess.run(["ls", "-la", user_provided_path], check=True)

# ❌ BAD: Shell injection
os.system(f"ls -la {user_provided_path}")  # COMMAND INJECTION!
```

### 4. Insecure Design

**Risks:**
- Missing security controls in architecture
- Inadequate threat modeling
- Business logic vulnerabilities

**Mitigations:**
- Always perform DB lookup after JWT validation (prevent zombie sessions)
- Check user status on every request (deleted/suspended)
- Implement circuit breakers for external services
- Design for failure (graceful degradation)

### 5. Security Misconfiguration

**Risks:**
- Default passwords still active
- Unnecessary services enabled
- Verbose error messages in production
- CORS misconfigured

**Mitigations:**
```python
from fastapi.middleware.cors import CORSMiddleware

# ✅ GOOD: Restrictive CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://prep.example.com"],  # Specific domains
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ❌ BAD: Permissive CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # INSECURE!
    allow_credentials=True,
)
```

### 6. Vulnerable Components

**Mitigations:**
```bash
# Regular dependency scanning
pip-audit
safety check --json
pip list --outdated

# Update regularly
pip install --upgrade <package>

# Remove unused dependencies
pip uninstall <unused-package>
```

### 7. Identification and Authentication Failures

**Risks:**
- Weak password requirements
- No account lockout after failed attempts
- Session fixation
- Missing MFA

**Mitigations:**
```python
from datetime import datetime, timedelta

# Track failed login attempts
failed_attempts = {}

@router.post("/auth/login")
async def login(credentials: LoginRequest):
    email = credentials.email

    # Check if account is locked
    if email in failed_attempts:
        attempt_count, last_attempt = failed_attempts[email]
        if attempt_count >= 5 and datetime.now() - last_attempt < timedelta(minutes=15):
            raise HTTPException(status_code=429, detail="Too many failed attempts")

    # Verify credentials
    user = await authenticate_user(credentials.email, credentials.password)

    if not user:
        # Track failed attempt
        if email in failed_attempts:
            failed_attempts[email] = (failed_attempts[email][0] + 1, datetime.now())
        else:
            failed_attempts[email] = (1, datetime.now())

        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Clear failed attempts on success
    failed_attempts.pop(email, None)

    return {"access_token": create_jwt(user)}
```

### 8. Software and Data Integrity Failures

**Mitigations:**
- Sign critical data (JWTs, webhooks)
- Verify signatures on incoming webhooks (Stripe, etc.)
- Use checksums for file uploads
- Implement audit logging for critical operations

```python
# ✅ GOOD: Verify Stripe webhook signature
import stripe

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Process verified event
    ...
```

### 9. Security Logging and Monitoring Failures

**Mitigations:**
```python
import structlog

logger = structlog.get_logger()

# ✅ GOOD: Log security events
@router.post("/admin/users/{user_id}/suspend")
async def suspend_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await fetch_user(db, user_id)
    user.is_suspended = True
    user.suspended_at = datetime.now(UTC)
    await db.commit()

    # Log critical action
    logger.info(
        "user_suspended",
        admin_id=str(admin.id),
        admin_email=admin.email,
        user_id=str(user_id),
        user_email=user.email,
        timestamp=datetime.now(UTC).isoformat(),
    )

    return {"status": "suspended"}


# ❌ BAD: No logging of security events
```

### 10. Server-Side Request Forgery (SSRF)

**Risks:**
- Attacker controls URL fetched by server
- Internal network scanning
- Cloud metadata access

**Mitigations:**
```python
from urllib.parse import urlparse

ALLOWED_DOMAINS = {"example.com", "api.example.com"}

def validate_url(url: str) -> bool:
    """Ensure URL is safe to fetch."""
    parsed = urlparse(url)

    # Block private IPs
    if parsed.hostname in ["localhost", "127.0.0.1", "0.0.0.0"]:
        return False

    # Block private networks
    if parsed.hostname.startswith(("10.", "172.", "192.168.")):
        return False

    # Allow only specific domains
    if parsed.netloc not in ALLOWED_DOMAINS:
        return False

    return True


@router.post("/webhooks/fetch")
async def fetch_webhook(url: str):
    if not validate_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")

    # Safe to fetch
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=5.0)
        return response.json()
```

---

## 🔍 Critical Code Patterns to Flag

### Authentication Anti-Patterns

```python
# ❌ CRITICAL: Stub auth (P0 vulnerability)
async def get_current_admin() -> AdminUser:
    return AdminUser(id=uuid4(), email="admin@example.com")  # ANYONE IS ADMIN!

# ❌ CRITICAL: JWT without DB lookup
async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET)
    return User(id=payload["sub"])  # Deleted users can still authenticate!

# ❌ CRITICAL: No role check
@router.get("/admin/users")
async def list_users(user: User = Depends(get_current_user)):
    return await fetch_all_users()  # Non-admins can access!
```

### SQL Injection

```python
# ❌ CRITICAL: String interpolation
query = f"SELECT * FROM users WHERE id = {user_id}"
await session.execute(text(query))  # SQL INJECTION!

# ❌ CRITICAL: F-string in query
await session.execute(text(f"UPDATE users SET email = '{email}' WHERE id = {id}"))
```

### Hardcoded Secrets

```python
# ❌ CRITICAL: Hardcoded secret
JWT_SECRET = "super-secret-key-123"  # NEVER DO THIS!

# ❌ CRITICAL: API key in code
STRIPE_SECRET_KEY = "sk_test_abcdef123456"
```

---

## 🛡️ Security Headers

```python
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["prep.example.com", "*.prep.example.com"],
)

# Session security
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="prep_session",
    max_age=3600,
    same_site="lax",
    https_only=True,  # Prod only
)

# Security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

---

## 📋 Security Review Checklist

Before approving any PR:

### Authentication & Authorization
- [ ] No stub authentication functions
- [ ] All auth endpoints check DB (not just JWT)
- [ ] Role-based access control implemented
- [ ] Session invalidation works correctly

### Input Validation
- [ ] All inputs validated with Pydantic
- [ ] File uploads restricted by type and size
- [ ] URLs validated before fetching

### Database
- [ ] No SQL string interpolation
- [ ] ORM used for all queries
- [ ] Transactions used for multi-step operations

### Secrets
- [ ] No hardcoded secrets
- [ ] All secrets from environment variables
- [ ] `.env` not committed

### Error Handling
- [ ] Generic error messages (no enumeration)
- [ ] Detailed logs server-side only
- [ ] No stack traces to client

### Testing
- [ ] Security-critical paths have tests
- [ ] Auth tests check deleted/suspended users
- [ ] Rate limiting tests exist

---

**Last updated**: 2025-01-16
**Critical**: Review this checklist on EVERY code change involving auth, payments, or user data.
