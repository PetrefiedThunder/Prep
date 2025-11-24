#!/usr/bin/env python3
"""
GitHub Failed Checks and Jobs Issue Creator

This script finds all failed checks and jobs in the repository's GitHub Actions workflows
and creates GitHub issues for each failure.

Usage:
    export GITHUB_TOKEN=your_personal_access_token
    python scripts/create_failure_issues.py --repo PetrefiedThunder/Prep --dry-run
    python scripts/create_failure_issues.py --repo PetrefiedThunder/Prep --execute
    
    # Limit to specific workflows:
    python scripts/create_failure_issues.py --repo PetrefiedThunder/Prep --workflow ci.yml --execute
    
    # Limit number of runs to check:
    python scripts/create_failure_issues.py --repo PetrefiedThunder/Prep --max-runs 50 --execute

Requirements:
    pip install requests
"""

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

# Set a reasonable timeout for all HTTP requests (30 seconds)
REQUEST_TIMEOUT = 30


@dataclass
class FailedJob:
    """Represents a failed GitHub Actions job"""

    workflow_name: str
    workflow_file: str
    run_id: int
    run_number: int
    job_name: str
    job_id: int
    conclusion: str
    html_url: str
    started_at: str
    completed_at: str
    run_url: str
    head_sha: str
    head_branch: str


class GitHubFailureTracker:
    """Tracks and creates issues for failed GitHub Actions workflows"""

    def __init__(self, repo: str, token: str):
        self.repo = repo
        self.token = token
        self.base_url = f"https://api.github.com/repos/{repo}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def get_workflows(self) -> list[dict[str, Any]]:
        """Get all workflows in the repository"""
        url = f"{self.base_url}/actions/workflows"
        response = requests.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            workflows = response.json()["workflows"]
            print(f"✓ Found {len(workflows)} workflows")
            return workflows
        else:
            print(f"✗ Failed to get workflows: {response.text}")
            return []

    def get_failed_runs(
        self, workflow_id: int | None = None, max_runs: int = 100
    ) -> list[dict[str, Any]]:
        """Get failed workflow runs"""
        failed_runs: list[dict[str, Any]] = []

        if workflow_id:
            url = f"{self.base_url}/actions/workflows/{workflow_id}/runs"
        else:
            url = f"{self.base_url}/actions/runs"

        params = {
            "status": "completed",
            "per_page": min(max_runs, 100),
        }

        response = requests.get(
            url, headers=self.headers, params=params, timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            all_runs = response.json()["workflow_runs"]
            # Filter for failed or errored runs
            failed_runs = [
                run
                for run in all_runs
                if run["conclusion"] in ["failure", "cancelled", "timed_out", "action_required"]
            ]
            return failed_runs
        else:
            print(f"✗ Failed to get workflow runs: {response.text}")
            return []

    def get_failed_jobs(self, run_id: int) -> list[FailedJob]:
        """Get failed jobs for a specific workflow run"""
        url = f"{self.base_url}/actions/runs/{run_id}/jobs"
        response = requests.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT)

        failed_jobs: list[FailedJob] = []

        if response.status_code == 200:
            jobs = response.json()["jobs"]

            for job in jobs:
                if job["conclusion"] in ["failure", "cancelled", "timed_out"]:
                    failed_jobs.append(
                        FailedJob(
                            workflow_name=job.get("workflow_name", "Unknown"),
                            workflow_file=job.get("run_url", "").split("/")[-3]
                            if "run_url" in job
                            else "unknown",
                            run_id=run_id,
                            run_number=job.get("run_number", 0),
                            job_name=job["name"],
                            job_id=job["id"],
                            conclusion=job["conclusion"],
                            html_url=job["html_url"],
                            started_at=job.get("started_at", ""),
                            completed_at=job.get("completed_at", ""),
                            run_url=job.get("run_url", ""),
                            head_sha=job.get("head_sha", ""),
                            head_branch=job.get("head_branch", ""),
                        )
                    )

        return failed_jobs

    def get_existing_issues(self, label: str = "ci-failure") -> list[dict[str, Any]]:
        """Get existing issues with the ci-failure label"""
        url = f"{self.base_url}/issues"
        params = {"labels": label, "state": "all", "per_page": 100}

        response = requests.get(
            url, headers=self.headers, params=params, timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            return response.json()
        return []

    def create_issue_for_failure(
        self, failed_job: FailedJob, dry_run: bool = True
    ) -> dict[str, Any] | None:
        """Create a GitHub issue for a failed job"""

        # Generate a unique identifier for this failure
        failure_id = hashlib.md5(
            f"{failed_job.workflow_name}:{failed_job.job_name}".encode()
        ).hexdigest()[:8]

        title = f"[CI Failure] {failed_job.workflow_name} - {failed_job.job_name}"

        body = f"""## CI Failure Report

**Workflow:** {failed_job.workflow_name}  
**Job:** {failed_job.job_name}  
**Conclusion:** `{failed_job.conclusion}`  
**Run:** [#{failed_job.run_number}]({failed_job.run_url})  
**Branch:** `{failed_job.head_branch}`  
**Commit:** `{failed_job.head_sha[:7]}`  

### Details

- **Started:** {failed_job.started_at}
- **Completed:** {failed_job.completed_at}
- **Job URL:** {failed_job.html_url}

### Next Steps

1. Review the [job logs]({failed_job.html_url})
2. Identify the root cause of the failure
3. Fix the issue or update the workflow configuration
4. Close this issue once resolved

### Failure ID
`{failure_id}` (for deduplication)

---
*This issue was automatically created by the CI failure tracker.*
"""

        labels = ["ci-failure", "github-actions", "automated"]

        if dry_run:
            print(f"\n[DRY RUN] Would create issue:")
            print(f"  Title: {title}")
            print(f"  Labels: {', '.join(labels)}")
            print(f"  Job URL: {failed_job.html_url}")
            return None

        # Check if issue already exists
        existing_issues = self.get_existing_issues()
        for issue in existing_issues:
            if failure_id in issue.get("body", ""):
                print(
                    f"✓ Issue already exists for {failed_job.job_name}: #{issue['number']}"
                )
                return issue

        # Create the issue
        url = f"{self.base_url}/issues"
        data = {"title": title, "body": body, "labels": labels}

        response = requests.post(
            url, headers=self.headers, json=data, timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 201:
            issue = response.json()
            print(f"✓ Created issue #{issue['number']}: {title}")
            return issue
        else:
            print(f"✗ Failed to create issue: {response.text}")
            return None

    def ensure_labels_exist(self) -> None:
        """Ensure required labels exist in the repository"""
        required_labels = [
            {
                "name": "ci-failure",
                "color": "d73a4a",
                "description": "CI/CD pipeline failure",
            },
            {
                "name": "github-actions",
                "color": "2088FF",
                "description": "Related to GitHub Actions workflows",
            },
            {
                "name": "automated",
                "color": "fbca04",
                "description": "Automatically created issue",
            },
        ]

        for label_data in required_labels:
            url = f"{self.base_url}/labels"
            # Check if label exists
            check_url = f"{url}/{label_data['name']}"
            response = requests.get(
                check_url, headers=self.headers, timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 404:
                # Create the label
                response = requests.post(
                    url, headers=self.headers, json=label_data, timeout=REQUEST_TIMEOUT
                )
                if response.status_code == 201:
                    print(f"✓ Created label: {label_data['name']}")
                else:
                    print(f"✗ Failed to create label {label_data['name']}: {response.text}")
            else:
                print(f"✓ Label exists: {label_data['name']}")

    def process_failures(
        self,
        workflow_filter: str | None = None,
        max_runs: int = 100,
        dry_run: bool = True,
    ) -> None:
        """Process all failures and create issues"""

        print("\n=== Ensuring labels exist ===")
        self.ensure_labels_exist()

        print("\n=== Fetching workflows ===")
        workflows = self.get_workflows()

        if workflow_filter:
            workflows = [w for w in workflows if workflow_filter in w["path"]]
            print(f"Filtered to {len(workflows)} workflows matching '{workflow_filter}'")

        all_failures: list[FailedJob] = []

        print("\n=== Fetching failed runs ===")
        for workflow in workflows:
            print(f"\nChecking workflow: {workflow['name']} ({workflow['path']})")
            failed_runs = self.get_failed_runs(workflow["id"], max_runs)

            if not failed_runs:
                print(f"  No failures found")
                continue

            print(f"  Found {len(failed_runs)} failed runs")

            for run in failed_runs[:10]:  # Limit to 10 most recent failures per workflow
                failed_jobs = self.get_failed_jobs(run["id"])
                if failed_jobs:
                    print(
                        f"    Run #{run['run_number']}: {len(failed_jobs)} failed jobs"
                    )
                    all_failures.extend(failed_jobs)

        if not all_failures:
            print("\n✓ No failures found!")
            return

        print(f"\n=== Found {len(all_failures)} total failed jobs ===")

        # Deduplicate by workflow + job name
        unique_failures: dict[str, FailedJob] = {}
        for failure in all_failures:
            key = f"{failure.workflow_name}:{failure.job_name}"
            if key not in unique_failures:
                unique_failures[key] = failure

        print(f"=== {len(unique_failures)} unique failures after deduplication ===")

        if dry_run:
            print("\n=== DRY RUN MODE ===")
            print(f"Would create {len(unique_failures)} issues\n")
        else:
            print("\n=== CREATING ISSUES ===\n")

        created = 0
        skipped = 0

        for failure in unique_failures.values():
            result = self.create_issue_for_failure(failure, dry_run)
            if result:
                created += 1
            elif not dry_run:
                skipped += 1

        print("\n=== SUMMARY ===")
        print(f"Total failures found: {len(all_failures)}")
        print(f"Unique failures: {len(unique_failures)}")
        if not dry_run:
            print(f"Issues created: {created}")
            print(f"Issues skipped (already exist): {skipped}")


def main():
    parser = argparse.ArgumentParser(
        description="Create GitHub issues for failed CI checks and jobs"
    )
    parser.add_argument(
        "--repo", required=True, help="GitHub repository (e.g., owner/repo)"
    )
    parser.add_argument(
        "--workflow",
        help="Filter by workflow file name (e.g., ci.yml)",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=100,
        help="Maximum number of runs to check per workflow (default: 100)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be created without creating"
    )
    parser.add_argument("--execute", action="store_true", help="Actually create the issues")

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("Error: Must specify either --dry-run or --execute")
        sys.exit(1)

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set")
        sys.exit(1)

    tracker = GitHubFailureTracker(args.repo, token)
    tracker.process_failures(
        workflow_filter=args.workflow,
        max_runs=args.max_runs,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
