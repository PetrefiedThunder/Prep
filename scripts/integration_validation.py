#!/usr/bin/env python3
"""
Integration Validation Script

Validates that all platform components are properly integrated and functional.

Usage:
    python scripts/integration_validation.py
    python scripts/integration_validation.py --quick
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Test Results
results = {"passed": [], "failed": [], "warnings": []}


def print_header(text: str):
    """Print section header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def test_pass(name: str):
    """Record test pass."""
    results["passed"].append(name)
    print(f"✓ {name}")


def test_fail(name: str, error: str):
    """Record test failure."""
    results["failed"].append({"name": name, "error": error})
    print(f"✗ {name}")
    print(f"  Error: {error}")


def test_warn(name: str, message: str):
    """Record test warning."""
    results["warnings"].append({"name": name, "message": message})
    print(f"⚠ {name}")
    print(f"  Warning: {message}")


def validate_schemas():
    """Validate all JSON schemas are valid."""
    print_header("Validating JSON Schemas")

    schemas_dir = Path("schemas")
    if not schemas_dir.exists():
        test_fail("Schemas directory", "schemas/ directory not found")
        return

    schema_files = list(schemas_dir.glob("*.schema.json"))

    if not schema_files:
        test_fail("Schema files", "No schema files found")
        return

    try:
        import jsonschema

        for schema_file in schema_files:
            try:
                with open(schema_file) as f:
                    schema = json.load(f)

                # Validate schema itself
                jsonschema.Draft202012Validator.check_schema(schema)
                test_pass(f"Schema: {schema_file.name}")

            except json.JSONDecodeError as e:
                test_fail(f"Schema: {schema_file.name}", f"Invalid JSON: {e}")
            except jsonschema.SchemaError as e:
                test_fail(f"Schema: {schema_file.name}", f"Invalid schema: {e}")

    except ImportError:
        test_warn("Schema validation", "jsonschema not installed (pip install jsonschema)")


def validate_regengine_rules():
    """Validate RegEngine rule files."""
    print_header("Validating RegEngine Rules")

    rules_dir = Path("regengine/cities")
    if not rules_dir.exists():
        test_fail("RegEngine", "regengine/cities/ directory not found")
        return

    jurisdictions = [d for d in rules_dir.iterdir() if d.is_dir() and d.name != "__pycache__"]

    if not jurisdictions:
        test_fail("RegEngine", "No jurisdictions found")
        return

    try:
        import yaml

        for jurisdiction in jurisdictions:
            rules_file = jurisdiction / "rules.yaml"
            config_file = jurisdiction / "config.yaml"

            # Check rules.yaml
            if rules_file.exists():
                try:
                    with open(rules_file) as f:
                        rules = yaml.safe_load(f)

                    if "rules" not in rules:
                        test_fail(f"Rules: {jurisdiction.name}", "No 'rules' key found")
                    else:
                        rule_count = len(rules["rules"])
                        test_pass(f"Rules: {jurisdiction.name} ({rule_count} rules)")

                except yaml.YAMLError as e:
                    test_fail(f"Rules: {jurisdiction.name}", f"Invalid YAML: {e}")
            else:
                test_warn(f"Rules: {jurisdiction.name}", "No rules.yaml file (config.yaml only)")

            # Check config.yaml
            if config_file.exists():
                try:
                    with open(config_file) as f:
                        config = yaml.safe_load(f)
                    test_pass(f"Config: {jurisdiction.name}")
                except yaml.YAMLError as e:
                    test_fail(f"Config: {jurisdiction.name}", f"Invalid YAML: {e}")
            else:
                test_fail(f"Config: {jurisdiction.name}", "No config.yaml file")

    except ImportError:
        test_fail("RegEngine validation", "pyyaml not installed (pip install pyyaml)")


def validate_documentation():
    """Validate documentation files exist."""
    print_header("Validating Documentation")

    required_docs = [
        "docs/PRODUCT_SPINE.md",
        "docs/API_VERSIONING_POLICY.md",
        "docs/PAYMENTS_ARCHITECTURE.md",
        "docs/SLO.md",
        "docs/OPS_HANDBOOK.md",
        "docs/GOLDEN_PATH_DEMO.md",
        "docs/architecture.md",
        "regengine/README.md",
        "OVERNIGHT_UPGRADE_SUMMARY.md",
    ]

    for doc in required_docs:
        doc_path = Path(doc)
        if doc_path.exists():
            # Check file size (should be > 1KB)
            size = doc_path.stat().st_size
            if size > 1024:
                test_pass(f"Documentation: {doc}")
            else:
                test_warn(f"Documentation: {doc}", f"File is small ({size} bytes)")
        else:
            test_fail(f"Documentation: {doc}", "File not found")


def validate_mock_services():
    """Validate mock service files exist and are executable."""
    print_header("Validating Mock Services")

    mock_files = [
        "mocks/stripe_mock.py",
        "mocks/gov_portals_mock.py",
        "docker-compose.mock.yml",
        "Dockerfile.mock-stripe",
    ]

    for mock_file in mock_files:
        mock_path = Path(mock_file)
        if mock_path.exists():
            test_pass(f"Mock service: {mock_file}")
        else:
            test_fail(f"Mock service: {mock_file}", "File not found")

    # Check if mock services are Python-runnable
    stripe_mock = Path("mocks/stripe_mock.py")
    if stripe_mock.exists():
        content = stripe_mock.read_text()
        if 'if __name__ == "__main__"' in content:
            test_pass("Mock Stripe: Runnable")
        else:
            test_warn("Mock Stripe", "Not directly runnable")


def validate_cli_tool():
    """Validate prepctl CLI tool."""
    print_header("Validating CLI Tool")

    cli_file = Path("prep/cli.py")
    if cli_file.exists():
        content = cli_file.read_text()

        # Check for key commands
        commands = ["dev", "vendor:onboard", "compliance:check", "db:migrate"]
        for cmd in commands:
            if cmd.replace(":", "_") in content or cmd in content:
                test_pass(f"CLI command: {cmd}")
            else:
                test_fail(f"CLI command: {cmd}", "Command not found in CLI")

    else:
        test_fail("CLI tool", "prep/cli.py not found")

    # Check wrapper script
    wrapper = Path("prep_dev.sh")
    if wrapper.exists():
        test_pass("CLI wrapper: prep_dev.sh")
    else:
        test_warn("CLI wrapper", "prep_dev.sh not found")


def validate_api_decorators():
    """Validate API decorator implementations."""
    print_header("Validating API Decorators")

    decorators_file = Path("prep/api/decorators.py")
    if decorators_file.exists():
        content = decorators_file.read_text()

        decorators = ["public_api", "internal_service_api", "experimental_api"]
        for decorator in decorators:
            if f"def {decorator}" in content:
                test_pass(f"API decorator: @{decorator}")
            else:
                test_fail(f"API decorator: @{decorator}", "Decorator not found")

    else:
        test_fail("API decorators", "prep/api/decorators.py not found")


def validate_audit_logging():
    """Validate audit logging system."""
    print_header("Validating Audit Logging")

    audit_file = Path("prep/audit/audit_logger.py")
    if audit_file.exists():
        content = audit_file.read_text()

        # Check key classes
        classes = ["AuditLog", "AuditLogger", "AuditAction", "AuditEntity"]
        for cls in classes:
            if f"class {cls}" in content:
                test_pass(f"Audit class: {cls}")
            else:
                test_fail(f"Audit class: {cls}", "Class not found")

    else:
        test_fail("Audit logging", "prep/audit/audit_logger.py not found")


def validate_middleware():
    """Validate middleware implementations."""
    print_header("Validating Middleware")

    middleware_file = Path("prep/api/middleware/schema_validation.py")
    if middleware_file.exists():
        content = middleware_file.read_text()

        functions = ["load_schema", "validate_against_schema", "validate_vendor", "validate_facility"]
        for func in functions:
            if f"def {func}" in content:
                test_pass(f"Middleware function: {func}")
            else:
                test_fail(f"Middleware function: {func}", "Function not found")

    else:
        test_fail("Schema validation middleware", "File not found")


def validate_test_suite():
    """Validate test files exist."""
    print_header("Validating Test Suite")

    test_files = [
        "tests/scenarios/test_golden_path.py",
    ]

    for test_file in test_files:
        test_path = Path(test_file)
        if test_path.exists():
            test_pass(f"Test file: {test_file}")
        else:
            test_fail(f"Test file: {test_file}", "File not found")


def validate_docker_compose():
    """Validate Docker Compose configuration."""
    print_header("Validating Docker Compose")

    compose_files = ["docker-compose.yml", "docker-compose.mock.yml"]

    try:
        import yaml

        for compose_file in compose_files:
            compose_path = Path(compose_file)
            if compose_path.exists():
                try:
                    with open(compose_path) as f:
                        compose = yaml.safe_load(f)

                    if "services" in compose:
                        service_count = len(compose["services"])
                        test_pass(f"Compose: {compose_file} ({service_count} services)")
                    else:
                        test_fail(f"Compose: {compose_file}", "No services defined")

                except yaml.YAMLError as e:
                    test_fail(f"Compose: {compose_file}", f"Invalid YAML: {e}")
            else:
                test_fail(f"Compose: {compose_file}", "File not found")

    except ImportError:
        test_warn("Docker Compose validation", "pyyaml not installed")


def print_summary():
    """Print test summary."""
    print_header("Validation Summary")

    total = len(results["passed"]) + len(results["failed"]) + len(results["warnings"])

    print(f"Total tests run: {total}")
    print(f"  ✓ Passed:   {len(results['passed'])}")
    print(f"  ✗ Failed:   {len(results['failed'])}")
    print(f"  ⚠ Warnings: {len(results['warnings'])}")

    if results["failed"]:
        print("\nFailed tests:")
        for failure in results["failed"]:
            print(f"  - {failure['name']}: {failure['error']}")

    if results["warnings"]:
        print("\nWarnings:")
        for warning in results["warnings"]:
            print(f"  - {warning['name']}: {warning['message']}")

    return len(results["failed"]) == 0


def main():
    parser = argparse.ArgumentParser(description="Validate Prep platform integration")
    parser.add_argument("--quick", action="store_true", help="Run quick validation (skip some checks)")
    args = parser.parse_args()

    print("🔍 Prep Platform Integration Validation")
    print("=" * 60)

    # Core validations (always run)
    validate_schemas()
    validate_regengine_rules()
    validate_documentation()
    validate_api_decorators()
    validate_audit_logging()

    if not args.quick:
        # Extended validations
        validate_mock_services()
        validate_cli_tool()
        validate_middleware()
        validate_test_suite()
        validate_docker_compose()

    # Print summary
    success = print_summary()

    if success:
        print("\n✅ Integration validation PASSED")
        sys.exit(0)
    else:
        print("\n❌ Integration validation FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
