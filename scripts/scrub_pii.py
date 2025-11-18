#!/usr/bin/env python3
"""
PII Minimization Script (H27)
Anonymizes user records in staging database dumps
Usage: python scripts/scrub_pii.py <input.sql> <output.sql>
"""

import hashlib
import re
import sys
from pathlib import Path


def hash_value(value: str) -> str:
    """Hash a value with SHA256"""
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def scrub_pii(input_file: str, output_file: str):
    """Anonymize PII in SQL dump"""

    print(f"Reading from {input_file}...")
    with open(input_file) as f:
        content = f.read()

    # Track progress

    # Anonymize email addresses
    content = re.sub(
        r"'[\w\.-]+@[\w\.-]+\.\w+'", lambda m: f"'user{hash_value(m.group())}@example.com'", content
    )

    # Anonymize names (assumes single-quoted strings in name fields)
    content = re.sub(
        r"(first_name|last_name|name)\s*=\s*'([^']+)'",
        lambda m: f"{m.group(1)} = 'ANON_{hash_value(m.group(2))}'",
        content,
    )

    # Anonymize phone numbers
    content = re.sub(
        r"(phone|mobile)\s*=\s*'([^']+)'",
        lambda m: f"{m.group(1)} = '555-{hash_value(m.group(2))[:8]}'",
        content,
    )

    # Anonymize addresses
    content = re.sub(
        r"(address|street)\s*=\s*'([^']+)'",
        lambda m: f"{m.group(1)} = '{hash_value(m.group(2))} Main St'",
        content,
    )

    # Anonymize SSN/tax IDs
    content = re.sub(
        r"(ssn|tax_id)\s*=\s*'([^']+)'",
        lambda m: f"{m.group(1)} = 'XXX-XX-{hash_value(m.group(2))[:4]}'",
        content,
    )

    print(f"Writing to {output_file}...")
    with open(output_file, "w") as f:
        f.write(content)

    print("✓ PII scrubbing complete!")
    print(f"  Input: {Path(input_file).stat().st_size} bytes")
    print(f"  Output: {Path(output_file).stat().st_size} bytes")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scrub_pii.py <input.sql> <output.sql>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not Path(input_file).exists():
        print(f"Error: Input file {input_file} not found")
        sys.exit(1)

    scrub_pii(input_file, output_file)
