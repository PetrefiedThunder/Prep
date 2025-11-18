#!/usr/bin/env python3
"""
GitHub Issues Creator for Ambiguity Remediation Sprint
This script creates all GitHub issues from the master sprint plan.

Usage:
    export GITHUB_TOKEN=your_personal_access_token
    python scripts/create_github_issues.py --repo PetrefiedThunder/Prep --dry-run
    python scripts/create_github_issues.py --repo PetrefiedThunder/Prep --execute

Requirements:
    pip install requests
"""

import argparse
import os
import sys
from dataclasses import dataclass

import requests

# Set a reasonable timeout for all HTTP requests (30 seconds)
REQUEST_TIMEOUT = 30


@dataclass
class Issue:
    """Represents a GitHub issue"""

    title: str
    body: str
    labels: list[str]
    milestone: str
    epic_id: str
    task_id: str


class GitHubIssueCreator:
    """Creates GitHub issues via the GitHub API"""

    def __init__(self, repo: str, token: str):
        self.repo = repo
        self.token = token
        self.base_url = f"https://api.github.com/repos/{repo}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.milestones = {}
        self.labels = {}

    def create_milestones(self) -> None:
        """Create milestones for each sprint"""
        milestones_data = [
            {
                "title": "Sprint 1: Golden Path + System Clarity",
                "description": "One reproducible end-to-end flow and clear system documentation",
                "state": "open",
            },
            {
                "title": "Sprint 2: Jurisdiction Clarity + MVP",
                "description": "Explicit city-by-city regulatory coverage and MVP definition",
                "state": "open",
            },
            {
                "title": "Sprint 3: Data Model, Payments, Compliance Engine",
                "description": "Data model clarity, payment architecture, and compliance engine improvements",
                "state": "open",
            },
            {
                "title": "Sprint 4: Observability + Cleanup",
                "description": "SLOs, monitoring, and repository hygiene",
                "state": "open",
            },
        ]

        for milestone_data in milestones_data:
            milestone = self._create_milestone(milestone_data)
            if milestone:
                self.milestones[milestone_data["title"]] = milestone

    def _create_milestone(self, data: dict) -> dict | None:
        """Create a single milestone"""
        # Check if milestone already exists
        existing = self._get_existing_milestone(data["title"])
        if existing:
            print(f"✓ Milestone already exists: {data['title']}")
            return existing

        url = f"{self.base_url}/milestones"
        response = requests.post(url, headers=self.headers, json=data, timeout=REQUEST_TIMEOUT)

        if response.status_code == 201:
            milestone = response.json()
            print(f"✓ Created milestone: {data['title']}")
            return milestone
        else:
            print(f"✗ Failed to create milestone: {data['title']} - {response.text}")
            return None

    def _get_existing_milestone(self, title: str) -> dict | None:
        """Check if milestone already exists"""
        url = f"{self.base_url}/milestones"
        response = requests.get(
            url, headers=self.headers, params={"state": "all"}, timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            milestones = response.json()
            for milestone in milestones:
                if milestone["title"] == title:
                    return milestone
        return None

    def create_labels(self) -> None:
        """Create labels for epics and sprints"""
        labels_data = [
            {"name": "epic-a-golden-path", "color": "0E8A16", "description": "Golden Path Demo"},
            {
                "name": "epic-b-system-map",
                "color": "0E8A16",
                "description": "System Map & Service Classification",
            },
            {
                "name": "epic-c-jurisdiction",
                "color": "0E8A16",
                "description": "Jurisdiction Clarity",
            },
            {"name": "epic-d-mvp", "color": "0E8A16", "description": "MVP Definition"},
            {
                "name": "epic-e-data-model",
                "color": "0E8A16",
                "description": "Data Model & ERD Clarity",
            },
            {"name": "epic-g-payments", "color": "0E8A16", "description": "Payments Architecture"},
            {
                "name": "epic-h-compliance",
                "color": "0E8A16",
                "description": "Compliance Engine Architecture",
            },
            {
                "name": "epic-i-observability",
                "color": "0E8A16",
                "description": "Observability & SLOs",
            },
            {
                "name": "epic-j-cleanup",
                "color": "0E8A16",
                "description": "Cleanup & Repository Hygiene",
            },
            {"name": "sprint-1", "color": "D4C5F9", "description": "Sprint 1"},
            {"name": "sprint-2", "color": "D4C5F9", "description": "Sprint 2"},
            {"name": "sprint-3", "color": "D4C5F9", "description": "Sprint 3"},
            {"name": "sprint-4", "color": "D4C5F9", "description": "Sprint 4"},
            {"name": "documentation", "color": "0075CA", "description": "Documentation tasks"},
            {"name": "infrastructure", "color": "FFA500", "description": "Infrastructure tasks"},
            {"name": "testing", "color": "D93F0B", "description": "Testing tasks"},
        ]

        for label_data in labels_data:
            label = self._create_label(label_data)
            if label:
                self.labels[label_data["name"]] = label

    def _create_label(self, data: dict) -> dict | None:
        """Create a single label"""
        # Check if label already exists
        existing = self._get_existing_label(data["name"])
        if existing:
            print(f"✓ Label already exists: {data['name']}")
            return existing

        url = f"{self.base_url}/labels"
        response = requests.post(url, headers=self.headers, json=data, timeout=REQUEST_TIMEOUT)

        if response.status_code == 201:
            label = response.json()
            print(f"✓ Created label: {data['name']}")
            return label
        else:
            print(f"✗ Failed to create label: {data['name']} - {response.text}")
            return None

    def _get_existing_label(self, name: str) -> dict | None:
        """Check if label already exists"""
        url = f"{self.base_url}/labels/{name}"
        response = requests.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            return response.json()
        return None

    def create_issue(self, issue: Issue) -> dict | None:
        """Create a single GitHub issue"""
        milestone_number = None
        if issue.milestone in self.milestones:
            milestone_number = self.milestones[issue.milestone]["number"]

        data = {
            "title": issue.title,
            "body": issue.body,
            "labels": issue.labels,
            "milestone": milestone_number,
        }

        url = f"{self.base_url}/issues"
        response = requests.post(url, headers=self.headers, json=data, timeout=REQUEST_TIMEOUT)

        if response.status_code == 201:
            created_issue = response.json()
            print(f"✓ Created issue #{created_issue['number']}: {issue.title}")
            return created_issue
        else:
            print(f"✗ Failed to create issue: {issue.title} - {response.text}")
            return None

    def create_all_issues(self, issues: list[Issue], dry_run: bool = True) -> None:
        """Create all issues"""
        if dry_run:
            print("\n=== DRY RUN MODE ===")
            print(f"Would create {len(issues)} issues\n")
            for i, issue in enumerate(issues, 1):
                print(f"{i}. {issue.title}")
                print(f"   Labels: {', '.join(issue.labels)}")
                print(f"   Milestone: {issue.milestone}")
                print()
            return

        print("\n=== CREATING ISSUES ===\n")
        created = 0
        failed = 0

        for issue in issues:
            result = self.create_issue(issue)
            if result:
                created += 1
            else:
                failed += 1

        print("\n=== SUMMARY ===")
        print(f"Created: {created}")
        print(f"Failed: {failed}")
        print(f"Total: {len(issues)}")


def get_all_issues() -> list[Issue]:
    """Define all issues from the sprint plan"""
    issues = []

    # Sprint 1 - Epic A: Golden Path Demo
    issues.extend(
        [
            Issue(
                title="Create Golden Path Documentation",
                body="""Create comprehensive documentation for the Golden Path demo flow that demonstrates the complete LA Vendor → Compliance → Booking scenario.

**Acceptance Criteria:**
- [ ] Create docs/GOLDEN_PATH_DEMO.md
- [ ] Define LA Vendor → Compliance → Booking scenario
- [ ] Add step-by-step commands (clone, setup, compose)
- [ ] Include expected outputs and success criteria
- [ ] Add troubleshooting section

**Epic Context:**
Part of Epic A: Golden Path Demo - establishing one reproducible, end-to-end working flow.
""",
                labels=["epic-a-golden-path", "sprint-1", "documentation"],
                milestone="Sprint 1: Golden Path + System Clarity",
                epic_id="A",
                task_id="A1",
            ),
            Issue(
                title="Create Golden Path Fixtures",
                body="""Create sample data fixtures to support the Golden Path demo, enabling consistent and reproducible testing of the LA vendor flow.

**Acceptance Criteria:**
- [ ] Create vendor license sample data
- [ ] Create facility sample data
- [ ] Create LA jurisdiction ruleset fixture
- [ ] Add fixture loading scripts
- [ ] Document fixture usage in GOLDEN_PATH_DEMO.md

**Epic Context:**
Part of Epic A: Golden Path Demo - providing test data for the end-to-end flow.
""",
                labels=["epic-a-golden-path", "sprint-1", "testing"],
                milestone="Sprint 1: Golden Path + System Clarity",
                epic_id="A",
                task_id="A2",
            ),
            Issue(
                title="Fix Service Boot Consistency Issues",
                body="""Ensure all services boot consistently and reliably during docker compose up, with proper environment variable configuration.

**Acceptance Criteria:**
- [ ] Verify all required env vars exist across services
- [ ] Update .env.example with missing variables
- [ ] Fix failing services during docker compose up
- [ ] Add service health checks to docker-compose.yml
- [ ] Document service dependencies

**Epic Context:**
Part of Epic A: Golden Path Demo - ensuring reliable service startup for demos.
""",
                labels=["epic-a-golden-path", "sprint-1", "infrastructure"],
                milestone="Sprint 1: Golden Path + System Clarity",
                epic_id="A",
                task_id="A3",
            ),
            Issue(
                title="Add Observability for Golden Path Demo",
                body="""Implement observability and monitoring for the Golden Path flow to track events and validate the compliance → booking pipeline.

**Acceptance Criteria:**
- [ ] Add Grafana dashboard for Golden Path event flow
- [ ] Add log tracing for compliance → booking
- [ ] Add pytest -m golden_path regression test
- [ ] Create alert rules for Golden Path failures
- [ ] Document monitoring setup

**Epic Context:**
Part of Epic A: Golden Path Demo - providing visibility into the end-to-end flow.
""",
                labels=["epic-a-golden-path", "sprint-1", "infrastructure", "testing"],
                milestone="Sprint 1: Golden Path + System Clarity",
                epic_id="A",
                task_id="A4",
            ),
        ]
    )

    # Sprint 1 - Epic B: System Map & Service Classification
    issues.extend(
        [
            Issue(
                title="Create System Map Documentation",
                body="""Create a comprehensive system map that documents all services, their purposes, owners, and current status.

**Acceptance Criteria:**
- [ ] List all services with purpose and owners
- [ ] Assign statuses: GA, Beta, Experimental
- [ ] Create service dependency diagram
- [ ] Link System Map from README
- [ ] Add service communication patterns

**Epic Context:**
Part of Epic B: System Map & Service Classification - making the repo understandable.
""",
                labels=["epic-b-system-map", "sprint-1", "documentation"],
                milestone="Sprint 1: Golden Path + System Clarity",
                epic_id="B",
                task_id="B1",
            ),
            Issue(
                title="Implement Service Status Classification",
                body="""Add status labels to all services and reorganize the repository structure based on service maturity.

**Acceptance Criteria:**
- [ ] Add #Status to every service README
- [ ] Move abandoned services to /experimental/
- [ ] Update top-level README with status table
- [ ] Create migration guide for moved services
- [ ] Update docker-compose files to reflect structure

**Epic Context:**
Part of Epic B: System Map & Service Classification - clarifying service maturity.
""",
                labels=["epic-b-system-map", "sprint-1", "documentation"],
                milestone="Sprint 1: Golden Path + System Clarity",
                epic_id="B",
                task_id="B2",
            ),
        ]
    )

    # Sprint 2 - Epic C: Jurisdiction Clarity
    issues.extend(
        [
            Issue(
                title="Document Jurisdiction Coverage Status",
                body="""Create comprehensive documentation of regulatory coverage for each jurisdiction (city).

**Acceptance Criteria:**
- [ ] List cities with coverage completeness
- [ ] Document regression test status per city
- [ ] Document issuer API/portal availability
- [ ] Add compliance requirements per city
- [ ] Include last updated dates

**Epic Context:**
Part of Epic C: Jurisdiction Clarity - making regulatory coverage explicit.
""",
                labels=["epic-c-jurisdiction", "sprint-2", "documentation"],
                milestone="Sprint 2: Jurisdiction Clarity + MVP",
                epic_id="C",
                task_id="C1",
            ),
            Issue(
                title="Implement Per-Jurisdiction Regression Tests",
                body="""Create comprehensive regression test suites for LA and SF jurisdictions.

**Acceptance Criteria:**
- [ ] Add LA compliance tests
- [ ] Add SF compliance tests
- [ ] Add fixture directories for each city
- [ ] Create test data for each jurisdiction
- [ ] Add CI pipeline for jurisdiction tests

**Epic Context:**
Part of Epic C: Jurisdiction Clarity - validating regulatory logic per city.
""",
                labels=["epic-c-jurisdiction", "sprint-2", "testing"],
                milestone="Sprint 2: Jurisdiction Clarity + MVP",
                epic_id="C",
                task_id="C2",
            ),
            Issue(
                title="Define and Implement MVP Jurisdiction Scope",
                body="""Clearly define the MVP jurisdiction scope (LA + SF) and adjust infrastructure accordingly.

**Acceptance Criteria:**
- [ ] Define MVP = LA + SF
- [ ] Disable other cities in compose.mvp.yml
- [ ] Cross-link with MVP_SCOPE.md
- [ ] Update documentation to reflect MVP scope
- [ ] Add feature flags for non-MVP jurisdictions

**Epic Context:**
Part of Epic C: Jurisdiction Clarity - focusing on MVP jurisdictions.
""",
                labels=["epic-c-jurisdiction", "sprint-2", "documentation"],
                milestone="Sprint 2: Jurisdiction Clarity + MVP",
                epic_id="C",
                task_id="C3",
            ),
        ]
    )

    # Sprint 2 - Epic D: MVP Definition
    issues.extend(
        [
            Issue(
                title="Document MVP Scope and Boundaries",
                body="""Create clear documentation defining what is included, excluded, and planned for future in the MVP.

**Acceptance Criteria:**
- [ ] Define Included in MVP
- [ ] Define Excluded from MVP
- [ ] Define Future Scope
- [ ] Add roadmap timeline
- [ ] Link to architecture decision records (ADRs)

**Epic Context:**
Part of Epic D: MVP Definition - establishing clear product boundaries.
""",
                labels=["epic-d-mvp", "sprint-2", "documentation"],
                milestone="Sprint 2: Jurisdiction Clarity + MVP",
                epic_id="D",
                task_id="D1",
            ),
            Issue(
                title="Reorganize Repository for MVP Focus",
                body="""Restructure the repository to clearly separate MVP services from experimental/future work.

**Acceptance Criteria:**
- [ ] Move non-MVP services to /experimental/
- [ ] Disable non-MVP services in compose.mvp.yml
- [ ] Add MVP-only CI test
- [ ] Update README with MVP structure
- [ ] Create migration guide

**Epic Context:**
Part of Epic D: MVP Definition - physically organizing code to match MVP scope.
""",
                labels=["epic-d-mvp", "sprint-2", "infrastructure"],
                milestone="Sprint 2: Jurisdiction Clarity + MVP",
                epic_id="D",
                task_id="D2",
            ),
        ]
    )

    # Sprint 3 - Epic E: Data Model & ERD Clarity
    issues.extend(
        [
            Issue(
                title="Create ERD Documentation",
                body="""Generate comprehensive Entity Relationship Diagrams for all core entities in the system.

**Acceptance Criteria:**
- [ ] Create ERD diagrams for core entities
- [ ] Add docs/ERD/ERD.png
- [ ] Document relationships clearly
- [ ] Add entity descriptions
- [ ] Link ERD from main documentation

**Epic Context:**
Part of Epic E: Data Model & ERD Clarity - visualizing data relationships.
""",
                labels=["epic-e-data-model", "sprint-3", "documentation"],
                milestone="Sprint 3: Data Model, Payments, Compliance Engine",
                epic_id="E",
                task_id="E1",
            ),
            Issue(
                title="Document Complete Data Model",
                body="""Create comprehensive documentation of the data model, including entities, relationships, and consistency rules.

**Acceptance Criteria:**
- [ ] Document each core entity
- [ ] Document ID consistency rules
- [ ] Document cross-service entity consumption
- [ ] Add data validation rules
- [ ] Include migration guidelines

**Epic Context:**
Part of Epic E: Data Model & ERD Clarity - documenting data structures.
""",
                labels=["epic-e-data-model", "sprint-3", "documentation"],
                milestone="Sprint 3: Data Model, Payments, Compliance Engine",
                epic_id="E",
                task_id="E2",
            ),
            Issue(
                title="Implement Data Model Consistency Tests",
                body="""Create automated tests to validate data model consistency across services and languages.

**Acceptance Criteria:**
- [ ] Validate Postgres schema matches entity model
- [ ] Add mismatch test between Node and Python services
- [ ] Add migration validation tests
- [ ] Create schema drift detection
- [ ] Add CI integration

**Epic Context:**
Part of Epic E: Data Model & ERD Clarity - ensuring model consistency.
""",
                labels=["epic-e-data-model", "sprint-3", "testing"],
                milestone="Sprint 3: Data Model, Payments, Compliance Engine",
                epic_id="E",
                task_id="E3",
            ),
        ]
    )

    # Sprint 3 - Epic G: Payments Architecture
    issues.extend(
        [
            Issue(
                title="Document Payments Architecture",
                body="""Create comprehensive documentation of the payments architecture, including Stripe Connect integration and fee structures.

**Acceptance Criteria:**
- [ ] Document Stripe Connect workflow
- [ ] Define vendor→connected account mapping
- [ ] Define platform fees and payout logic
- [ ] Add payment flow diagrams
- [ ] Document error handling and retries

**Epic Context:**
Part of Epic G: Payments Architecture - clarifying payment flows.
""",
                labels=["epic-g-payments", "sprint-3", "documentation"],
                milestone="Sprint 3: Data Model, Payments, Compliance Engine",
                epic_id="G",
                task_id="G1",
            ),
            Issue(
                title="Implement Payments and Fees Testing",
                body="""Create comprehensive test suite for payment calculations, fees, and ledger operations.

**Acceptance Criteria:**
- [ ] Add fee calculation tests
- [ ] Add pricing simulation fixtures
- [ ] Validate ledger write logic
- [ ] Test payout scenarios
- [ ] Add integration tests with Stripe

**Epic Context:**
Part of Epic G: Payments Architecture - validating payment logic.
""",
                labels=["epic-g-payments", "sprint-3", "testing"],
                milestone="Sprint 3: Data Model, Payments, Compliance Engine",
                epic_id="G",
                task_id="G2",
            ),
        ]
    )

    # Sprint 3 - Epic H: Compliance Engine Architecture
    issues.extend(
        [
            Issue(
                title="Create Compliance Engine Documentation",
                body="""Document the compliance engine architecture, rule formats, and decision logic.

**Acceptance Criteria:**
- [ ] Create regengine/README.md
- [ ] Document rule formats (YAML or Python DSL)
- [ ] Document decision tree / DAG
- [ ] Add rule authoring guide
- [ ] Include examples for LA and SF

**Epic Context:**
Part of Epic H: Compliance Engine Architecture - documenting regulatory logic.
""",
                labels=["epic-h-compliance", "sprint-3", "documentation"],
                milestone="Sprint 3: Data Model, Payments, Compliance Engine",
                epic_id="H",
                task_id="H1",
            ),
            Issue(
                title="Convert Hard-Coded Rules to Data-Driven Configuration",
                body="""Refactor compliance engine to use data-driven rule configuration instead of hard-coded logic.

**Acceptance Criteria:**
- [ ] Convert hard-coded rules to configs
- [ ] Add common validation interface
- [ ] Create rule DAG visualizations for LA + SF
- [ ] Implement rule versioning
- [ ] Add rule validation tooling

**Epic Context:**
Part of Epic H: Compliance Engine Architecture - making rules maintainable.
""",
                labels=["epic-h-compliance", "sprint-3", "infrastructure"],
                milestone="Sprint 3: Data Model, Payments, Compliance Engine",
                epic_id="H",
                task_id="H2",
            ),
            Issue(
                title="Implement Compliance Engine Test Matrix",
                body="""Create comprehensive test matrix for compliance rules across all jurisdictions.

**Acceptance Criteria:**
- [ ] Build compliance test matrix
- [ ] Add failing→passing rule tests
- [ ] Link tests directly to Golden Path
- [ ] Add edge case coverage
- [ ] Create regression test suite

**Epic Context:**
Part of Epic H: Compliance Engine Architecture - validating regulatory logic.
""",
                labels=["epic-h-compliance", "sprint-3", "testing"],
                milestone="Sprint 3: Data Model, Payments, Compliance Engine",
                epic_id="H",
                task_id="H3",
            ),
        ]
    )

    # Sprint 4 - Epic I: Observability & SLOs
    issues.extend(
        [
            Issue(
                title="Document SLOs for Core Services",
                body="""Define and document Service Level Objectives for all core services.

**Acceptance Criteria:**
- [ ] Create docs/SLO.md
- [ ] Define latency budgets
- [ ] Define error budgets
- [ ] Set availability targets
- [ ] Document measurement methodology

**Epic Context:**
Part of Epic I: Observability & SLOs - establishing reliability standards.
""",
                labels=["epic-i-observability", "sprint-4", "documentation"],
                milestone="Sprint 4: Observability + Cleanup",
                epic_id="I",
                task_id="I1",
            ),
            Issue(
                title="Create Grafana Dashboards for SLOs",
                body="""Implement comprehensive Grafana dashboards to monitor SLOs and service health.

**Acceptance Criteria:**
- [ ] Add Grafana SLO dashboards
- [ ] Add service uptime metrics
- [ ] Create alert templates
- [ ] Implement alert routing
- [ ] Document dashboard usage

**Epic Context:**
Part of Epic I: Observability & SLOs - monitoring service reliability.
""",
                labels=["epic-i-observability", "sprint-4", "infrastructure"],
                milestone="Sprint 4: Observability + Cleanup",
                epic_id="I",
                task_id="I2",
            ),
        ]
    )

    # Sprint 4 - Epic J: Cleanup & Repository Hygiene
    issues.extend(
        [
            Issue(
                title="Clean Up Repository Structure",
                body="""Clean up repository by removing outdated code, organizing prototypes, and establishing ownership.

**Acceptance Criteria:**
- [ ] Move prototypes to /experimental/
- [ ] Delete outdated or duplicate docs
- [ ] Add CODEOWNERS
- [ ] Remove dead code
- [ ] Update .gitignore

**Epic Context:**
Part of Epic J: Cleanup & Repository Hygiene - reducing technical debt.
""",
                labels=["epic-j-cleanup", "sprint-4", "infrastructure"],
                milestone="Sprint 4: Observability + Cleanup",
                epic_id="J",
                task_id="J1",
            ),
            Issue(
                title="Create Consistent Service Documentation",
                body="""Ensure every service has consistent, comprehensive documentation following a standard template.

**Acceptance Criteria:**
- [ ] Add README to every service
- [ ] Link each README to System Map
- [ ] Add semantic version tagging
- [ ] Create documentation template
- [ ] Validate documentation completeness

**Epic Context:**
Part of Epic J: Cleanup & Repository Hygiene - standardizing documentation.
""",
                labels=["epic-j-cleanup", "sprint-4", "documentation"],
                milestone="Sprint 4: Observability + Cleanup",
                epic_id="J",
                task_id="J2",
            ),
        ]
    )

    return issues


def main():
    parser = argparse.ArgumentParser(description="Create GitHub issues from sprint plan")
    parser.add_argument("--repo", required=True, help="GitHub repository (e.g., owner/repo)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be created without creating"
    )
    parser.add_argument("--execute", action="store_true", help="Actually create the issues")
    parser.add_argument("--milestones-only", action="store_true", help="Only create milestones")
    parser.add_argument("--labels-only", action="store_true", help="Only create labels")

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("Error: Must specify either --dry-run or --execute")
        sys.exit(1)

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set")
        sys.exit(1)

    creator = GitHubIssueCreator(args.repo, token)

    print("=== Creating Milestones ===")
    creator.create_milestones()

    if args.milestones_only:
        return

    print("\n=== Creating Labels ===")
    creator.create_labels()

    if args.labels_only:
        return

    issues = get_all_issues()
    creator.create_all_issues(issues, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
