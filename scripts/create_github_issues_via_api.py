#!/usr/bin/env python3
"""
Create GitHub issues via API from the identified codebase issues.

Usage:
    export GITHUB_TOKEN="your_token_here"
    python scripts/create_github_issues_via_api.py
    
    # Or specify token as argument
    python scripts/create_github_issues_via_api.py your_token_here
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, List
import requests


REPO_OWNER = "PetrefiedThunder"
REPO_NAME = "Prep"
ISSUES_FILE = "IDENTIFIED_ISSUES.json"


def load_issues() -> List[Dict]:
    """Load issues from JSON file."""
    issues_path = Path(ISSUES_FILE)
    if not issues_path.exists():
        print(f"❌ Error: {ISSUES_FILE} not found")
        print("Please run: python scripts/create_codebase_issues.py --dry-run")
        sys.exit(1)
    
    with open(issues_path) as f:
        data = json.load(f)
    
    return data["issues"]


def create_github_issue(
    token: str,
    title: str,
    body: str,
    labels: List[str],
    priority: str
) -> Dict:
    """Create a GitHub issue via API."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    # Add priority to body
    body_with_priority = f"**Priority:** {priority}\n\n{body}"
    
    payload = {
        "title": title,
        "body": body_with_priority,
        "labels": labels
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Failed to create issue: {response.status_code} - {response.text}")


def main():
    """Main entry point."""
    print("=" * 80)
    print("GITHUB ISSUE CREATOR (API)")
    print("=" * 80)
    print()
    
    # Get GitHub token
    token = None
    if len(sys.argv) > 1:
        token = sys.argv[1]
    else:
        token = os.environ.get("GITHUB_TOKEN")
    
    if not token:
        print("❌ Error: GitHub token not provided")
        print()
        print("Usage:")
        print("  export GITHUB_TOKEN='your_token_here'")
        print("  python scripts/create_github_issues_via_api.py")
        print()
        print("Or:")
        print("  python scripts/create_github_issues_via_api.py your_token_here")
        sys.exit(1)
    
    # Load issues
    issues = load_issues()
    print(f"📝 Found {len(issues)} issues to create")
    print(f"📍 Repository: {REPO_OWNER}/{REPO_NAME}")
    print()
    
    # Confirm
    response = input(f"Create {len(issues)} issues? (y/N): ")
    if response.lower() != 'y':
        print("❌ Aborted")
        sys.exit(0)
    
    print()
    print("Creating issues...")
    print()
    
    created = []
    failed = []
    
    for i, issue in enumerate(issues, 1):
        title = issue["title"]
        body = issue["body"]
        labels = issue["labels"]
        priority = issue["priority"]
        
        print(f"[{i}/{len(issues)}] Creating: {title}")
        
        try:
            result = create_github_issue(token, title, body, labels, priority)
            issue_url = result["html_url"]
            issue_number = result["number"]
            print(f"  ✅ Created: #{issue_number} - {issue_url}")
            created.append(issue_number)
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            failed.append(title)
        
        print()
    
    print("=" * 80)
    print("Summary:")
    print(f"  Created: {len(created)}")
    print(f"  Failed: {len(failed)}")
    print(f"  Total: {len(issues)}")
    print("=" * 80)
    
    if created:
        print()
        print("Created issues:")
        for num in created:
            print(f"  - Issue #{num}: https://github.com/{REPO_OWNER}/{REPO_NAME}/issues/{num}")
    
    if failed:
        print()
        print("Failed issues:")
        for title in failed:
            print(f"  - {title}")
        sys.exit(1)
    
    print()
    print(f"✅ All issues created successfully!")
    print(f"View: https://github.com/{REPO_OWNER}/{REPO_NAME}/issues")


if __name__ == "__main__":
    main()
