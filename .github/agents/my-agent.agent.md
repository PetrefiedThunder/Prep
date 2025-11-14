name: Code Hygiene Agent for Prep
description: >
  Reviews and remediates code inconsistencies across the Prep repository, ensuring style compliance,
  removal of redundant logic, and automated formatting corrections in Python and JavaScript files.

---

# My Agent

This agent performs a comprehensive code cleanup pass across the entire Prep repository. Specifically, it will:

- Enforce **PEP 8** compliance across all Python files.
- Enforce **ESLint** rules for all JavaScript files.
- Identify and remove:
  - Unused imports
  - Unused or redundant functions
  - Dead code blocks
  - Inconsistent variable naming
  - Any unreferenced constants or configuration keys
- Normalize formatting using `black` for Python and `prettier` or `eslint --fix` for JS where applicable.
- Automatically create a **detailed summary report** of all detected inconsistencies and applied fixes.
- Submit all changes as a **single pull request**, including:
  - Full commit diff with changelog
  - A markdown summary of modifications by file and issue type
  - CI green check confirmation before merge

All changes must be completed and production-ready by **end of day today**.
