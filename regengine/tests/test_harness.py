#!/usr/bin/env python3
"""
RIC (Regulatory Intelligence Core) Test Harness

This harness validates that the regengine compliance kernel produces
correct, reproducible outputs by comparing against golden files.

Usage:
    python regengine/tests/test_harness.py

Exit codes:
    0 - All tests passed
    1 - Test failures detected
    2 - Missing golden files or configuration errors
"""

import json
import os
import sys
from difflib import unified_diff
from pathlib import Path
from typing import Any

# Import the compliance kernel
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from regengine.cities.compliance_kernel import MunicipalComplianceKernel


class Colors:
    """ANSI color codes for terminal output"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class TestHarness:
    """Test harness for RIC compliance engine"""

    def __init__(self, golden_dir: str = None):
        self.golden_dir = golden_dir or os.path.join(
            os.path.dirname(__file__), "..", "cities", "golden"
        )
        self.failures: list[dict[str, Any]] = []
        self.passes: list[str] = []

    def load_golden_file(self, filename: str) -> dict[str, Any]:
        """Load a golden test file"""
        filepath = os.path.join(self.golden_dir, filename)

        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Golden file not found: {filepath}\nExpected location: {os.path.abspath(filepath)}"
            )

        with open(filepath) as f:
            return json.load(f)

    def normalize_evaluation(self, evaluation: dict[str, Any]) -> dict[str, Any]:
        """Normalize evaluation for comparison (remove timestamps)"""
        normalized = evaluation.copy()
        # Remove dynamic fields that change between runs
        normalized.pop("evaluated_at", None)
        return normalized

    def compare_evaluations(
        self, expected: dict[str, Any], actual: dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Compare expected vs actual evaluation results.

        Returns:
            (matches: bool, diff_message: str)
        """
        # Normalize both for comparison
        norm_expected = self.normalize_evaluation(expected)
        norm_actual = self.normalize_evaluation(actual)

        # Pretty print for comparison
        expected_str = json.dumps(norm_expected, indent=2, sort_keys=True)
        actual_str = json.dumps(norm_actual, indent=2, sort_keys=True)

        if expected_str == actual_str:
            return True, ""

        # Generate diff
        diff = unified_diff(
            expected_str.splitlines(keepends=True),
            actual_str.splitlines(keepends=True),
            fromfile="expected",
            tofile="actual",
            lineterm="",
        )
        diff_str = "".join(diff)

        return False, diff_str

    def run_test_case(self, golden_file: str) -> bool:
        """
        Run a single test case from a golden file.

        Returns:
            True if test passed, False otherwise
        """
        print(f"\n{Colors.BLUE}Testing: {golden_file}{Colors.RESET}")

        try:
            golden_data = self.load_golden_file(golden_file)
        except FileNotFoundError as e:
            print(f"{Colors.RED}ERROR: {e}{Colors.RESET}")
            self.failures.append({"test": golden_file, "error": str(e)})
            return False
        except json.JSONDecodeError as e:
            print(f"{Colors.RED}ERROR: Invalid JSON in {golden_file}: {e}{Colors.RESET}")
            self.failures.append({"test": golden_file, "error": f"Invalid JSON: {e}"})
            return False

        # Extract test components
        jurisdiction_id = golden_data.get("jurisdiction_id")
        kitchen_data = golden_data.get("kitchen_data", {})
        maker_data = golden_data.get("maker_data", {})
        booking_data = golden_data.get("booking_data", {})
        expected_result = golden_data.get("expected_result", {})

        if not jurisdiction_id:
            print(f"{Colors.RED}ERROR: No jurisdiction_id in {golden_file}{Colors.RESET}")
            self.failures.append({"test": golden_file, "error": "Missing jurisdiction_id"})
            return False

        # Run the compliance kernel
        try:
            kernel = MunicipalComplianceKernel(jurisdiction_id)
            evaluation = kernel.evaluate_booking(
                kitchen_data=kitchen_data, maker_data=maker_data, booking_data=booking_data
            )
            actual_result = evaluation.to_dict()
        except Exception as e:
            print(f"{Colors.RED}ERROR: Kernel execution failed: {e}{Colors.RESET}")
            self.failures.append({"test": golden_file, "error": f"Kernel error: {e}"})
            return False

        # Compare results
        matches, diff = self.compare_evaluations(expected_result, actual_result)

        if matches:
            print(f"{Colors.GREEN}✓ PASS{Colors.RESET}")
            self.passes.append(golden_file)
            return True
        else:
            print(f"{Colors.RED}✗ FAIL{Colors.RESET}")
            print(f"\n{Colors.YELLOW}Diff:{Colors.RESET}")
            print(diff)
            self.failures.append({"test": golden_file, "diff": diff})
            return False

    def discover_golden_files(self) -> list[str]:
        """Discover all golden test files"""
        if not os.path.exists(self.golden_dir):
            return []

        return sorted([f for f in os.listdir(self.golden_dir) if f.endswith(".json")])

    def run_all_tests(self) -> int:
        """
        Run all golden file tests.

        Returns:
            Exit code (0 = success, 1 = failures, 2 = error)
        """
        print(f"{Colors.BOLD}=== RIC Test Harness ==={Colors.RESET}")
        print(f"Golden directory: {os.path.abspath(self.golden_dir)}\n")

        golden_files = self.discover_golden_files()

        if not golden_files:
            print(f"{Colors.RED}ERROR: No golden files found in {self.golden_dir}{Colors.RESET}")
            print("Expected JSON files with test cases.")
            return 2

        print(f"Found {len(golden_files)} test case(s)\n")

        # Run all tests
        for golden_file in golden_files:
            self.run_test_case(golden_file)

        # Print summary
        print(f"\n{Colors.BOLD}=== Test Summary ==={Colors.RESET}")
        print(f"{Colors.GREEN}Passed: {len(self.passes)}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {len(self.failures)}{Colors.RESET}")

        if self.failures:
            print(f"\n{Colors.RED}Failed tests:{Colors.RESET}")
            for failure in self.failures:
                print(f"  - {failure['test']}")
            return 1

        print(f"\n{Colors.GREEN}{Colors.BOLD}All tests passed!{Colors.RESET}")
        return 0


def main():
    """Main entry point"""
    harness = TestHarness()
    exit_code = harness.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
