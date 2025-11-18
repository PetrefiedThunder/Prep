# GitHub Issues to Create

Based on my investigation of the test cancellation problems in the Prep Connect CI workflow, please create the following 3 GitHub issues:

---

## Issue 1: [CRITICAL] Missing package-lock.json blocks all Prep Connect CI runs

**Labels**: `bug`, `ci/cd`, `priority: critical`, `prep-connect`

**Assignees**: (assign to infrastructure/devops team)

**Body**:
```markdown
## Problem Description

The Prep Connect CI workflow is failing during the "Use Node.js" step because it cannot find the required `package-lock.json` file for dependency caching.

## Root Cause

The workflow configuration at `.github/workflows/prep-connect.yml` specifies:
```yaml
cache: 'npm'
cache-dependency-path: services/prep-connect/package-lock.json
```

However, the `services/prep-connect` directory does not contain a `package-lock.json` file, which causes the GitHub Actions cache setup to fail with:
```
Error: Some specified paths were not resolved, unable to cache dependencies.
```

## Impact

- ❌ All Prep Connect CI workflows are failing at the setup stage
- ❌ Tests are not running
- ❌ Build and deployment steps are being skipped
- ❌ This affects PRs #475, #476, #477, #478, and any future PRs

## Proposed Solution

**Option 1: Generate package-lock.json (Recommended)**
```bash
cd services/prep-connect
npm install
git add package-lock.json
git commit -m "fix: add package-lock.json for CI dependency caching"
```

**Benefits**:
- ✅ Ensures consistent dependency versions across environments
- ✅ Improves build reproducibility
- ✅ Enables faster CI runs with dependency caching
- ✅ Follows npm best practices

**Option 2: Remove cache configuration** (not recommended)
Remove cache-related lines from the workflow

**Option 3: Use alternative package manager**
If using Yarn or pnpm, update the cache configuration accordingly

## Recommendation

Option 1 is strongly recommended. This is a quick fix that will immediately unblock all CI workflows.

## Steps to Fix

1. Checkout main branch
2. Run `cd services/prep-connect && npm install`
3. Commit the generated `package-lock.json`
4. Push to trigger CI
5. Verify workflow runs successfully

## Related Workflow Runs

- [Run #26](https://github.com/PetrefiedThunder/Prep/actions/runs/19384992028) - Failed on missing cache path
- [Run #23](https://github.com/PetrefiedThunder/Prep/actions/runs/19384990395) - Failed on missing cache path
- [Run #22](https://github.com/PetrefiedThunder/Prep/actions/runs/19384985230) - Failed on missing cache path

## Related PRs

- PR #476 (supertest update)
- PR #477 (@types/supertest update)
- PR #472 (@types/jest update)
- PR #475 (express update)
```

---

## Issue 2: Prep Connect CI workflow runs being cancelled with "action_required" status

**Labels**: `bug`, `ci/cd`, `github-actions`, `prep-connect`

**Assignees**: (assign to infrastructure/devops team)

**Body**:
```markdown
## Problem Description

The Prep Connect CI workflow shows "action_required" conclusion with tests being cancelled before they can start running.

## Root Cause Analysis

Multiple dependency PRs created by Dependabot are causing workflow runs to be cancelled:

1. **PR #476**: supertest ^6.4.2 → ^7.1.4 (major version)
2. **PR #477**: @types/supertest 2.0.16 → 6.0.3 (major version)
3. **PR #472**: @types/jest 29.5.14 → 30.0.0 (major version)
4. **PR #475**: express 4.21.2 → 5.1.0 (major version)

## Observed Behavior

- Workflow runs show `conclusion: "action_required"`
- Jobs list shows `total_count: 0` (no jobs executed)
- Runs are being cancelled immediately without executing any steps
- Multiple concurrent PRs triggering workflows simultaneously

## Investigation Findings

Runs #29, #30, #31 for PR #478 all show:
- Status: "completed"
- Conclusion: "action_required"  
- Jobs executed: 0

This is likely caused by:
1. Multiple concurrent PRs triggering the same workflow
2. Missing package-lock.json causing setup-node to fail (see #XXX)
3. No explicit concurrency control in the workflow
4. GitHub Actions default concurrency behavior

## Impact

- ⚠️ Dependency updates cannot be tested automatically
- ⚠️ CI/CD pipeline unreliable
- ⚠️ Difficult to identify real vs cancelled failures
- ⚠️ Wasted GitHub Actions minutes

## Proposed Solutions

### 1. Add Concurrency Control

Update `.github/workflows/prep-connect.yml`:
```yaml
name: Prep Connect CI

on:
  push:
    paths:
      - 'services/prep-connect/**'
      - '.github/workflows/prep-connect.yml'
  pull_request:
    paths:
      - 'services/prep-connect/**'
      - '.github/workflows/prep-connect.yml'

concurrency:
  group: prep-connect-ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # existing jobs...
```

### 2. Configure Dependabot Grouping

Create/update `.github/dependabot.yml`:
```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/services/prep-connect"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 3
    groups:
      test-dependencies:
        patterns:
          - "@types/*"
          - "supertest"
          - "jest"
          - "ts-jest"
      production-dependencies:
        patterns:
          - "express"
          - "helmet"
          - "cors"
```

### 3. Fix Missing Dependencies First

Address the package-lock.json issue (see related issue #XXX) before processing these PRs.

## Recommended Action Order

1. ✅ Fix package-lock.json issue first (blocking)
2. ✅ Add concurrency controls to workflow
3. ✅ Configure Dependabot grouping
4. ✅ Test with one PR before processing others
5. ✅ Close/rebase Dependabot PRs as needed

## Related Issues

- #XXX - Missing package-lock.json (critical blocker)
- #XXX - Dependency compatibility review needed
```

---

## Issue 3: Review and test major dependency updates for Prep Connect compatibility

**Labels**: `dependencies`, `testing`, `prep-connect`, `enhancement`

**Assignees**: (assign to development team)

**Body**:
```markdown
## Problem Description

Multiple Dependabot PRs contain major version updates to critical testing and runtime dependencies that may introduce breaking changes requiring code modifications.

## Affected Dependencies

### Runtime Dependencies
- **express**: 4.21.2 → 5.1.0 (PR #475) 🔴 HIGH RISK
  - Major version with significant API changes

### Test Dependencies
- **supertest**: ^6.4.2 → ^7.1.4 (PR #476) 🟡 MEDIUM RISK
- **@types/supertest**: 2.0.16 → 6.0.3 (PR #477) 🟡 MEDIUM RISK
- **@types/jest**: 29.5.14 → 30.0.0 (PR #472) 🟡 MEDIUM RISK

## Known Breaking Changes

### Express 5.x
- Promise rejection handling changes
- Router parameter handling updates
- Middleware signature changes
- Deprecated methods removed
- [Migration Guide](https://expressjs.com/en/guide/migrating-5.html)

### SuperTest 7.x
- Updated type signatures
- Potential assertion method changes
- Updated superagent dependency

### Type Definitions
- More strict type checking
- Potential compilation errors
- Deprecated type removals

## Impact Assessment

**Current Codebase**:
- `/services/prep-connect/src/server.ts` - Express app setup
- `/services/prep-connect/src/routes/` - All route handlers
- `/services/prep-connect/tests/integrations.test.ts` - SuperTest usage

**Potential Issues**:
- TypeScript compilation errors
- Test failures
- Runtime errors in production
- Middleware incompatibilities

## Recommended Approach

### Phase 1: Prerequisites ✅
- [x] Fix package-lock.json (issue #XXX)
- [x] Fix CI workflow (issue #XXX)
- [ ] Ensure CI pipeline is stable

### Phase 2: Type-Only Updates (Low Risk) 🟡
1. Update @types/jest first
   - Run: `npm install --save-dev @types/jest@30.0.0`
   - Fix TypeScript errors if any
   - Run tests: `npm test`
   
2. Update @types/supertest
   - Run: `npm install --save-dev @types/supertest@6.0.3`
   - Fix TypeScript errors if any
   - Run tests: `npm test`

### Phase 3: Test Library (Medium Risk) 🟡
1. Update supertest
   - Run: `npm install --save-dev supertest@^7.1.4`
   - Review test file: `tests/integrations.test.ts`
   - Update test patterns if needed
   - Verify all tests pass

### Phase 4: Runtime Update (High Risk) 🔴
1. Research Express 5 thoroughly
2. Create feature branch
3. Update Express: `npm install express@^5.1.0`
4. Review ALL route handlers for compatibility
5. Test ALL endpoints manually
6. Run full test suite
7. Monitor for deprecation warnings
8. Consider deferring if too risky

## Testing Checklist

For each dependency update:

- [ ] TypeScript compiles: `npm run build`
- [ ] Linter passes: `npm run lint`
- [ ] All tests pass: `npm test`
- [ ] No console warnings/errors
- [ ] Manual endpoint testing:
  - [ ] GET /integrations (with valid JWT)
  - [ ] POST /integrations (with valid JWT)
  - [ ] DELETE /integrations/:id (with valid JWT)
  - [ ] 401 responses for missing/invalid JWT
- [ ] Performance unchanged

## Code Review Focus Areas

When reviewing PRs for these updates:

1. **Middleware Changes**
   - Error handling patterns
   - Async/await usage
   - Request/response typing

2. **Type Safety**
   - No `any` types introduced
   - Proper type imports
   - Generic constraints

3. **Test Coverage**
   - All existing tests still pass
   - Test assertions still valid
   - No tests skipped/commented out

## Rollback Plan

If issues discovered:
1. Revert to previous version
2. Pin version in package.json
3. Create separate task for fixing compatibility
4. Document known issues

## Success Criteria

- ✅ All tests passing
- ✅ No TypeScript errors
- ✅ No runtime warnings
- ✅ CI pipeline green
- ✅ Manual testing successful
- ✅ Performance maintained

## Timeline

- **Week 1**: Fix CI blockers, update type definitions
- **Week 2**: Update test libraries, verify compatibility  
- **Week 3**: Evaluate Express 5 update decision
- **Week 4**: Complete chosen updates, close PRs

## Resources

- [Express 5 Migration Guide](https://expressjs.com/en/guide/migrating-5.html)
- [Express 5 Changelog](https://github.com/expressjs/express/blob/5.x/History.md)
- [SuperTest Repository](https://github.com/ladjs/supertest)
- [Jest Type Definitions](https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/jest)

## Related Issues

- #XXX - Missing package-lock.json (blocker)
- #XXX - CI workflow cancellations

## Related PRs

- PR #472 - @types/jest update
- PR #475 - Express update
- PR #476 - SuperTest update  
- PR #477 - @types/supertest update
```

---

## Instructions

1. Create the above 3 issues in GitHub
2. Update the issue references (replace `#XXX` with actual issue numbers)
3. Link the issues together in the descriptions
4. Add appropriate labels and assignees
5. Set issue #1 as highest priority (critical blocker)

## Quick Reference

| Issue | Title | Priority | Blocking |
|-------|-------|----------|----------|
| 1 | Missing package-lock.json | Critical | Yes |
| 2 | CI workflow cancellations | High | Partially |
| 3 | Dependency compatibility | Medium | No |

Handle Issue #1 first - it blocks everything else!
