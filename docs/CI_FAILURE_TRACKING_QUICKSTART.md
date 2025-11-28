# Quick Start: CI Failure Tracking

This guide will help you quickly set up and run the CI failure tracking script.

## Step 1: Get a GitHub Token

1. Go to https://github.com/settings/tokens/new
2. Give it a name like "CI Failure Tracker"
3. Select scopes:
   - `repo` (Full control of private repositories)
   - `workflow` (Update GitHub Action workflows) - optional
4. Click "Generate token"
5. Copy the token (you won't see it again!)

## Step 2: Set Up Environment

```bash
# Export your token (replace with your actual token)
export GITHUB_TOKEN=ghp_your_token_here

# Verify it's set
echo $GITHUB_TOKEN
```

## Step 3: Run in Dry-Run Mode (Recommended First)

This shows what issues would be created without actually creating them:

```bash
cd /path/to/Prep

# Check all workflows
python scripts/create_failure_issues.py \
  --repo PetrefiedThunder/Prep \
  --dry-run

# Or check just one workflow
python scripts/create_failure_issues.py \
  --repo PetrefiedThunder/Prep \
  --workflow ci.yml \
  --dry-run
```

Expected output:
```
=== Ensuring labels exist ===
✓ Label exists: ci-failure
✓ Label exists: github-actions
✓ Label exists: automated

=== Fetching workflows ===
✓ Found 31 workflows

=== Fetching failed runs ===

Checking workflow: CI (.github/workflows/ci.yml)
  Found 8 failed runs
    Run #1324: 3 failed jobs
    Run #1322: 3 failed jobs

...

=== Found 24 total failed jobs ===
=== 8 unique failures after deduplication ===

=== DRY RUN MODE ===
Would create 8 issues

[DRY RUN] Would create issue:
  Title: [CI Failure] CI - test (apps/city_regulatory_service)
  Labels: ci-failure, github-actions, automated
  Job URL: https://github.com/PetrefiedThunder/Prep/actions/runs/19627223010/job/52337726449

...

=== SUMMARY ===
Total failures found: 24
Unique failures: 8
```

## Step 4: Create Issues for Real

Once you're satisfied with the dry-run output:

```bash
python scripts/create_failure_issues.py \
  --repo PetrefiedThunder/Prep \
  --execute
```

Expected output:
```
=== CREATING ISSUES ===

✓ Created issue #584: [CI Failure] CI - test (apps/city_regulatory_service)
✓ Created issue #585: [CI Failure] CI - test (apps/federal_regulatory_service)
✓ Issue already exists for test (apps/vendor_verification): #586
...

=== SUMMARY ===
Total failures found: 24
Unique failures: 8
Issues created: 7
Issues skipped (already exist): 1
```

## Step 5: Review Created Issues

1. Go to https://github.com/PetrefiedThunder/Prep/issues
2. Filter by label: `ci-failure`
3. Review each issue and:
   - Click the job URL to see logs
   - Investigate the root cause
   - Fix the issue
   - Close the issue once resolved

## Common Use Cases

### Weekly Failure Sweep
```bash
# Check last 50 runs across all workflows
python scripts/create_failure_issues.py \
  --repo PetrefiedThunder/Prep \
  --max-runs 50 \
  --execute
```

### Focus on Specific Workflow
```bash
# Only check Python CI workflow
python scripts/create_failure_issues.py \
  --repo PetrefiedThunder/Prep \
  --workflow python-ci.yml \
  --execute
```

### Quick Health Check
```bash
# Dry-run with limited runs
python scripts/create_failure_issues.py \
  --repo PetrefiedThunder/Prep \
  --max-runs 20 \
  --dry-run
```

## What Gets Created

Each issue includes:

```markdown
## CI Failure Report

**Workflow:** CI  
**Job:** test (apps/city_regulatory_service)  
**Conclusion:** `failure`  
**Run:** [#1324](https://github.com/.../runs/19627223010)  
**Branch:** `main`  
**Commit:** `2d83e7c`  

### Details

- **Started:** 2025-11-24T07:58:38Z
- **Completed:** 2025-11-24T08:01:43Z
- **Job URL:** https://github.com/.../job/52337726449

### Next Steps

1. Review the job logs
2. Identify the root cause of the failure
3. Fix the issue or update the workflow configuration
4. Close this issue once resolved

### Failure ID
`a1b2c3d4` (for deduplication)
```

## Tips

1. **Start Small**: Use `--max-runs 20` on first run
2. **Be Specific**: Use `--workflow` to target problem areas
3. **Dry Run First**: Always preview with `--dry-run`
4. **Review Regularly**: Run weekly to catch new failures
5. **Clean Up**: Close resolved issues to keep tracking current

## Troubleshooting

**"GITHUB_TOKEN environment variable not set"**
- Make sure you ran `export GITHUB_TOKEN=your_token`
- Check with: `echo $GITHUB_TOKEN`

**Too many issues created**
- Use `--max-runs 10` to limit history
- Use `--workflow specific.yml` to focus
- Issues are deduplicated automatically

**Script runs slowly**
- Reduce `--max-runs` value
- Check specific `--workflow` instead of all
- GitHub API has rate limits (5000 req/hour for authenticated)

## Next Steps

- Set up a weekly cron job to run automatically
- Add to GitHub Actions for automatic tracking
- Customize labels or issue format as needed
- See full documentation: [docs/CI_FAILURE_TRACKING.md](docs/CI_FAILURE_TRACKING.md)
