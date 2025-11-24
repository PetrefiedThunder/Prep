# GitHub Issues to Create - Repository Inconsistencies

**Generated**: 2025-11-24  
**Source**: PR Inconsistencies and Issues Analysis  
**Total Issues**: 12 actionable issues

This document contains ready-to-create GitHub Issues based on the repository inconsistency analysis. Copy each issue directly into GitHub.

---

## 🔴 High Priority Issues (Create First)

### Issue 1: Consolidate Bug Documentation

**Title**: Consolidate 14 bug report files into single tracking system

**Labels**: `documentation`, `technical-debt`, `cleanup`, `P0`

**Milestone**: Sprint 1

**Assignees**: (assign to technical lead)

**Description**:
```markdown
## Problem

Currently, 14 separate markdown files document bugs with significant overlap (~236 KB total). This creates confusion and makes it impossible to track which bugs are fixed.

### Current State
- BUG_AND_INTEGRATION_REPORT_2025-11-19.md (15,869 bytes)
- BUG_AUDIT_AND_FIX_SUMMARY_2025-11-17.md (11,720 bytes)
- BUG_AUDIT_QUICK_REFERENCE.md (6,564 bytes)
- BUG_FIXES_SUMMARY.md (16,062 bytes)
- BUG_HUNT_REPORT_2025-11-11.md (24,089 bytes)
- BUG_SCAN_EXECUTIVE_SUMMARY.md (6,613 bytes)
- BUG_SCAN_INDEX.md (12,372 bytes)
- COMPREHENSIVE_BUG_AUDIT_REPORT_2025-11-17.md (13,912 bytes)
- COMPREHENSIVE_BUG_HUNT_REPORT_2025-11-11.md (45,649 bytes) ⚠️
- COMPREHENSIVE_BUG_SCAN_REPORT.md (22,896 bytes)
- CRITICAL_BUGS_HUNTING_LIST.md (25,823 bytes)
- REMAINING_ISSUES_REPORT.md (11,069 bytes)
- RUNTIME_BUG_REPORT_2025-11-19.md (12,965 bytes)
- CODE_QUALITY_ISSUES_DETAILS.md (16,533 bytes)

### Issues
- No single source of truth
- Same bugs documented multiple times
- Difficult to track which bugs are fixed vs open
- Root directory cluttered
- Developers don't know which document is current

## Solution

Consolidate into proper tracking system:
1. Archive old reports (historical record)
2. Create GitHub Issues for all open bugs
3. Single ACTIVE_BUGS.md that links to GitHub Issues
4. Prevent future proliferation

## Tasks

- [ ] Create docs/bugs/archive/ directory
- [ ] Archive old bug reports (2025-11-11, 2025-11-17) to docs/bugs/archive/
- [ ] Review all 14 files and extract unique open bugs
- [ ] Create GitHub Issues for all currently open bugs
- [ ] Create docs/ACTIVE_BUGS.md that links to GitHub Issues
- [ ] Update .gitignore to prevent future proliferation:
  ```
  BUG_REPORT_*.md
  COMPREHENSIVE_BUG_*.md
  ```
- [ ] Document process in CONTRIBUTING.md: Use GitHub Issues, not markdown files
- [ ] Add README.md link to docs/ACTIVE_BUGS.md

## Acceptance Criteria

- ✅ All historical bug reports moved to docs/bugs/archive/
- ✅ All open bugs tracked in GitHub Issues
- ✅ Single ACTIVE_BUGS.md at docs/ level
- ✅ Root directory has no BUG_*.md files
- ✅ .gitignore prevents future BUG_*.md files
- ✅ Process documented

## Impact

- Reduces confusion
- Enables proper bug tracking
- Cleaner root directory
- Single source of truth for bug status

## Estimated Effort

2-3 hours
```

---

### Issue 2: Remove Duplicate harborhomes Service Folder

**Title**: Remove duplicate harborhomes/ folder, keep apps/harborhomes/

**Labels**: `bug`, `technical-debt`, `duplicate-code`, `P0`

**Milestone**: Sprint 1

**Assignees**: (assign to infrastructure team)

**Description**:
```markdown
## Problem

Complete duplicate of harborhomes Next.js app exists in two locations:
- `./apps/harborhomes/` (canonical, 18 files)
- `./harborhomes/` (duplicate, identical 18 files)

### Duplicated Files
- package.json (2 copies)
- tailwind.config.ts (2 copies)
- tsconfig.json (2 copies)
- tsconfig.base.json (2 copies)
- vitest.config.ts (2 copies)
- vitest.setup.ts (2 copies)
- All lib/ files (types.ts, utils.ts, etc.)
- All app/ files
- All components/ files

### Issues
- Changes made to one location won't reflect in the other
- Double the maintenance burden
- Confusing for developers which one is "source of truth"
- Wastes disk space and CI time
- Risk of divergence over time

## Solution

Remove the duplicate `harborhomes/` folder and use only `apps/harborhomes/`.

## Tasks

- [ ] Verify apps/harborhomes/ is the source of truth (check git history)
- [ ] Search entire codebase for references to harborhomes/ path:
  ```bash
  grep -r "harborhomes/" --include="*.yml" --include="*.yaml" --include="*.json" --include="*.ts" --include="*.js"
  ```
- [ ] Update all references to use apps/harborhomes/
- [ ] Check docker-compose.yml for harborhomes/ references
- [ ] Check .github/workflows/ for harborhomes/ references
- [ ] Test builds locally:
  ```bash
  cd apps/harborhomes && npm install && npm run build
  ```
- [ ] Delete harborhomes/ folder:
  ```bash
  git rm -r harborhomes/
  ```
- [ ] Verify CI/CD pipelines work
- [ ] Update README.md if harborhomes/ is mentioned

## Acceptance Criteria

- ✅ Only apps/harborhomes/ exists in repository
- ✅ All references updated to apps/harborhomes/
- ✅ Builds and tests pass
- ✅ CI/CD pipelines work
- ✅ No broken imports or paths

## Impact

- Eliminates maintenance burden
- Prevents divergence
- Clearer repository structure
- Reduces disk usage

## Estimated Effort

30-45 minutes
```

---

### Issue 3: Consolidate Duplicate swarm_coordinator.py

**Title**: Consolidate duplicate swarm_coordinator.py files

**Labels**: `bug`, `duplicate-code`, `agents`, `P0`

**Milestone**: Sprint 1

**Assignees**: (assign to AI/agents team)

**Description**:
```markdown
## Problem

Two identical swarm_coordinator.py files exist in different locations:
- `./prep/ai/swarm_coordinator.py`
- `./agents/coordinators/swarm_coordinator.py`

### Issues
- One is likely outdated
- Changes to agent swarm logic may only update one file
- Import confusion (which one to use?)
- Code divergence risk

## Solution

Consolidate to single location with backward-compatible import.

## Tasks

- [ ] Compare both files to check for differences:
  ```bash
  diff prep/ai/swarm_coordinator.py agents/coordinators/swarm_coordinator.py
  ```
- [ ] Determine canonical location (likely agents/coordinators/)
- [ ] Search for imports of the old location:
  ```bash
  grep -r "from prep.ai.swarm_coordinator" --include="*.py"
  grep -r "from prep.ai import swarm_coordinator" --include="*.py"
  ```
- [ ] Update all imports to use agents.coordinators.swarm_coordinator
- [ ] Add backward-compatible import in prep/ai/__init__.py:
  ```python
  # Backward compatibility
  from agents.coordinators.swarm_coordinator import SwarmCoordinator
  ```
- [ ] Delete prep/ai/swarm_coordinator.py
- [ ] Run tests to verify nothing breaks
- [ ] Update documentation if needed

## Acceptance Criteria

- ✅ Only one swarm_coordinator.py exists
- ✅ All imports use new location
- ✅ Backward compatibility maintained
- ✅ Tests pass
- ✅ No import errors

## Impact

- Eliminates confusion
- Ensures single source of truth
- Prevents code divergence

## Estimated Effort

30 minutes
```

---

### Issue 4: Archive README.old.md

**Title**: Archive or delete README.old.md

**Labels**: `documentation`, `cleanup`, `P0`

**Milestone**: Sprint 1

**Assignees**: (assign to documentation lead)

**Description**:
```markdown
## Problem

README.old.md (32 KB) contains outdated "Enterprise Compliance Orchestration Platform" branding that conflicts with current README.md "Commercial Kitchen Compliance & Booking Platform" branding.

### Current State
- **README.md** (24 KB): Current branding, MVP focus, Dec 7 deadline
- **README.old.md** (32 KB): Old branding, different architecture details

### Issues
- Confusing for new developers (which is correct?)
- Different target audiences mentioned
- Conflicting technical details
- Outdated information
- Two sources of truth

## Solution

Archive README.old.md to docs/archive/ or delete if no longer needed.

## Tasks

- [ ] Review README.old.md for any unique content not in README.md
- [ ] Extract any valuable content and add to current docs:
  - Technical stack details
  - Architecture diagrams
  - Setup instructions
- [ ] Create docs/archive/ directory if it doesn't exist
- [ ] Move to docs/archive/README_2025-11-archive.md:
  ```bash
  mkdir -p docs/archive
  git mv README.old.md docs/archive/README_2025-11-archive.md
  ```
- [ ] OR delete if no valuable content:
  ```bash
  git rm README.old.md
  ```
- [ ] Update any links to README.old.md (search for references)
- [ ] Ensure README.md is the single source of truth

## Acceptance Criteria

- ✅ Only README.md exists at root level
- ✅ No conflicting information
- ✅ Any valuable content from README.old.md preserved in docs/
- ✅ No broken links
- ✅ Clear for new developers

## Impact

- Eliminates confusion for new developers
- Single source of truth for project README
- Cleaner root directory

## Estimated Effort

15-20 minutes
```

---

### Issue 5: Create GitHub Issues from PREP_CONNECT_ISSUES_TO_CREATE.md

**Title**: Create 3 GitHub Issues from PREP_CONNECT_ISSUES_TO_CREATE.md

**Labels**: `prep-connect`, `ci/cd`, `dependencies`, `meta`, `P0`

**Milestone**: Sprint 1

**Assignees**: (assign to DevOps/CI lead)

**Description**:
```markdown
## Problem

PREP_CONNECT_ISSUES_TO_CREATE.md contains 3 well-documented issues that block CI, but they're not in GitHub Issues for proper tracking.

### Issues to Create

1. **[CRITICAL] Missing package-lock.json blocks all Prep Connect CI runs**
   - Priority: Critical (Blocking)
   - Labels: `bug`, `ci/cd`, `priority: critical`, `prep-connect`

2. **Prep Connect CI workflow runs being cancelled with "action_required" status**
   - Priority: High (Partially Blocking)
   - Labels: `bug`, `ci/cd`, `github-actions`, `prep-connect`

3. **Review and test major dependency updates for Prep Connect compatibility**
   - Priority: Medium
   - Labels: `dependencies`, `testing`, `prep-connect`, `enhancement`

## Solution

Create the 3 issues in GitHub with all the detailed information from PREP_CONNECT_ISSUES_TO_CREATE.md.

## Tasks

- [ ] Create Issue #1: Missing package-lock.json (copy full content from doc)
  - Label as `Critical`, `Blocking`
  - Assign to DevOps team
  - Link to related PRs: #475, #476, #477, #478

- [ ] Create Issue #2: CI workflow cancellations (copy full content from doc)
  - Label as `High`, `Partially Blocking`
  - Add dependency on Issue #1
  - Link to workflow runs

- [ ] Create Issue #3: Dependency compatibility (copy full content from doc)
  - Label as `Medium`
  - Add dependencies on Issues #1 and #2
  - Link to related PRs

- [ ] Link issues together in descriptions:
  - Issue #2 depends on Issue #1
  - Issue #3 depends on Issues #1 and #2

- [ ] Update PREP_CONNECT_ISSUES_TO_CREATE.md with GitHub Issue links
- [ ] Move PREP_CONNECT_ISSUES_TO_CREATE.md to docs/archive/ after creation

## Acceptance Criteria

- ✅ All 3 issues created in GitHub
- ✅ Issues properly linked and labeled
- ✅ Dependencies mapped
- ✅ PREP_CONNECT_ISSUES_TO_CREATE.md archived
- ✅ Team notified of critical blocking issue

## Impact

- Unblocks CI pipeline
- Enables proper tracking and prioritization
- Team visibility into blocking issues

## Estimated Effort

30 minutes
```

---

### Issue 6: Create GitHub Issues from GITHUB_ISSUES_MASTER.md

**Title**: Create 24 GitHub Issues from GITHUB_ISSUES_MASTER.md

**Labels**: `epic`, `sprint-planning`, `documentation`, `meta`, `P1`

**Milestone**: Sprint 1

**Assignees**: (assign to project manager)

**Description**:
```markdown
## Problem

docs/GITHUB_ISSUES_MASTER.md contains 24 well-structured issues across 4 sprints and 9 epics, but they're not in GitHub Issues for proper tracking and execution.

### Current State
- 24 issues defined in markdown
- 4 sprints planned
- 9 epics defined
- Complete with acceptance criteria
- No tracking in GitHub Issues

### Epics
- Epic A: Golden Path Demo (4 issues)
- Epic B: System Map & Service Classification (2 issues)
- Epic C: Jurisdiction Clarity (3 issues)
- Epic D: MVP Definition (2 issues)
- Epic E: Data Model & ERD Clarity (3 issues)
- Epic G: Payments Architecture (2 issues)
- Epic H: Compliance Engine Architecture (3 issues)
- Epic I: Observability & SLOs (2 issues)
- Epic J: Cleanup & Repository Hygiene (2 issues)

## Solution

Create all issues in GitHub with proper milestones, labels, and dependencies.

## Tasks

### Step 1: Setup
- [ ] Create milestones in GitHub:
  - Sprint 1: Golden Path + System Clarity
  - Sprint 2: Jurisdiction Clarity + MVP
  - Sprint 3: Data Model, Payments, Compliance Engine
  - Sprint 4: Observability + Cleanup

- [ ] Create labels in GitHub:
  - `epic-a-golden-path`
  - `epic-b-system-map`
  - `epic-c-jurisdiction`
  - `epic-d-mvp`
  - `epic-e-data-model`
  - `epic-g-payments`
  - `epic-h-compliance`
  - `epic-i-observability`
  - `epic-j-cleanup`
  - `sprint-1`, `sprint-2`, `sprint-3`, `sprint-4`
  - `documentation`, `infrastructure`, `testing`

### Step 2: Create Issues (Sprint 1 - 6 issues)
- [ ] A1: Create Golden Path Documentation
- [ ] A2: Create Golden Path Fixtures
- [ ] A3: Service Boot Consistency
- [ ] A4: Observability for Golden Path
- [ ] B1: Create SYSTEM_MAP.md
- [ ] B2: Add Service Status Labels

### Step 3: Create Issues (Sprint 2 - 5 issues)
- [ ] C1: Create JURISDICTION_STATUS.md
- [ ] C2: Add Jurisdiction Regression Tests
- [ ] C3: Define MVP Jurisdiction Scope
- [ ] D1: Create MVP_SCOPE.md
- [ ] D2: Repository Hygiene for MVP

### Step 4: Create Issues (Sprint 3 - 9 issues)
- [ ] E1: Generate Entity Relationship Diagrams
- [ ] E2: Create DATA_MODEL.md
- [ ] E3: Add Migration Consistency Tests
- [ ] G1: Create PAYMENTS_ARCHITECTURE.md
- [ ] G2: Add Pricing and Fees Tests
- [ ] H1: Document Compliance Engine
- [ ] H2: Refactor to Data-Driven Rules
- [ ] H3: Add Compliance Regression Tests

### Step 5: Create Issues (Sprint 4 - 4 issues)
- [ ] I1: Define Service Level Objectives
- [ ] I2: Implement Observability Dashboards
- [ ] J1: Repository Cleanup
- [ ] J2: Standardize Service Documentation

### Step 6: Link and Update
- [ ] Link dependencies between issues
- [ ] Update GITHUB_ISSUES_MASTER.md with GitHub Issue links
- [ ] Create project board for sprint tracking

## Automation Option

Consider using the GitHub API or CLI to batch create:
```bash
# See scripts/create_github_issues.py for automation
gh issue create --title "..." --body "..." --label "..." --milestone "..."
```

## Acceptance Criteria

- ✅ All 4 milestones created
- ✅ All labels created
- ✅ All 24 issues created with proper metadata
- ✅ Dependencies linked
- ✅ GITHUB_ISSUES_MASTER.md updated with links
- ✅ Project board created

## Impact

- Enables proper project management
- Team can track progress
- Clear sprint goals
- Proper epic organization

## Estimated Effort

2-3 hours (or 30 min with automation script)
```

---

## 🟡 Medium Priority Issues

### Issue 7: Consolidate Security Documentation

**Title**: Move security audits to docs/security/audits/

**Labels**: `documentation`, `security`, `cleanup`, `P2`

**Milestone**: Sprint 2

**Description**:
```markdown
## Problem

5 security-related files at root level should be organized:
- SECURITY.md (should stay at root - GitHub standard)
- SECURITY_AUDIT_REPORT_2025-11-11.md (should move)
- SECURITY_FIXES_2025-11-19.md (should move)
- SECURITY_VULNERABILITY_REPORT.md (should move)
- docs/MICROSERVICES_SECURITY_SCANNING.md (already in docs/)

## Tasks

- [ ] Create docs/security/audits/ directory
- [ ] Move SECURITY_AUDIT_REPORT_*.md to docs/security/audits/
- [ ] Move SECURITY_FIXES_*.md to docs/security/audits/
- [ ] Move SECURITY_VULNERABILITY_REPORT.md to docs/security/audits/
- [ ] Keep SECURITY.md at root (GitHub standard)
- [ ] Update links in other docs
- [ ] Update README.md security section

## Acceptance Criteria

- ✅ Only SECURITY.md at root
- ✅ All audits in docs/security/audits/
- ✅ No broken links
- ✅ README.md updated

## Estimated Effort

20 minutes
```

---

### Issue 8: Rename Generic test_core.py Files

**Title**: Rename 5 test_core.py files to be module-specific

**Labels**: `testing`, `code-quality`, `refactor`, `P2`

**Milestone**: Sprint 2

**Description**:
```markdown
## Problem

5 test files all named test_core.py make it impossible to identify which test failed:
- tests/lse_impact_simulator/test_core.py
- tests/gdpr_ccpa_core/test_core.py
- tests/dol_reg_compliance_engine/test_core.py
- tests/gaap_ledger_porter/test_core.py
- tests/auto_projection_bot/test_core.py

## Tasks

- [ ] Rename tests/lse_impact_simulator/test_core.py → test_lse_simulator.py
- [ ] Rename tests/gdpr_ccpa_core/test_core.py → test_gdpr_ccpa.py
- [ ] Rename tests/dol_reg_compliance_engine/test_core.py → test_dol_compliance.py
- [ ] Rename tests/gaap_ledger_porter/test_core.py → test_gaap_ledger.py
- [ ] Rename tests/auto_projection_bot/test_core.py → test_auto_projection.py
- [ ] Update CI configuration if test paths are hardcoded
- [ ] Run tests to verify everything still works

## Acceptance Criteria

- ✅ No files named test_core.py
- ✅ All test files have descriptive names
- ✅ Tests still pass
- ✅ CI works correctly

## Estimated Effort

30 minutes
```

---

### Issue 9: Convert TODOs to GitHub Issues

**Title**: Convert 11 TODO comments to tracked GitHub Issues

**Labels**: `technical-debt`, `code-quality`, `P2`

**Milestone**: Sprint 2

**Description**:
```markdown
## Problem

11 TODO/FIXME comments in code should be tracked as GitHub Issues for visibility and prioritization:

1. dags/foodcode_ingest.py:13 - TODO: Implement actual fetch logic
2. dags/foodcode_ingest.py:27 - TODO: Implement actual parsing logic
3. dags/foodcode_ingest.py:41 - TODO: Implement actual load logic
4. integrations/docusign_client.py:90 - TODO: Update _create_client for async
5. tests/admin/test_certification_api_auth.py:16 - TODO: Implement these tests once ORM issues are resolved
6. (Plus 6 more TODOs discovered in analysis)

## Tasks

- [ ] Search for all TODO/FIXME/XXX/HACK comments:
  ```bash
  grep -r "TODO\|FIXME\|XXX\|HACK" --include="*.py" --include="*.ts" --include="*.js"
  ```
- [ ] Create GitHub Issue for each TODO with:
  - Code context
  - File and line number
  - Description of what needs to be done
  - Priority estimate
- [ ] Replace TODO comments with issue links:
  ```python
  # TODO: Fix async - see Issue #123
  ```
- [ ] Add TODO linter rule to CI to prevent new TODOs without issue links
- [ ] Document policy in CONTRIBUTING.md

## Acceptance Criteria

- ✅ All TODOs tracked in GitHub Issues
- ✅ TODO comments replaced with issue links
- ✅ CI linter rule added
- ✅ Policy documented

## Estimated Effort

1-2 hours
```

---

### Issue 10: Refactor Duplicate Jurisdiction Validators

**Title**: Create base validator class to eliminate jurisdiction duplication

**Labels**: `refactor`, `code-quality`, `technical-debt`, `P2`

**Milestone**: Sprint 3

**Description**:
```markdown
## Problem

5 jurisdiction validate.py files contain duplicate code (~100 lines each = 500 total lines):
- apps/city_regulatory_service/jurisdictions/san_jose/validate.py
- apps/city_regulatory_service/jurisdictions/san_francisco/validate.py
- apps/city_regulatory_service/jurisdictions/berkeley/validate.py
- apps/city_regulatory_service/jurisdictions/palo_alto/validate.py
- apps/city_regulatory_service/jurisdictions/joshua_tree/validate.py

## Solution

Create base validator class with common logic. Reduce to ~100 base + 5×20 custom = 200 total lines (60% reduction).

## Tasks

- [ ] Analyze all 5 validate.py files to identify common patterns
- [ ] Create apps/city_regulatory_service/jurisdictions/base_validator.py
- [ ] Extract common validation logic to base class
- [ ] Refactor san_francisco/validate.py to inherit from base
- [ ] Refactor san_jose/validate.py to inherit from base
- [ ] Refactor berkeley/validate.py to inherit from base
- [ ] Refactor palo_alto/validate.py to inherit from base
- [ ] Refactor joshua_tree/validate.py to inherit from base
- [ ] Add comprehensive tests for base validator
- [ ] Update tests for each jurisdiction
- [ ] Document validator architecture

## Acceptance Criteria

- ✅ base_validator.py created with common logic
- ✅ All 5 jurisdictions inherit from base
- ✅ Each jurisdiction only contains city-specific logic
- ✅ Code reduced by ~300 lines
- ✅ All tests pass
- ✅ No functionality broken

## Impact

- Reduces code duplication by 60%
- Easier maintenance
- Consistent validation logic
- Easier to add new jurisdictions

## Estimated Effort

3-4 hours
```

---

## 🟢 Low Priority Issues

### Issue 11: Standardize TypeScript Configuration

**Title**: Create shared tsconfig.json, reduce 20 copies

**Labels**: `typescript`, `code-quality`, `refactor`, `P3`

**Milestone**: Sprint 4

**Description**:
```markdown
## Problem

20 tsconfig.json files exist with minor variations. Should use shared base configuration.

## Tasks

- [ ] Create tsconfig.base.json at root with common config
- [ ] Extract common settings from all 20 configs
- [ ] Update each tsconfig.json to extend base:
  ```json
  {
    "extends": "../../tsconfig.base.json",
    "compilerOptions": {
      // Only service-specific overrides
    }
  }
  ```
- [ ] Verify all builds still work
- [ ] Document TypeScript configuration strategy

## Acceptance Criteria

- ✅ Single source of truth for common TS config
- ✅ All 20 configs extend base
- ✅ Builds work correctly
- ✅ Documentation updated

## Estimated Effort

2-3 hours
```

---

### Issue 12: Clean Up Multiple service.py Files

**Title**: Rename generic service.py files to be module-specific

**Labels**: `code-quality`, `naming`, `P3`

**Milestone**: Sprint 4

**Description**:
```markdown
## Problem

Multiple service.py files with same name make debugging difficult.

## Tasks

- [ ] Find all service.py files
- [ ] Rename to module-specific names
- [ ] Update imports
- [ ] Update tests

## Estimated Effort

1-2 hours
```

---

## Summary

**Total Issues to Create**: 12

### By Priority
- **P0 (Critical)**: 6 issues → Create immediately
- **P1 (High)**: 0 issues
- **P2 (Medium)**: 4 issues → This sprint
- **P3 (Low)**: 2 issues → Next sprint

### By Category
- **Documentation**: 4 issues
- **Code Quality**: 4 issues
- **Duplicate Elimination**: 3 issues
- **Meta/Process**: 1 issue

### Quick Wins (< 30 min each)
1. Issue 4: Archive README.old.md (15 min)
2. Issue 3: Consolidate swarm_coordinator.py (30 min)
3. Issue 7: Move security docs (20 min)

### Medium Effort (1-3 hours each)
1. Issue 1: Consolidate bug docs (2-3 hours)
2. Issue 6: Create GitHub Issues from master (2-3 hours)
3. Issue 9: Convert TODOs to issues (1-2 hours)
4. Issue 10: Refactor validators (3-4 hours)

### High Impact Issues
1. Issue 1: Bug documentation consolidation → Single source of truth
2. Issue 2: Remove duplicate harborhomes → Eliminate confusion
3. Issue 5: Create Prep Connect issues → Unblock CI
4. Issue 6: Create sprint issues → Enable project management

---

**Next Step**: Start with Issue 4 (Quick Win, 15 min) to build momentum.
