# Prep Setup Command

Load Prep repository context and prepare for development session.

## Actions

1. Read master context:
   - Load `.claude/CONTEXT.md`

2. Load active agent profiles:
   - `python-development.md` - Modern Python patterns
   - `backend-development.md` - API and service design
   - `security-scanning.md` - Security auditing
   - `testing-tdd.md` - Test-driven development
   - `code-review-ai.md` - Code quality review

3. Check repository status:
   - Current git branch
   - Recent commits (last 5)
   - Uncommitted changes
   - Active session (if using cc-sessions)

4. Confirm readiness:
   - Environment: Warp + Claude Code
   - Python version: 3.11+
   - Virtual environment: `.venv/` active
   - Database: PostgreSQL connection available
   - Redis: Connection available (if needed)

## Expected Output

```
📋 Prep Repository Ready

Branch: main (or current branch)
Recent Commits:
- abc123f feat: add JWT refresh token support
- def456g fix: resolve N+1 query in bookings
- ghi789h test: add coverage for auth flows
...

Uncommitted Changes: 3 modified files
- prep/auth/core.py
- tests/auth/test_core_helpers.py
- .env.example

Active Agent Profiles:
✅ python-development
✅ backend-development
✅ security-scanning
✅ testing-tdd
✅ code-review-ai

Workflow: ContextKit 4-Phase (Plan → Implement → Test → Report)

Ready for work. What would you like to build?
```

## Usage

```
/prep-setup
```

Or manually:
```
Read .claude/CONTEXT.md
Read .claude/agents/python-development.md
Read .claude/agents/backend-development.md
Read .claude/agents/security-scanning.md
Read .claude/agents/testing-tdd.md
Read .claude/agents/code-review-ai.md
```
