#!/usr/bin/env python3
"""
Script to create GitHub issues based on comprehensive codebase analysis.
This script identifies and categorizes issues that should be tracked.

Usage:
    python scripts/create_codebase_issues.py --dry-run  # Preview issues
    python scripts/create_codebase_issues.py             # Create issues (requires GITHUB_TOKEN)
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def get_issues():
    """Return list of issues to create."""
    return [
        {
            "title": "Fix code quality issues (ruff linting)",
            "labels": ["code-quality", "good-first-issue", "technical-debt"],
            "priority": "P2",
            "body": """## Summary
Fix 15 minor code quality issues identified by ruff linting tool.

## Details
Current ruff scan shows 15 linting issues across the codebase:
- Import sorting (I001): 3 files
- Unused imports (F401): 2 occurrences
- Deprecated type annotations (UP035, UP045, UP006): 8 occurrences
- Minor style issues (SIM108, F541): 2 occurrences

**Note**: 12 of these are auto-fixable with `ruff check . --fix`

## Files Affected
- `apps/vendor_verification/auth.py`
- `prep/ai/swarm_config.py`
- `scripts/bootstrap_mvp.py`

## Steps to Fix
```bash
# Auto-fix most issues
ruff check . --fix

# Review and manually fix remaining issues
ruff check .
```

## Acceptance Criteria
- [ ] All ruff linting errors resolved
- [ ] Code maintains consistent formatting
- [ ] No new linting issues introduced
- [ ] All existing tests still pass

## Priority
P2 - Low priority, can be fixed incrementally during other work
"""
        },
        {
            "title": "Improve test coverage for core modules",
            "labels": ["testing", "technical-debt", "quality"],
            "priority": "P1",
            "body": """## Summary
Improve test coverage for 41 Python modules in the `prep/` directory that currently lack dedicated test files.

## Current State
Test coverage scan identified **41 modules** without corresponding test files, including critical modules like:
- `prep/settings.py` - Configuration management
- `prep/main.py` - Application entry point
- `prep/cache.py` - Caching layer
- `prep/ai/agent_framework.py` - Agent system core
- `prep/ai/swarm_coordinator.py` - Swarm coordination
- And 36 more modules...

## Why This Matters
- **Reliability**: Untested code is prone to bugs
- **Refactoring Safety**: Tests enable confident refactoring
- **Documentation**: Tests serve as usage examples
- **MVP Goal**: Target is 55%+ test coverage

## Recommended Approach
1. **Prioritize by Impact**: Start with most-used modules (settings, cache, main)
2. **Incremental Addition**: Add tests module by module
3. **Focus on Public APIs**: Test public functions and critical paths
4. **Use Existing Patterns**: Follow test patterns in `tests/` directory

## Acceptance Criteria
- [ ] Tests added for top 10 highest-priority modules
- [ ] Test coverage increases to 55%+
- [ ] All new tests pass in CI
- [ ] Tests follow existing patterns and conventions

## Priority
P1 - High priority, directly supports MVP goal of 55%+ coverage
"""
        },
        {
            "title": "Audit and expand E2E test coverage for MVP flows",
            "labels": ["testing", "e2e", "mvp-critical"],
            "priority": "P0",
            "body": """## Summary
Ensure end-to-end test coverage exists for the complete MVP user journey: Signup → Search → Book → Pay → Receipt.

## Context
Per the MVP goal (Dec 7, 2025), we need:
- ✅ Complete E2E flow working without manual intervention
- ✅ E2E pass rate ≥ 95%
- ✅ Tests running in Playwright CI
- ❌ **Current Gap**: E2E flows are incomplete (15% complete per README)

## Required E2E Test Scenarios
1. Complete happy path (new user signup through payment)
2. Existing user login → search → book → pay
3. Search with filters (date, capacity, amenities)
4. Booking modification/cancellation
5. Payment failure handling
6. Session timeout handling

## Implementation Steps
1. Setup Playwright with proper test environment
2. Create test data fixtures (test kitchens, users)
3. Configure Stripe test mode for payment testing
4. Implement happy path test end-to-end
5. Add error scenario tests
6. Configure CI pipeline to run E2E tests
7. Set up test reporting with screenshots/videos on failure

## Acceptance Criteria
- [ ] Complete happy path test passes consistently (95%+ success rate)
- [ ] 5+ critical path tests implemented
- [ ] 3+ error scenario tests implemented
- [ ] Tests run automatically in CI
- [ ] Test failures include screenshots/videos
- [ ] Test execution time < 5 minutes
- [ ] No mocks - real API calls to test environment

## Priority
P0 - **CRITICAL** - Required for MVP launch (Dec 7, 2025)
"""
        },
        {
            "title": "Frontend-Backend Integration: Wire real APIs",
            "labels": ["frontend", "backend", "integration", "mvp-critical"],
            "priority": "P0",
            "body": """## Summary
Replace all mock data in the HarborHomes Next.js frontend with real API calls to backend services.

## Context
From README: "Frontend is still mock-only: HarborHomes routes and mock-data utilities serve static responses; no backend connectivity is wired yet"

## Current State (Mock Data)
The frontend currently uses mock utilities and no actual network requests to backend.

## Target State (Real Integration)
- Frontend makes real HTTP requests to backend APIs
- Authentication with JWT tokens
- Real-time data from PostgreSQL
- Proper error handling
- Loading states

## Key Integration Points
1. Authentication (login/signup)
2. Kitchen search (GET /api/kitchens/search)
3. Booking creation (POST /api/bookings)
4. Payment processing (Stripe checkout)

## Implementation Plan
1. Create API client (`lib/api-client.ts`)
2. Configure environment (NEXT_PUBLIC_API_URL)
3. Replace mock functions page by page
4. Add loading states and error handling
5. Test integration at each step

## Acceptance Criteria
- [ ] API client created with proper typing
- [ ] Authentication flow uses real JWT tokens
- [ ] Kitchen search fetches data from PostgreSQL
- [ ] Booking creation persists to database
- [ ] Payment processing uses real Stripe (test mode)
- [ ] All mock data utilities removed or deprecated
- [ ] Error handling covers network failures
- [ ] Loading states implemented throughout
- [ ] E2E tests pass with real API integration

## Priority
P0 - **CRITICAL** - Required for MVP, currently blocking complete user flows
"""
        },
        {
            "title": "Implement proper error handling and logging",
            "labels": ["logging", "error-handling", "observability"],
            "priority": "P1",
            "body": """## Summary
Implement comprehensive error handling and structured logging across all services to improve observability and debugging.

## Context
Based on previous bug reports mentioning "silently ignored errors" and "empty catch blocks", we need to ensure all errors are properly logged and handled.

## Current Gaps
1. Silent Failures: Catch blocks without logging
2. Poor Error Context: Errors without sufficient debugging information
3. No Centralized Logging: Inconsistent logging patterns
4. Missing Error Tracking: No integration with error tracking service

## Implementation Plan
1. Python: Implement structured logging with structlog
2. TypeScript: Use Winston for consistent logging
3. Frontend: Implement error boundary with reporting
4. Standards: Never use empty catch blocks, always include context

## Standards to Implement
1. Never use empty catch blocks - Always log at minimum
2. Include context - User ID, request ID, relevant IDs
3. Log levels - ERROR for failures, WARN for recoverable, INFO for significant events
4. Structured logs - JSON format for machine parsing
5. Sensitive data - Redact passwords, tokens, PII from logs

## Acceptance Criteria
- [ ] All catch blocks include error logging
- [ ] Structured logging implemented in Python services
- [ ] Winston logging configured in TypeScript services
- [ ] Frontend has error boundary with reporting
- [ ] Log format is consistent across all services
- [ ] Sensitive data redacted from logs
- [ ] Documentation added for logging standards

## Priority
P1 - High priority, critical for production observability
"""
        },
        {
            "title": "Database connection pooling and resilience",
            "labels": ["database", "infrastructure", "reliability"],
            "priority": "P1",
            "body": """## Summary
Ensure database connections use proper pooling and implement resilience patterns (retries, circuit breakers) for production reliability.

## Context
With multiple services connecting to PostgreSQL, proper connection management is critical for:
- Performance (connection reuse)
- Reliability (handling transient failures)
- Resource management (preventing connection exhaustion)

## Best Practices to Implement
1. Connection pool configuration (size, timeouts, recycling)
2. Retry logic for transient failures
3. Circuit breaker pattern for database calls
4. Health check endpoints
5. Connection monitoring and metrics

## Implementation Tasks
- [ ] Audit current connection pool configurations
- [ ] Implement connection pooling with appropriate limits
- [ ] Add retry logic for transient database errors
- [ ] Implement circuit breaker for database calls
- [ ] Add database health check endpoints
- [ ] Configure connection timeout values
- [ ] Implement graceful degradation (use cache on DB failure)
- [ ] Add monitoring for connection pool metrics
- [ ] Document database connection best practices

## Metrics to Monitor
- Connection pool utilization
- Connection acquisition time
- Query execution time
- Failed connection attempts
- Circuit breaker state

## Acceptance Criteria
- [ ] All services use connection pooling
- [ ] Retry logic handles transient failures
- [ ] Circuit breaker prevents cascade failures
- [ ] Health check endpoints implemented
- [ ] Connection pool metrics exposed
- [ ] Documentation includes DB resilience patterns
- [ ] Load testing validates connection handling

## Priority
P1 - High priority, critical for production stability
"""
        },
        {
            "title": "TypeScript strict mode compliance",
            "labels": ["typescript", "code-quality", "technical-debt"],
            "priority": "P2",
            "body": """## Summary
Ensure all TypeScript code complies with strict mode type checking.

## Context
The repository uses TypeScript across multiple services. Ensuring strict mode compliance improves type safety and catches potential bugs at compile time.

## Benefits of Strict Mode
- Type Safety: Catch more bugs at compile time
- Better IDE Support: Improved autocomplete and refactoring
- Code Quality: Forces explicit typing of edge cases
- Maintainability: Easier to understand code intent

## Implementation Steps
1. Audit current strict mode status
2. Enable strict mode if not already enabled
3. Fix type errors service by service
4. Add ESLint rules to prevent type issues

## Acceptance Criteria
- [ ] All TypeScript services compile with strict mode enabled
- [ ] No use of `any` type (use `unknown` when necessary)
- [ ] All function parameters have explicit types
- [ ] Null/undefined properly handled throughout
- [ ] ESLint rules enforce strict typing
- [ ] Documentation updated with type safety guidelines

## Priority
P2 - Medium priority, improves long-term code quality
"""
        },
        {
            "title": "Add module-level docstrings to key modules",
            "labels": ["documentation", "good-first-issue"],
            "priority": "P2",
            "body": """## Summary
Add module-level docstrings to Python modules that are missing them.

## Why This Matters
- Discoverability: Helps developers understand module purpose
- IDE Support: Enables better IDE documentation tooltips
- Code Quality: Following PEP 257 conventions
- Onboarding: Makes it easier for new developers

## Standards
- Follow PEP 257 conventions
- Include module purpose and key functionality
- Add usage examples for complex modules
- Keep docstrings concise but informative

## Acceptance Criteria
- [ ] Identified modules have module-level docstrings
- [ ] Docstrings follow PEP 257 format
- [ ] Documentation builds without warnings
- [ ] PR includes docstring additions only (no logic changes)

## Priority
P2 - Medium priority, improves developer experience
"""
        }
    ]


def preview_issues(issues):
    """Preview issues that would be created."""
    print("\n" + "=" * 80)
    print("GITHUB ISSUES TO BE CREATED")
    print("=" * 80)
    
    for i, issue in enumerate(issues, 1):
        print(f"\n{'=' * 80}")
        print(f"Issue {i}/{len(issues)}")
        print(f"{'=' * 80}")
        print(f"Title: {issue['title']}")
        print(f"Labels: {', '.join(issue['labels'])}")
        print(f"Priority: {issue['priority']}")
        print(f"\nBody Preview (first 500 chars):")
        print("-" * 80)
        print(issue['body'][:500] + "...")
        print("-" * 80)
    
    print(f"\n{'=' * 80}")
    print(f"Total Issues: {len(issues)}")
    print(f"{'=' * 80}\n")


def save_issues_to_file(issues):
    """Save issues to a JSON file for documentation."""
    output_file = Path("/home/runner/work/Prep/Prep/IDENTIFIED_ISSUES.json")
    
    issues_data = {
        "generated_at": datetime.now().isoformat(),
        "total_issues": len(issues),
        "issues": issues
    }
    
    with open(output_file, 'w') as f:
        json.dump(issues_data, f, indent=2)
    
    print(f"\n✅ Issues saved to: {output_file}")
    
    # Also create a markdown summary
    md_file = Path("/home/runner/work/Prep/Prep/IDENTIFIED_ISSUES.md")
    with open(md_file, 'w') as f:
        f.write("# Identified Codebase Issues\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total Issues**: {len(issues)}\n\n")
        
        # Group by priority
        by_priority = {}
        for issue in issues:
            priority = issue['priority']
            if priority not in by_priority:
                by_priority[priority] = []
            by_priority[priority].append(issue)
        
        f.write("## Issues by Priority\n\n")
        for priority in ['P0', 'P1', 'P2']:
            if priority in by_priority:
                f.write(f"### {priority} - {len(by_priority[priority])} issues\n\n")
                for issue in by_priority[priority]:
                    f.write(f"- **{issue['title']}**\n")
                    f.write(f"  - Labels: {', '.join(issue['labels'])}\n\n")
        
        f.write("\n## Detailed Issues\n\n")
        for i, issue in enumerate(issues, 1):
            f.write(f"### {i}. {issue['title']}\n\n")
            f.write(f"**Priority**: {issue['priority']}\n\n")
            f.write(f"**Labels**: {', '.join(issue['labels'])}\n\n")
            f.write(issue['body'])
            f.write("\n\n---\n\n")
    
    print(f"✅ Markdown summary saved to: {md_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Create GitHub issues from codebase analysis")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview issues without creating them"
    )
    
    args = parser.parse_args()
    
    issues = get_issues()
    
    print("\n" + "=" * 80)
    print("PREP CODEBASE ISSUE GENERATOR")
    print("=" * 80)
    print(f"\nMode: {'DRY RUN (Preview Only)' if args.dry_run else 'CREATE ISSUES'}")
    print(f"Total Issues to Create: {len(issues)}\n")
    
    # Always preview
    preview_issues(issues)
    
    # Save to files
    save_issues_to_file(issues)
    
    if args.dry_run:
        print("\n✅ Dry run complete. No issues created.")
        print("\nTo create these issues, run without --dry-run:")
        print("  python scripts/create_codebase_issues.py\n")
        return 0
    
    print("\n⚠️  ISSUE CREATION NOT IMPLEMENTED YET")
    print("This script currently generates issue templates as documentation.")
    print("Issues should be manually created in GitHub using the generated templates.")
    print("\nSee IDENTIFIED_ISSUES.md for the full issue list.\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
