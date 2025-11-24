# CI Failure Tracking

This document describes how to use the CI failure tracking system to automatically create GitHub issues for failed checks and jobs.

## Overview

The `create_failure_issues.py` script monitors GitHub Actions workflow runs and creates issues for any failures it finds. This helps track and resolve CI/CD issues systematically.

## Features

- **Automatic Detection**: Scans all workflows for failed, cancelled, or timed out runs
- **Deduplication**: Prevents duplicate issues for the same failure type
- **Detailed Reports**: Each issue includes workflow details, job information, and direct links to logs
- **Filtering**: Can focus on specific workflows or limit the number of runs to check
- **Dry-Run Mode**: Preview what issues would be created before actually creating them

## Prerequisites

1. GitHub Personal Access Token with `repo` scope
2. Python 3.11+ installed
3. `requests` library (`pip install requests`)

## Usage

### Basic Usage

```bash
# Set your GitHub token
export GITHUB_TOKEN=your_personal_access_token

# Dry run - see what would be created
python scripts/create_failure_issues.py --repo PetrefiedThunder/Prep --dry-run

# Actually create the issues
python scripts/create_failure_issues.py --repo PetrefiedThunder/Prep --execute
```

### Advanced Options

```bash
# Check only a specific workflow
python scripts/create_failure_issues.py \
  --repo PetrefiedThunder/Prep \
  --workflow ci.yml \
  --execute

# Limit to recent runs (default is 100)
python scripts/create_failure_issues.py \
  --repo PetrefiedThunder/Prep \
  --max-runs 50 \
  --execute

# Combine options
python scripts/create_failure_issues.py \
  --repo PetrefiedThunder/Prep \
  --workflow python-ci.yml \
  --max-runs 30 \
  --dry-run
```

## How It Works

1. **Fetch Workflows**: Retrieves all GitHub Actions workflows in the repository
2. **Find Failures**: For each workflow, fetches completed runs and filters for failures
3. **Extract Jobs**: Gets detailed job information for each failed run
4. **Deduplicate**: Groups failures by workflow + job name to avoid duplicates
5. **Check Existing**: Verifies if an issue already exists using a unique failure ID
6. **Create Issues**: Creates new issues for unique failures with detailed information

## Issue Format

Each created issue includes:

- **Title**: `[CI Failure] {Workflow Name} - {Job Name}`
- **Labels**: `ci-failure`, `github-actions`, `automated`
- **Body Contains**:
  - Workflow and job names
  - Failure conclusion (failure, cancelled, timed_out)
  - Run number and links
  - Branch and commit information
  - Timestamps
  - Direct link to job logs
  - Unique failure ID for deduplication

## Labels

The script automatically creates these labels if they don't exist:

- **ci-failure** (red): Indicates CI/CD pipeline failure
- **github-actions** (blue): Related to GitHub Actions workflows
- **automated** (yellow): Automatically created issue

## Deduplication Strategy

Issues are deduplicated using:

1. **Failure ID**: MD5 hash of `{workflow_name}:{job_name}`
2. **Existing Issues**: Checks all issues with `ci-failure` label for matching failure IDs

This ensures that multiple failures of the same job type only create one issue.

## Best Practices

1. **Run Regularly**: Schedule this script to run daily or weekly to catch new failures
2. **Start with Dry-Run**: Always use `--dry-run` first to preview issues
3. **Close Resolved Issues**: Close issues once the underlying problem is fixed
4. **Add Context**: Add comments to issues with additional debugging information
5. **Filter When Needed**: Use `--workflow` to focus on specific problem areas

## Troubleshooting

### "GITHUB_TOKEN environment variable not set"
- Make sure you've exported your GitHub token: `export GITHUB_TOKEN=your_token`

### "Must specify either --dry-run or --execute"
- Always include one of these flags to explicitly indicate your intention

### Too Many Issues Created
- Use `--max-runs` to limit the number of runs checked
- Use `--workflow` to focus on specific workflows
- Close duplicate or resolved issues regularly

### No Failures Found
- Great! Your CI is healthy
- Try increasing `--max-runs` to check more history
- Verify the repository and token have correct permissions

## Integration with CI

You can automate this script by adding it to your GitHub Actions:

```yaml
name: Track CI Failures
on:
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Monday
  workflow_dispatch:  # Manual trigger

jobs:
  track-failures:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install requests
      - name: Track failures
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python scripts/create_failure_issues.py \
            --repo ${{ github.repository }} \
            --max-runs 50 \
            --execute
```

## Related Scripts

- **scripts/create_github_issues.py**: Creates sprint planning issues
- **scripts/bootstrap_mvp.py**: Creates MVP milestone issues

## Contributing

To improve this script:

1. Test changes with `--dry-run` first
2. Ensure deduplication logic remains intact
3. Update this documentation for new features
4. Consider backward compatibility

## Support

For issues or questions:
- Check existing GitHub issues with the `ci-failure` label
- Review GitHub Actions documentation
- Consult the repository maintainers
