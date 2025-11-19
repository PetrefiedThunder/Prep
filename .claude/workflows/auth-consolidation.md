# Auth Consolidation Workflow

**Goal**: Consolidate authentication logic into reusable, secure, DRY helpers
**Status**: In Progress
**Priority**: P0 (Security-Critical)

---

## Workflow Phases

### Phase 1: PLAN 📋

**Objective**: Map all existing auth patterns and identify consolidation opportunities

**Tasks**:
1. Inventory all authentication functions across the codebase
2. Identify duplicate JWT validation logic
3. Find all places where DB user lookup is missing
4. List all stub/mock authentication functions
5. Design shared auth helpers API

**Success Criteria**:
- Complete list of auth-related files and functions
- Clear understanding of security gaps
- API design for shared helpers approved

**Deliverables**:
- Auth inventory document
- Security gap analysis
- `prep/auth/core.py` API design

---

### Phase 2: IMPLEMENT 💻

**Objective**: Build and test shared authentication helpers

**Tasks**:
1. Create `prep/auth/core.py` with:
   - `decode_and_validate_jwt()` - JWT validation with signature, expiry, audience checks
   - `load_user_from_db()` - DB-backed user loading with active/suspended checks

2. Write comprehensive tests:
   - JWT validation (valid, expired, wrong signature, wrong audience)
   - DB user loading (active, inactive, suspended, deleted, role checks)
   - Integration tests (JWT + DB lookup preventing zombie sessions)

3. Refactor existing auth code:
   - Update `prep/admin/dependencies.py` to use shared helpers
   - Remove stub auth from `prep/admin/certification_api.py`
   - Fix any other auth anti-patterns discovered

**Success Criteria**:
- All tests passing (7+ JWT tests, 11+ DB tests)
- No stub authentication remaining
- All admin endpoints enforce DB-backed auth

**Deliverables**:
- `prep/auth/core.py` (140+ lines)
- `tests/auth/test_core_helpers.py` (400+ lines)
- Refactored `prep/admin/dependencies.py`
- Fixed `prep/admin/certification_api.py`

---

### Phase 3: TEST 🧪

**Objective**: Verify security improvements and prevent regressions

**Test Coverage**:
- ✅ JWT validation (100% coverage)
- ✅ User loading (100% coverage)
- ✅ Zombie session prevention
- ✅ Real-time suspension enforcement
- ✅ Admin authorization checks

**Commands**:
```bash
# Run JWT tests
pytest tests/auth/test_core_helpers.py::test_decode_* -xvs

# Run admin auth tests
pytest tests/admin/test_dependencies.py -xvs

# Run full auth suite
pytest tests/auth/ tests/admin/ -xvs --cov=prep.auth --cov=prep.admin
```

**Success Criteria**:
- All tests passing
- 100% coverage on security-critical paths
- No flaky tests
- Performance regression tests pass

---

### Phase 4: REPORT 📊

**Objective**: Document changes and security improvements

**Deliverables**:
1. **Security Impact Report**:
   - List all security issues fixed (P0, P1, P2)
   - Explain how each fix prevents specific attacks
   - Document any remaining known issues

2. **Pull Request**:
   - Title: "🔒 Auth Hardening - Phase 1: Consolidate & Secure"
   - Description with before/after comparison
   - Test results and coverage report
   - Migration guide (if breaking changes)

3. **Documentation Updates**:
   - Update `docs/deep-dive/AUTHENTICATION_DEEP_DIVE.md`
   - Add examples to `.claude/agents/security-scanning.md`
   - Update `.env.example` with new required variables

**Success Criteria**:
- PR created and reviewed
- Documentation complete
- Security team signoff (if required)

---

## Security Checklist

Before marking as complete:

- [ ] No stub authentication functions remain
- [ ] All admin endpoints enforce `get_current_admin` from `prep.admin.dependencies`
- [ ] JWT validation includes: signature, expiry, audience
- [ ] DB lookup enforces: `is_active=True`, `is_suspended=False`
- [ ] Deleted users cannot authenticate (zombie session prevention)
- [ ] Suspended users cannot authenticate (real-time enforcement)
- [ ] Role-based access control works correctly
- [ ] Error messages don't leak information (user enumeration prevention)
- [ ] All security-critical paths have 100% test coverage

---

## Next Phases

### Phase 2: Extend to All User Endpoints
- Refactor `prep/auth/__init__.py` to use shared helpers
- Update all public API endpoints
- Add refresh token support

### Phase 3: Advanced Security Features
- Multi-factor authentication (MFA)
- Rate limiting on auth endpoints
- Account lockout after failed attempts
- Session management improvements
- Audit logging for security events

---

**Last Updated**: 2025-01-16
**Current Phase**: Implementation (Phase 2)
**Next Milestone**: PR #497 merge
