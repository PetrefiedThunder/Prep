"""Specialized monitoring agent implementations.

This module contains agent implementations for security, code quality,
testing, documentation, and compliance monitoring.

Production-ready implementations that integrate with real security and
code quality tools: gitleaks, bandit, safety, ruff, mypy, etc.
"""

import asyncio
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.agent import Agent


@dataclass
class ToolResult:
    """Result from running an external tool."""

    success: bool
    output: str
    issues_found: int = 0
    details: dict[str, Any] | None = None


async def run_command(
    cmd: list[str], cwd: Path | None = None, timeout: int = 300
) -> ToolResult:
    """Run an external command asynchronously and capture output."""
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )

        output = stdout.decode() + stderr.decode()
        success = process.returncode == 0

        return ToolResult(success=success, output=output)
    except asyncio.TimeoutError:
        return ToolResult(success=False, output=f"Command timed out after {timeout}s")
    except FileNotFoundError:
        return ToolResult(success=False, output=f"Command not found: {cmd[0]}")
    except Exception as e:
        return ToolResult(success=False, output=f"Error running command: {e}")


class SecurityMonitorAgent(Agent):
    """Agent for monitoring security aspects of the repository.

    Integrates with:
    - gitleaks: Secret detection in git history
    - bandit: Python security linter
    - safety: Python dependency vulnerability scanner
    """

    async def execute(self) -> None:
        """Execute security monitoring tasks."""
        self.logger.info(f"Security agent {self.config.name} checking repository")

        # Check for potential security issues using real tools
        await self._check_secrets()
        await self._check_dependencies()
        await self._check_python_security()
        await self._check_permissions()

    async def _check_secrets(self) -> None:
        """Check for exposed secrets using gitleaks."""
        repo_root = Path.cwd()

        # Check if gitleaks is available
        if not shutil.which("gitleaks"):
            self.logger.warning(
                "gitleaks not installed - skipping secret scan. Install with: brew install gitleaks"
            )
            return

        self.logger.info("Running gitleaks secret scan...")

        # Run gitleaks with JSON output for parsing
        result = await run_command(
            [
                "gitleaks",
                "detect",
                "--source",
                str(repo_root),
                "--no-git",
                "-f",
                "json",
                "--exit-code",
                "0",
            ],
            cwd=repo_root,
            timeout=600,
        )

        if not result.success:
            self.logger.error(f"gitleaks scan failed: {result.output}")
            return

        # Parse results
        try:
            if result.output.strip():
                findings = (
                    json.loads(result.output)
                    if result.output.strip().startswith("[")
                    else []
                )
                if findings:
                    self.logger.warning(
                        f"gitleaks found {len(findings)} potential secrets!"
                    )
                    for finding in findings[:5]:  # Log first 5
                        self.logger.warning(
                            f"  Secret in {finding.get('File', 'unknown')}: "
                            f"{finding.get('Description', 'unknown type')}"
                        )
                else:
                    self.logger.info("gitleaks scan complete - no secrets found")
            else:
                self.logger.info("gitleaks scan complete - no secrets found")
        except json.JSONDecodeError:
            self.logger.debug(f"gitleaks output: {result.output[:500]}")

    async def _check_dependencies(self) -> None:
        """Check for vulnerable dependencies using safety."""
        repo_root = Path.cwd()
        requirements_file = repo_root / "requirements.txt"

        if not requirements_file.exists():
            self.logger.debug("No requirements.txt found - skipping dependency check")
            return

        # Check if safety is available
        if not shutil.which("safety"):
            self.logger.warning(
                "safety not installed - skipping dependency vulnerability scan. Install with: pip install safety"
            )
            return

        self.logger.info("Running safety dependency vulnerability scan...")

        result = await run_command(
            ["safety", "check", "-r", str(requirements_file), "--json"],
            cwd=repo_root,
            timeout=120,
        )

        # Safety exits with code 64 when vulnerabilities found
        try:
            if result.output.strip():
                data = json.loads(result.output)
                vulns = (
                    data.get("vulnerabilities", []) if isinstance(data, dict) else data
                )
                if vulns:
                    self.logger.warning(
                        f"safety found {len(vulns)} vulnerable dependencies!"
                    )
                    for vuln in vulns[:5]:
                        if isinstance(vuln, dict):
                            self.logger.warning(
                                f"  {vuln.get('package_name', 'unknown')}: {vuln.get('vulnerability_id', 'unknown')}"
                            )
                else:
                    self.logger.info(
                        "safety scan complete - no vulnerable dependencies found"
                    )
        except json.JSONDecodeError:
            if "No known security vulnerabilities" in result.output:
                self.logger.info(
                    "safety scan complete - no vulnerable dependencies found"
                )
            else:
                self.logger.debug(f"safety output: {result.output[:500]}")

    async def _check_python_security(self) -> None:
        """Check Python code security using bandit."""
        repo_root = Path.cwd()

        # Check if bandit is available
        if not shutil.which("bandit"):
            self.logger.warning(
                "bandit not installed - skipping Python security scan. Install with: pip install bandit"
            )
            return

        self.logger.info("Running bandit Python security scan...")

        # Run bandit on Python source directories
        result = await run_command(
            ["bandit", "-r", "prep", "agents", "-f", "json", "-q"],
            cwd=repo_root,
            timeout=300,
        )

        try:
            if result.output.strip():
                data = json.loads(result.output)
                results = data.get("results", [])

                high_severity = sum(
                    1 for r in results if r.get("issue_severity") == "HIGH"
                )
                medium_severity = sum(
                    1 for r in results if r.get("issue_severity") == "MEDIUM"
                )

                if high_severity > 0:
                    self.logger.error(
                        f"bandit found {high_severity} HIGH severity issues!"
                    )
                if medium_severity > 0:
                    self.logger.warning(
                        f"bandit found {medium_severity} MEDIUM severity issues"
                    )

                for issue in [r for r in results if r.get("issue_severity") == "HIGH"][
                    :3
                ]:
                    self.logger.error(
                        f"  {issue.get('filename', 'unknown')}:{issue.get('line_number', '?')}: "
                        f"{issue.get('issue_text', 'unknown issue')}"
                    )

                if not results:
                    self.logger.info("bandit scan complete - no security issues found")
        except json.JSONDecodeError:
            self.logger.debug(f"bandit output: {result.output[:500]}")

    async def _check_permissions(self) -> None:
        """Check file permissions for sensitive files."""
        repo_root = Path.cwd()

        sensitive_patterns = [".env", "*.pem", "*.key", "*secret*", "*credential*"]
        issues_found = 0

        for pattern in sensitive_patterns:
            for file_path in repo_root.glob(f"**/{pattern}"):
                if file_path.is_file():
                    # Check if file is world-readable (on Unix systems)
                    try:
                        mode = file_path.stat().st_mode
                        if mode & 0o004:  # World readable
                            self.logger.warning(
                                f"Sensitive file is world-readable: {file_path}"
                            )
                            issues_found += 1
                    except OSError:
                        pass

        if issues_found == 0:
            self.logger.debug("File permission check complete - no issues found")


class CodeQualityAgent(Agent):
    """Agent for monitoring code quality.

    Integrates with:
    - ruff: Fast Python linter
    - mypy: Static type checker
    """

    async def execute(self) -> None:
        """Execute code quality monitoring tasks."""
        self.logger.info(f"Code quality agent {self.config.name} analyzing code")

        await self._check_linting()
        await self._check_typing()

    async def _check_linting(self) -> None:
        """Check code linting status using ruff."""
        repo_root = Path.cwd()

        if not shutil.which("ruff"):
            self.logger.warning(
                "ruff not installed - skipping lint check. Install with: pip install ruff"
            )
            return

        self.logger.info("Running ruff linter...")

        result = await run_command(
            ["ruff", "check", "prep", "agents", "--output-format", "json"],
            cwd=repo_root,
            timeout=120,
        )

        try:
            if result.output.strip():
                issues = json.loads(result.output)
                if issues:
                    error_count = sum(
                        1 for i in issues if i.get("code", "").startswith("E")
                    )
                    warning_count = len(issues) - error_count

                    if error_count > 0:
                        self.logger.warning(
                            f"ruff found {error_count} errors, {warning_count} warnings"
                        )
                        for issue in issues[:5]:
                            self.logger.debug(
                                f"  {issue.get('filename', '?')}:{issue.get('location', {}).get('row', '?')}: "
                                f"{issue.get('code', '?')} {issue.get('message', '')}"
                            )
                    else:
                        self.logger.info(
                            f"ruff found {warning_count} warnings (no errors)"
                        )
                else:
                    self.logger.info("ruff check complete - no issues found")
        except json.JSONDecodeError:
            # ruff outputs nothing when no issues found
            self.logger.info("ruff check complete - no issues found")

    async def _check_typing(self) -> None:
        """Check type annotations using mypy."""
        repo_root = Path.cwd()

        if not shutil.which("mypy"):
            self.logger.warning(
                "mypy not installed - skipping type check. Install with: pip install mypy"
            )
            return

        self.logger.info("Running mypy type checker...")

        result = await run_command(
            [
                "mypy",
                "prep",
                "agents",
                "--ignore-missing-imports",
                "--no-error-summary",
            ],
            cwd=repo_root,
            timeout=300,
        )

        if result.output.strip():
            lines = result.output.strip().split("\n")
            error_lines = [l for l in lines if ": error:" in l]

            if error_lines:
                self.logger.warning(f"mypy found {len(error_lines)} type errors")
                for line in error_lines[:5]:
                    self.logger.debug(f"  {line}")
            else:
                self.logger.info("mypy check complete - no type errors")
        else:
            self.logger.info("mypy check complete - no type errors")


class TestingAgent(Agent):
    """Agent for monitoring testing coverage and status.

    Integrates with:
    - pytest: Test runner with coverage support
    - coverage.py: Code coverage measurement
    """

    async def execute(self) -> None:
        """Execute testing monitoring tasks."""
        self.logger.info(f"Testing agent {self.config.name} checking tests")

        await self._check_test_coverage()
        await self._check_test_status()

    async def _check_test_coverage(self) -> None:
        """Check test coverage metrics from coverage reports."""
        repo_root = Path.cwd()
        coverage_file = repo_root / ".coverage"
        coverage_json = repo_root / "coverage.json"

        # Check for existing coverage data
        if coverage_json.exists():
            try:
                with open(coverage_json) as f:
                    data = json.load(f)
                    totals = data.get("totals", {})
                    percent = totals.get("percent_covered", 0)

                    if percent < 70:
                        self.logger.warning(f"Test coverage is low: {percent:.1f}%")
                    elif percent < 85:
                        self.logger.info(f"Test coverage: {percent:.1f}% (target: 85%)")
                    else:
                        self.logger.info(f"Test coverage is good: {percent:.1f}%")
                    return
            except (json.JSONDecodeError, KeyError):
                pass

        # If no coverage report, try to generate one
        if coverage_file.exists() and shutil.which("coverage"):
            result = await run_command(
                ["coverage", "report", "--format=total"],
                cwd=repo_root,
                timeout=60,
            )
            if result.success and result.output.strip():
                try:
                    percent = float(result.output.strip())
                    if percent < 70:
                        self.logger.warning(f"Test coverage is low: {percent:.1f}%")
                    else:
                        self.logger.info(f"Test coverage: {percent:.1f}%")
                except ValueError:
                    self.logger.debug("Could not parse coverage output")
        else:
            self.logger.debug(
                "No coverage data available - run pytest with --cov to generate"
            )

    async def _check_test_status(self) -> None:
        """Check for test failures by running a quick smoke test."""
        repo_root = Path.cwd()

        if not shutil.which("pytest"):
            self.logger.warning("pytest not installed - skipping test status check")
            return

        # Run only smoke tests for quick feedback
        smoke_tests = repo_root / "tests" / "smoke"
        if smoke_tests.exists():
            self.logger.info("Running smoke tests...")
            result = await run_command(
                ["pytest", str(smoke_tests), "-q", "--tb=no", "-x"],
                cwd=repo_root,
                timeout=120,
            )

            if result.success:
                self.logger.info("Smoke tests passed")
            else:
                self.logger.error(f"Smoke tests failed: {result.output[-500:]}")
        else:
            self.logger.debug("No smoke tests directory found")


class DocumentationAgent(Agent):
    """Agent for monitoring documentation quality.

    Checks for:
    - OpenAPI/Swagger documentation
    - README completeness
    - Missing docstrings in public functions
    """

    async def execute(self) -> None:
        """Execute documentation monitoring tasks."""
        self.logger.info(f"Documentation agent {self.config.name} checking docs")

        await self._check_api_docs()
        await self._check_readme()
        await self._check_docstrings()

    async def _check_api_docs(self) -> None:
        """Check API documentation completeness."""
        repo_root = Path.cwd()

        # Check for OpenAPI spec
        openapi_files = list(repo_root.glob("**/openapi.yaml")) + list(
            repo_root.glob("**/openapi.json")
        )

        if openapi_files:
            self.logger.info(f"Found {len(openapi_files)} OpenAPI spec(s)")
            for spec_file in openapi_files:
                try:
                    import yaml

                    with open(spec_file) as f:
                        spec = yaml.safe_load(f)
                        paths_count = len(spec.get("paths", {}))
                        self.logger.debug(
                            f"  {spec_file.name}: {paths_count} endpoints documented"
                        )
                except Exception:
                    self.logger.debug(f"  {spec_file.name}: could not parse")
        else:
            self.logger.warning(
                "No OpenAPI specification found - consider adding openapi.yaml"
            )

    async def _check_readme(self) -> None:
        """Check README.md completeness."""
        repo_root = Path.cwd()
        readme = repo_root / "README.md"

        if not readme.exists():
            self.logger.error("README.md not found!")
            return

        content = readme.read_text()
        required_sections = [
            ("installation", "Installation"),
            ("usage", "Usage"),
            ("license", "License"),
        ]

        missing_sections = []
        for keyword, section in required_sections:
            if keyword.lower() not in content.lower():
                missing_sections.append(section)

        if missing_sections:
            self.logger.warning(
                f"README.md missing recommended sections: {', '.join(missing_sections)}"
            )
        else:
            self.logger.info("README.md has all recommended sections")

    async def _check_docstrings(self) -> None:
        """Check for missing docstrings in Python files."""
        repo_root = Path.cwd()

        # Use pydocstyle if available
        if shutil.which("pydocstyle"):
            result = await run_command(
                ["pydocstyle", "prep", "--count"],
                cwd=repo_root,
                timeout=120,
            )

            if result.output.strip():
                lines = result.output.strip().split("\n")
                # Last line usually contains count
                self.logger.info(f"pydocstyle found {len(lines)} docstring issues")
            else:
                self.logger.info("All public modules have docstrings")
        else:
            self.logger.debug("pydocstyle not installed - skipping docstring check")


class ComplianceAgent(Agent):
    """Agent for monitoring regulatory compliance.

    Checks for:
    - License compatibility using pip-licenses
    - GDPR/CCPA compliance markers
    - Security policy presence
    """

    async def execute(self) -> None:
        """Execute compliance monitoring tasks."""
        self.logger.info(f"Compliance agent {self.config.name} checking compliance")

        await self._check_license_compliance()
        await self._check_security_policy()
        await self._check_privacy_docs()

    async def _check_license_compliance(self) -> None:
        """Check license compliance using pip-licenses."""
        repo_root = Path.cwd()

        if not shutil.which("pip-licenses"):
            self.logger.debug("pip-licenses not installed - skipping license check")
            return

        result = await run_command(
            ["pip-licenses", "--format=json"],
            cwd=repo_root,
            timeout=60,
        )

        if result.success and result.output.strip():
            try:
                licenses = json.loads(result.output)

                # Check for problematic licenses
                problematic = ["GPL", "AGPL", "SSPL"]
                issues = [
                    pkg
                    for pkg in licenses
                    if any(lic in pkg.get("License", "") for lic in problematic)
                ]

                if issues:
                    self.logger.warning(
                        f"Found {len(issues)} packages with copyleft licenses:"
                    )
                    for pkg in issues[:5]:
                        self.logger.warning(
                            f"  {pkg.get('Name')}: {pkg.get('License')}"
                        )
                else:
                    self.logger.info(
                        f"License check passed - {len(licenses)} packages scanned"
                    )
            except json.JSONDecodeError:
                self.logger.debug("Could not parse pip-licenses output")

    async def _check_security_policy(self) -> None:
        """Check for security policy and disclosure process."""
        repo_root = Path.cwd()

        security_files = [
            "SECURITY.md",
            ".github/SECURITY.md",
            "docs/SECURITY.md",
        ]

        found = False
        for sec_file in security_files:
            if (repo_root / sec_file).exists():
                found = True
                self.logger.info(f"Security policy found: {sec_file}")
                break

        if not found:
            self.logger.warning(
                "No SECURITY.md found - add vulnerability disclosure policy"
            )

    async def _check_privacy_docs(self) -> None:
        """Check for privacy documentation."""
        repo_root = Path.cwd()

        privacy_indicators = [
            "PRIVACY.md",
            "GDPR.md",
            "gdpr_ccpa_core/",
        ]

        found_docs = []
        for indicator in privacy_indicators:
            path = repo_root / indicator
            if path.exists():
                found_docs.append(indicator)

        if found_docs:
            self.logger.info(f"Privacy compliance docs found: {', '.join(found_docs)}")
        else:
            self.logger.warning(
                "No privacy documentation found - required for GDPR/CCPA compliance"
            )
