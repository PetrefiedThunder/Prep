#!/usr/bin/env python3
"""
Release Notes Generator (U59)
Compiles merged PRs into formatted release notes using PR titles and labels
Usage: python scripts/generate_release_notes.py <from_tag> <to_tag>
"""

import re
import subprocess
import sys
from collections import defaultdict


def get_merged_prs(from_tag: str, to_tag: str):
    """Get list of merged PRs between two tags"""
    # Get commit messages between tags
    cmd = ["git", "log", f"{from_tag}..{to_tag}", "--merges", "--oneline", "--pretty=format:%s"]

    result = subprocess.run(cmd, capture_output=True, text=True)

    prs = []
    for line in result.stdout.split("\n"):
        # Extract PR number from "Merge pull request #123"
        match = re.search(r"#(\d+)", line)
        if match:
            pr_num = match.group(1)
            # Get PR title (simplified - in real implementation, use GitHub API)
            prs.append(
                {
                    "number": pr_num,
                    "title": line.replace(f"Merge pull request #{pr_num}", "").strip(),
                    "labels": [],  # Would fetch from GitHub API
                }
            )

    return prs


def categorize_prs(prs):
    """Categorize PRs by type"""
    categories = defaultdict(list)

    for pr in prs:
        title = pr["title"].lower()

        if any(word in title for word in ["feat:", "feature"]):
            categories["Features"].append(pr)
        elif any(word in title for word in ["fix:", "bug"]):
            categories["Bug Fixes"].append(pr)
        elif any(word in title for word in ["docs:", "documentation"]):
            categories["Documentation"].append(pr)
        elif any(word in title for word in ["perf:", "performance"]):
            categories["Performance"].append(pr)
        elif any(word in title for word in ["security", "sec:"]):
            categories["Security"].append(pr)
        elif any(word in title for word in ["refactor:", "refactoring"]):
            categories["Refactoring"].append(pr)
        else:
            categories["Other"].append(pr)

    return categories


def generate_release_notes(from_tag: str, to_tag: str):
    """Generate formatted release notes"""

    print(f"Generating release notes from {from_tag} to {to_tag}...")

    prs = get_merged_prs(from_tag, to_tag)
    categories = categorize_prs(prs)

    # Generate markdown
    notes = []
    notes.append(f"# Release Notes: {to_tag}")
    notes.append("")
    notes.append(f"**Changes since {from_tag}**")
    notes.append("")

    for category, pr_list in sorted(categories.items()):
        if not pr_list:
            continue

        notes.append(f"## {category}")
        notes.append("")

        for pr in pr_list:
            # Clean up title
            title = pr["title"].replace("from", "").strip()
            title = re.sub(
                r"^(feat|fix|docs|perf|refactor|security):\s*", "", title, flags=re.IGNORECASE
            )
            notes.append(f"- {title} (#{pr['number']})")

        notes.append("")

    # Add footer
    notes.append("---")
    notes.append("")
    notes.append(
        f"**Full Changelog**: https://github.com/PetrefiedThunder/Prep/compare/{from_tag}...{to_tag}"
    )

    return "\n".join(notes)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_release_notes.py <from_tag> <to_tag>")
        print("Example: python generate_release_notes.py v1.0.0 v1.1.0")
        sys.exit(1)

    from_tag = sys.argv[1]
    to_tag = sys.argv[2]

    notes = generate_release_notes(from_tag, to_tag)

    # Write to file
    output_file = f"RELEASE_NOTES_{to_tag}.md"
    with open(output_file, "w") as f:
        f.write(notes)

    print(f"\n✓ Release notes generated: {output_file}")
    print("\nPreview:")
    print("=" * 60)
    print(notes)
