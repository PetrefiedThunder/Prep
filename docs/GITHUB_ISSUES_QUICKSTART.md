# GitHub Issues Quick Start Guide

This guide explains how to create all the Ambiguity Remediation Sprint issues in GitHub.

## Overview

The sprint plan has been converted into:
- **24 GitHub Issues** organized across 4 sprints
- **4 Milestones** (one per sprint)
- **16 Labels** (9 epic labels, 4 sprint labels, 3 category labels)

## Files Created

1. **docs/GITHUB_ISSUES_MASTER.md** - Complete issue templates with full descriptions
2. **scripts/create_github_issues.py** - Automation script for creating issues via GitHub API
3. **docs/GITHUB_ISSUES_QUICKSTART.md** - This file

## Option 1: Automated Creation (Recommended)

### Prerequisites

```bash
# Install required package
pip install requests

# Set your GitHub Personal Access Token
export GITHUB_TOKEN=your_github_personal_access_token
```

### Getting a GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a descriptive name: "Prep Issue Creator"
4. Select scopes:
   - `repo` (Full control of private repositories)
5. Click "Generate token"
6. Copy the token and export it: `export GITHUB_TOKEN=ghp_...`

### Run the Script

```bash
# Preview what will be created (dry run)
python scripts/create_github_issues.py --repo PetrefiedThunder/Prep --dry-run

# Create only milestones
python scripts/create_github_issues.py --repo PetrefiedThunder/Prep --milestones-only --execute

# Create only labels
python scripts/create_github_issues.py --repo PetrefiedThunder/Prep --labels-only --execute

# Create everything
python scripts/create_github_issues.py --repo PetrefiedThunder/Prep --execute
```

### What the Script Does

1. **Creates 4 Milestones:**
   - Sprint 1: Golden Path + System Clarity
   - Sprint 2: Jurisdiction Clarity + MVP
   - Sprint 3: Data Model, Payments, Compliance Engine
   - Sprint 4: Observability + Cleanup

2. **Creates 16 Labels:**
   - Epic labels (green): `epic-a-golden-path`, `epic-b-system-map`, etc.
   - Sprint labels (purple): `sprint-1`, `sprint-2`, `sprint-3`, `sprint-4`
   - Category labels: `documentation`, `infrastructure`, `testing`

3. **Creates 24 Issues:**
   - Each issue includes title, description, acceptance criteria, labels, and milestone
   - Issues are linked to their parent epic for context

## Option 2: Manual Creation

If you prefer to create issues manually or don't have API access, use the templates in `docs/GITHUB_ISSUES_MASTER.md`.

### Steps

1. **Create Milestones** (GitHub → Issues → Milestones → New milestone)
   - Follow the milestone definitions in GITHUB_ISSUES_MASTER.md

2. **Create Labels** (GitHub → Issues → Labels → New label)
   - Follow the label definitions in GITHUB_ISSUES_MASTER.md
   - Use the specified colors for consistency

3. **Create Issues** (GitHub → Issues → New issue)
   - Copy each issue template from GITHUB_ISSUES_MASTER.md
   - Add the appropriate labels and milestone
   - Create issues in order (A1, A2, A3, etc.)

## Issue Organization

### By Sprint

- **Sprint 1** (6 issues): Foundation work - Golden Path + System Map
- **Sprint 2** (5 issues): Scope definition - Jurisdiction + MVP
- **Sprint 3** (9 issues): Core architecture - Data Model + Payments + Compliance
- **Sprint 4** (4 issues): Quality - Observability + Cleanup

### By Epic

- **Epic A** - Golden Path Demo (4 issues)
- **Epic B** - System Map (2 issues)
- **Epic C** - Jurisdiction Clarity (3 issues)
- **Epic D** - MVP Definition (2 issues)
- **Epic E** - Data Model (3 issues)
- **Epic G** - Payments (2 issues)
- **Epic H** - Compliance Engine (3 issues)
- **Epic I** - Observability (2 issues)
- **Epic J** - Cleanup (2 issues)

### By Type

- **Documentation**: 11 issues
- **Infrastructure**: 7 issues
- **Testing**: 6 issues

## Workflow Recommendations

### 1. Sequential Sprint Execution

Execute sprints in order:
1. Start with Sprint 1 (Foundation)
2. Move to Sprint 2 (Scope)
3. Then Sprint 3 (Architecture)
4. Finish with Sprint 4 (Quality)

### 2. Parallel Execution Within Sprints

Within each sprint, issues can often be worked in parallel by different team members:

**Sprint 1 Parallelization:**
- Track 1: Epic A (Golden Path) - 4 issues
- Track 2: Epic B (System Map) - 2 issues

**Sprint 2 Parallelization:**
- Track 1: Epic C (Jurisdiction) - 3 issues
- Track 2: Epic D (MVP) - 2 issues

**Sprint 3 Parallelization:**
- Track 1: Epic E (Data Model) - 3 issues
- Track 2: Epic G (Payments) - 2 issues
- Track 3: Epic H (Compliance) - 3 issues

**Sprint 4 Parallelization:**
- Track 1: Epic I (Observability) - 2 issues
- Track 2: Epic J (Cleanup) - 2 issues

### 3. Epic-Based Assignment

Assign entire epics to team members based on expertise:
- Backend engineer → Epics G (Payments), H (Compliance)
- DevOps engineer → Epics A (Golden Path), I (Observability)
- Documentation specialist → Epics B (System Map), D (MVP), E (Data Model)
- QA engineer → Epic C (Jurisdiction testing)
- Tech lead → Epic J (Cleanup)

## Project Board Setup (Optional)

Create a GitHub Project board with columns:
- **Backlog** - All unstarted issues
- **Sprint 1** - Current sprint 1 work
- **Sprint 2** - Current sprint 2 work
- **Sprint 3** - Current sprint 3 work
- **Sprint 4** - Current sprint 4 work
- **In Progress** - Actively being worked
- **Review** - Awaiting PR review
- **Done** - Completed

## Tracking Progress

### GitHub Milestones View

Navigate to: `https://github.com/PetrefiedThunder/Prep/milestones`

This shows:
- Progress per sprint (% complete)
- Open vs closed issues
- Due dates (if set)

### GitHub Labels View

Navigate to: `https://github.com/PetrefiedThunder/Prep/labels`

Filter by:
- Epic labels to see all issues in an epic
- Sprint labels to see all issues in a sprint
- Category labels to see all documentation/infrastructure/testing work

## Next Steps After Issue Creation

1. **Assign Issues** - Assign team members to issues
2. **Set Due Dates** - Add due dates to milestones
3. **Create Project Board** - Set up GitHub Projects for kanban view
4. **Link to PRs** - Reference issue numbers in PR descriptions
5. **Update Status** - Close issues as work is completed

## Tips

- Use issue templates for consistency
- Link related issues with "Relates to #X" or "Blocks #X"
- Add acceptance criteria checklists to track sub-task completion
- Use labels to filter and organize work
- Reference issues in commit messages: "Fixes #123" to auto-close

## Verification

After running the automation script, verify:

```bash
# Check milestones were created
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/PetrefiedThunder/Prep/milestones

# Check labels were created
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/PetrefiedThunder/Prep/labels

# Check issues were created
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/PetrefiedThunder/Prep/issues?state=all
```

## Troubleshooting

### Issue: "GITHUB_TOKEN not set"
**Solution:** Export your GitHub personal access token:
```bash
export GITHUB_TOKEN=ghp_your_token_here
```

### Issue: "403 Forbidden"
**Solution:** Ensure your token has `repo` scope permissions

### Issue: "Milestone not found"
**Solution:** Run with `--milestones-only` first, then create issues

### Issue: "Label not found"
**Solution:** Run with `--labels-only` first, then create issues

### Issue: "Dry run shows nothing"
**Solution:** This is expected - dry run only previews, use `--execute` to create

## Support

For questions or issues:
1. Check the GITHUB_ISSUES_MASTER.md for full issue details
2. Review the create_github_issues.py script
3. Consult GitHub's API documentation: https://docs.github.com/en/rest

---

**Happy sprint planning! 🚀**
