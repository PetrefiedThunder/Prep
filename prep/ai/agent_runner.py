"""Agent runner utility for comprehensive code auditing.

This module provides utilities to run all copilot agents across Python files
in the repository, aggregating results for comprehensive code audits. Designed
for integration into CI/CD pipelines and PR bot workflows.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from prep.ai.agent_framework import SafetyLayer, ValidationLayer
from prep.ai.copilot_agents import (
    BackendArchitectAgent,
    CodeQualityAgent,
    Finding,
    OperationsAgent,
    SecurityAgent,
    Severity,
    TestingAgent,
)


@dataclass
class AuditReport:
    """Comprehensive audit report from all agents."""

    total_files_scanned: int = 0
    total_findings: int = 0
    findings_by_severity: dict[str, int] = field(default_factory=dict)
    findings_by_agent: dict[str, int] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    requires_human_review: bool = False

    def add_finding(self, finding: Finding) -> None:
        """Add a finding to the report."""
        self.findings.append(finding)
        self.total_findings += 1

        # Update severity counts
        severity_key = finding.severity.value
        self.findings_by_severity[severity_key] = (
            self.findings_by_severity.get(severity_key, 0) + 1
        )

        # Update agent counts
        self.findings_by_agent[finding.agent] = self.findings_by_agent.get(finding.agent, 0) + 1

        # Check if human review required
        if finding.severity in [Severity.CRITICAL, Severity.HIGH]:
            self.requires_human_review = True

    def get_summary(self) -> str:
        """Get a formatted summary of the audit report."""
        lines = ["=" * 80, "CODE AUDIT REPORT", "=" * 80, ""]

        lines.append(f"Files Scanned: {self.total_files_scanned}")
        lines.append(f"Total Findings: {self.total_findings}")
        lines.append(f"Requires Human Review: {self.requires_human_review}")
        lines.append("")

        if self.findings_by_severity:
            lines.append("Findings by Severity:")
            for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
                count = self.findings_by_severity.get(severity, 0)
                if count > 0:
                    lines.append(f"  {severity}: {count}")
            lines.append("")

        if self.findings_by_agent:
            lines.append("Findings by Agent:")
            for agent, count in sorted(self.findings_by_agent.items()):
                lines.append(f"  {agent}: {count}")
            lines.append("")

        if self.errors:
            lines.append(f"Errors: {len(self.errors)}")
            for error in self.errors[:10]:  # Show first 10 errors
                lines.append(f"  - {error}")
            if len(self.errors) > 10:
                lines.append(f"  ... and {len(self.errors) - 10} more")
            lines.append("")

        lines.append("=" * 80)
        return "\n".join(lines)

    def get_detailed_report(self, max_findings: int = 100) -> str:
        """Get a detailed report with individual findings.

        Args:
            max_findings: Maximum number of findings to include in detail

        Returns:
            Formatted detailed report string
        """
        lines = [self.get_summary(), "", "DETAILED FINDINGS:", ""]

        # Group findings by severity
        by_severity: dict[Severity, list[Finding]] = {}
        for finding in self.findings:
            by_severity.setdefault(finding.severity, []).append(finding)

        count = 0
        for severity in [
            Severity.CRITICAL,
            Severity.HIGH,
            Severity.MEDIUM,
            Severity.LOW,
            Severity.INFO,
        ]:
            if severity in by_severity:
                findings = by_severity[severity]
                lines.append(f"\n{severity.value} ({len(findings)} findings):")
                lines.append("-" * 80)

                for finding in findings[:max_findings - count]:
                    lines.append(str(finding))
                    lines.append("")
                    count += 1

                    if count >= max_findings:
                        remaining = self.total_findings - count
                        if remaining > 0:
                            lines.append(f"... and {remaining} more findings")
                        break

                if count >= max_findings:
                    break

        return "\n".join(lines)


class AgentRunner:
    """Utility to run all copilot agents across Python files."""

    def __init__(
        self,
        root_dir: str | Path = ".",
        agents: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> None:
        """Initialize the agent runner.

        Args:
            root_dir: Root directory to scan for Python files
            agents: List of agent names to run (default: all agents)
            exclude_patterns: List of path patterns to exclude (e.g., ["tests/", ".venv/"])
        """
        self.root_dir = Path(root_dir)
        self.safety_layer = SafetyLayer()
        self.validation_layer = ValidationLayer()

        # Initialize agents
        self.available_agents = {
            "security": SecurityAgent(self.safety_layer, self.validation_layer),
            "architecture": BackendArchitectAgent(self.safety_layer, self.validation_layer),
            "quality": CodeQualityAgent(self.safety_layer, self.validation_layer),
            "testing": TestingAgent(self.safety_layer, self.validation_layer),
            "operations": OperationsAgent(self.safety_layer, self.validation_layer),
        }

        # Select agents to run
        if agents is None:
            self.agents = self.available_agents
        else:
            self.agents = {k: v for k, v in self.available_agents.items() if k in agents}

        # Default exclude patterns
        self.exclude_patterns = exclude_patterns or [
            ".venv/",
            "venv/",
            "__pycache__/",
            ".git/",
            "node_modules/",
            ".pytest_cache/",
            "migrations/",
            "alembic/versions/",
            ".tox/",
            "build/",
            "dist/",
            "*.egg-info/",
        ]

    def discover_python_files(self) -> list[Path]:
        """Discover all Python files in the repository.

        Returns:
            List of Path objects for Python files
        """
        python_files = []

        for path in self.root_dir.rglob("*.py"):
            # Check if path matches any exclude pattern
            path_str = str(path)
            if any(pattern in path_str for pattern in self.exclude_patterns):
                continue

            python_files.append(path)

        return sorted(python_files)

    async def scan_file(self, file_path: Path) -> list[Finding]:
        """Scan a single file with all agents.

        Args:
            file_path: Path to the Python file to scan

        Returns:
            List of findings from all agents
        """
        findings: list[Finding] = []

        try:
            code_content = file_path.read_text()
        except Exception as e:
            # Return error as a finding
            findings.append(
                Finding(
                    agent="AgentRunner",
                    severity=Severity.INFO,
                    message=f"Could not read file: {e}",
                    file_path=str(file_path),
                )
            )
            return findings

        # Run all agents on the file
        for agent_name, agent in self.agents.items():
            try:
                result = await agent.execute_task(
                    f"Scan {file_path.name}",
                    {"file_path": str(file_path), "code_content": code_content},
                )

                # Extract findings from result metadata
                agent_findings = result.metadata.get("findings", [])
                for finding_dict in agent_findings:
                    # Reconstruct Finding object
                    finding = Finding(
                        agent=finding_dict["agent"],
                        severity=Severity(finding_dict["severity"]),
                        message=finding_dict["message"],
                        file_path=finding_dict["file_path"],
                        line_number=finding_dict.get("line_number"),
                        code_snippet=finding_dict.get("code_snippet"),
                        recommendation=finding_dict.get("recommendation"),
                        metadata=finding_dict.get("metadata", {}),
                    )
                    findings.append(finding)

            except Exception as e:
                findings.append(
                    Finding(
                        agent=agent_name,
                        severity=Severity.INFO,
                        message=f"Agent error: {e}",
                        file_path=str(file_path),
                    )
                )

        return findings

    async def run_audit(
        self,
        file_patterns: list[str] | None = None,
        max_files: int | None = None,
    ) -> AuditReport:
        """Run comprehensive audit across all Python files.

        Args:
            file_patterns: Optional list of file patterns to include (e.g., ["prep/auth/*"])
            max_files: Optional maximum number of files to scan (for testing)

        Returns:
            AuditReport with aggregated findings
        """
        report = AuditReport()

        # Discover files
        python_files = self.discover_python_files()

        # Filter by patterns if provided
        if file_patterns:
            import fnmatch
            filtered_files = []
            for pattern in file_patterns:
                for file in python_files:
                    # Use fnmatch for consistent glob-style matching
                    if fnmatch.fnmatch(str(file), f"*{pattern}*") or fnmatch.fnmatch(str(file), pattern):
                        filtered_files.append(file)
            python_files = list(set(filtered_files))  # Remove duplicates

        # Limit files if requested
        if max_files:
            python_files = python_files[:max_files]

        report.total_files_scanned = len(python_files)

        # Scan files (can be parallelized)
        tasks = [self.scan_file(file) for file in python_files]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    report.errors.append(f"{python_files[i]}: {result}")
                else:
                    for finding in result:
                        report.add_finding(finding)

        except Exception as e:
            report.errors.append(f"Audit failed: {e}")

        return report

    async def run_audit_on_file(self, file_path: str | Path) -> AuditReport:
        """Run audit on a single file.

        Args:
            file_path: Path to the Python file to audit

        Returns:
            AuditReport with findings for the file
        """
        report = AuditReport()
        report.total_files_scanned = 1

        file_path = Path(file_path)
        findings = await self.scan_file(file_path)

        for finding in findings:
            report.add_finding(finding)

        return report


async def main() -> None:
    """Run agent audit from command line."""
    import sys

    if len(sys.argv) > 1:
        # Audit specific file
        file_path = sys.argv[1]
        runner = AgentRunner()
        report = await runner.run_audit_on_file(file_path)
        print(report.get_detailed_report())
    else:
        # Full repository audit
        runner = AgentRunner(root_dir="prep")
        print("Starting comprehensive code audit...")
        report = await runner.run_audit(max_files=10)  # Limit for demo
        print(report.get_detailed_report())


if __name__ == "__main__":
    asyncio.run(main())


__all__ = ["AgentRunner", "AuditReport"]
