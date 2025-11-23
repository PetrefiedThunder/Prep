"""Tests for copilot agents and agent runner."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from prep.ai import agent_framework, agent_runner, copilot_agents


@pytest.fixture
def safety_layer():
    """Create a safety layer for testing."""
    return agent_framework.SafetyLayer()


@pytest.fixture
def validation_layer():
    """Create a validation layer for testing."""
    return agent_framework.ValidationLayer()


@pytest.fixture
def security_agent(safety_layer, validation_layer):
    """Create a security agent for testing."""
    return copilot_agents.SecurityAgent(safety_layer, validation_layer)


@pytest.fixture
def backend_agent(safety_layer, validation_layer):
    """Create a backend architect agent for testing."""
    return copilot_agents.BackendArchitectAgent(safety_layer, validation_layer)


@pytest.fixture
def quality_agent(safety_layer, validation_layer):
    """Create a code quality agent for testing."""
    return copilot_agents.CodeQualityAgent(safety_layer, validation_layer)


@pytest.fixture
def testing_agent(safety_layer, validation_layer):
    """Create a testing agent for testing."""
    return copilot_agents.TestingAgent(safety_layer, validation_layer)


@pytest.fixture
def operations_agent(safety_layer, validation_layer):
    """Create an operations agent for testing."""
    return copilot_agents.OperationsAgent(safety_layer, validation_layer)


class TestSecurityAgentBehavior:
    """Tests for SecurityAgent."""

    @pytest.mark.asyncio
    async def test_detects_hardcoded_secrets(self, security_agent):
        """Test that security agent detects hardcoded secrets."""
        code = """
api_key = "fake_test_key_abcdef123456789012345678"
secret_key = "very_secret_password_123"
"""
        result = await security_agent.execute_task(
            "Scan for secrets", {"file_path": "production.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        assert len(findings) >= 1
        assert any("hardcoded" in f["message"].lower() for f in findings)

    @pytest.mark.asyncio
    async def test_detects_sql_injection(self, security_agent):
        """Test that security agent detects SQL injection risks."""
        code = """
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return execute(query)
"""
        result = await security_agent.execute_task(
            "Scan for SQL injection", {"file_path": "production.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        assert len(findings) >= 1
        assert any("sql" in f["message"].lower() for f in findings)

    @pytest.mark.asyncio
    async def test_detects_insecure_auth(self, security_agent):
        """Test that security agent detects insecure authentication."""
        code = """
import jwt
payload = jwt.decode(token, secret, verify=False)
"""
        result = await security_agent.execute_task(
            "Scan for auth issues", {"file_path": "production.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        assert len(findings) >= 1
        assert any("auth" in f["message"].lower() for f in findings)

    @pytest.mark.asyncio
    async def test_detects_command_injection(self, security_agent):
        """Test that security agent detects command injection risks."""
        code = """
import subprocess
subprocess.run(user_input, shell=True)
"""
        result = await security_agent.execute_task(
            "Scan for command injection", {"file_path": "production.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        assert len(findings) >= 1
        assert any(
            "command" in f["message"].lower() or "shell" in f["message"].lower() for f in findings
        )

    @pytest.mark.asyncio
    async def test_no_findings_for_clean_code(self, security_agent):
        """Test that security agent returns no findings for clean code."""
        code = """
from sqlalchemy import select
async def get_user(db, user_id):
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
"""
        result = await security_agent.execute_task(
            "Scan clean code", {"file_path": "production.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        # Should have minimal or no critical findings
        critical_findings = [
            f for f in findings if f.get("severity") == copilot_agents.Severity.CRITICAL
        ]
        assert len(critical_findings) == 0


class TestBackendArchitectAgentBehavior:
    """Tests for BackendArchitectAgent."""

    @pytest.mark.asyncio
    async def test_detects_n_plus_one_queries(self, backend_agent):
        """Test that backend agent detects N+1 query patterns."""
        code = """
for user in users:
    orders = db.query(Order).filter(Order.user_id == user.id).all()
"""
        result = await backend_agent.execute_task(
            "Review architecture", {"file_path": "production.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        assert len(findings) >= 1
        assert any(
            "n+1" in f["message"].lower() or "query" in f["message"].lower() for f in findings
        )

    @pytest.mark.asyncio
    async def test_detects_bare_except(self, backend_agent):
        """Test that backend agent detects bare except clauses."""
        code = """
try:
    risky_operation()
except:
    pass
"""
        result = await backend_agent.execute_task(
            "Review error handling", {"file_path": "production.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        assert len(findings) >= 1
        assert any("except" in f["message"].lower() for f in findings)


class TestCodeQualityAgentBehavior:
    """Tests for CodeQualityAgent."""

    @pytest.mark.asyncio
    async def test_detects_high_complexity(self, quality_agent):
        """Test that quality agent detects high complexity functions."""
        code = """
def complex_function(x):
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    if x > 40:
                        if x > 50:
                            if x > 60:
                                if x > 70:
                                    if x > 80:
                                        if x > 90:
                                            return "high"
    return "low"
"""
        result = await quality_agent.execute_task(
            "Assess quality", {"file_path": "production.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        assert len(findings) >= 1
        assert any("complexity" in f["message"].lower() for f in findings)

    @pytest.mark.asyncio
    async def test_detects_missing_type_hints(self, quality_agent):
        """Test that quality agent detects missing type hints."""
        code = """
def process_data(data):
    return data * 2
"""
        result = await quality_agent.execute_task(
            "Check type hints", {"file_path": "production.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        assert len(findings) >= 1
        assert any(
            "type" in f["message"].lower() or "hint" in f["message"].lower() for f in findings
        )

    @pytest.mark.asyncio
    async def test_detects_missing_docstrings(self, quality_agent):
        """Test that quality agent detects missing docstrings."""
        code = """
class MyClass:
    def public_method(self):
        pass
"""
        result = await quality_agent.execute_task(
            "Check documentation", {"file_path": "production.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        assert len(findings) >= 1
        assert any("docstring" in f["message"].lower() for f in findings)

    @pytest.mark.asyncio
    async def test_detects_naming_violations(self, quality_agent):
        """Test that quality agent detects naming convention violations."""
        code = """
def MyFunction():
    pass

class my_class:
    pass
"""
        result = await quality_agent.execute_task(
            "Check naming", {"file_path": "production.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        assert len(findings) >= 1
        assert any(
            "convention" in f["message"].lower() or "case" in f["message"].lower() for f in findings
        )


class TestTestingAgentBehavior:
    """Tests for TestingAgent."""

    @pytest.mark.asyncio
    async def test_detects_missing_assertions(self, testing_agent):
        """Test that testing agent detects test functions without assertions."""
        code = """
def test_something():
    result = do_something()
    # No assertion!
"""
        result = await testing_agent.execute_task(
            "Validate tests", {"file_path": "test_module.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        assert len(findings) >= 1
        assert any("assertion" in f["message"].lower() for f in findings)

    @pytest.mark.asyncio
    async def test_accepts_tests_with_assertions(self, testing_agent):
        """Test that testing agent accepts tests with proper assertions."""
        code = """
def test_something():
    result = do_something()
    assert result == expected
"""
        result = await testing_agent.execute_task(
            "Validate tests", {"file_path": "test_module.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        assertion_findings = [f for f in findings if "assertion" in f.get("message", "").lower()]
        assert len(assertion_findings) == 0


class TestOperationsAgentBehavior:
    """Tests for OperationsAgent."""

    @pytest.mark.asyncio
    async def test_detects_file_deletion(self, operations_agent):
        """Test that operations agent detects file deletion operations."""
        code = """
import os
os.remove("/path/to/file.txt")
"""
        result = await operations_agent.execute_task(
            "Audit operations", {"file_path": "production.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        assert len(findings) >= 1
        assert any(
            "deletion" in f["message"].lower() or "remove" in f["message"].lower() for f in findings
        )
        assert result.metadata.get("requires_human_approval") is True

    @pytest.mark.asyncio
    async def test_detects_database_deletion(self, operations_agent):
        """Test that operations agent detects database deletion operations."""
        code = """
query = "DROP TABLE users"
db.execute(query)
"""
        result = await operations_agent.execute_task(
            "Audit operations", {"file_path": "production.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        assert len(findings) >= 1
        assert any(
            "database" in f["message"].lower() or "drop" in f["message"].lower() for f in findings
        )
        assert result.metadata.get("requires_human_approval") is True

    @pytest.mark.asyncio
    async def test_flags_production_modifications(self, operations_agent):
        """Test that operations agent flags production environment modifications."""
        code = """
environment = "production"
config.set("ENV", environment)
"""
        result = await operations_agent.execute_task(
            "Audit operations", {"file_path": "production.py", "code_content": code}
        )

        findings = result.metadata.get("findings", [])
        assert len(findings) >= 1
        assert any("production" in f["message"].lower() for f in findings)


class TestAgentRunner:
    """Tests for AgentRunner."""

    @pytest.mark.asyncio
    async def test_discovers_python_files(self):
        """Test that agent runner discovers Python files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files
            test_dir = Path(tmpdir)
            (test_dir / "file1.py").write_text("# Test file 1")
            (test_dir / "file2.py").write_text("# Test file 2")
            (test_dir / ".venv").mkdir()
            (test_dir / ".venv" / "excluded.py").write_text("# Should be excluded")

            runner = agent_runner.AgentRunner(root_dir=tmpdir)
            files = runner.discover_python_files()

            assert len(files) == 2
            assert all(f.suffix == ".py" for f in files)
            assert not any(".venv" in str(f) for f in files)

    @pytest.mark.asyncio
    async def test_scans_file_with_all_agents(self):
        """Test that agent runner scans files with all agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "production.py"
            test_file.write_text("""
api_key = "secret_123456789"

def test_function():
    pass
""")

            runner = agent_runner.AgentRunner(root_dir=tmpdir)
            findings = await runner.scan_file(test_file)

            assert len(findings) > 0
            # Should have findings from multiple agents
            agents = {f.agent for f in findings}
            assert len(agents) >= 1

    @pytest.mark.asyncio
    async def test_generates_audit_report(self):
        """Test that agent runner generates comprehensive audit reports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "production.py"
            test_file.write_text("""
secret = "hardcoded_secret_123"
""")

            runner = agent_runner.AgentRunner(root_dir=tmpdir)
            report = await runner.run_audit()

            assert report.total_files_scanned == 1
            assert report.total_findings > 0
            assert len(report.findings_by_severity) > 0

            # Test summary generation
            summary = report.get_summary()
            assert "CODE AUDIT REPORT" in summary
            assert "Files Scanned" in summary

            # Test detailed report generation
            detailed = report.get_detailed_report()
            assert "DETAILED FINDINGS" in detailed

    @pytest.mark.asyncio
    async def test_filters_by_file_patterns(self):
        """Test that agent runner can filter files by patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            (test_dir / "auth").mkdir()
            (test_dir / "api").mkdir()
            (test_dir / "auth" / "core.py").write_text("# Auth code")
            (test_dir / "api" / "routes.py").write_text("# API code")

            runner = agent_runner.AgentRunner(root_dir=tmpdir)
            report = await runner.run_audit(file_patterns=["auth/*"])

            # Should only scan auth files
            assert report.total_files_scanned <= 1

    @pytest.mark.asyncio
    async def test_limits_max_files(self):
        """Test that agent runner respects max_files limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            for i in range(10):
                (test_dir / f"file{i}.py").write_text(f"# File {i}")

            runner = agent_runner.AgentRunner(root_dir=tmpdir)
            report = await runner.run_audit(max_files=5)

            assert report.total_files_scanned == 5

    @pytest.mark.asyncio
    async def test_audit_single_file(self):
        """Test that agent runner can audit a single file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "production.py"
            test_file.write_text("api_key = 'secret_123'")

            runner = agent_runner.AgentRunner(root_dir=tmpdir)
            report = await runner.run_audit_on_file(test_file)

            assert report.total_files_scanned == 1
            assert report.total_findings > 0


class TestAuditReport:
    """Tests for AuditReport."""

    def test_adds_finding(self):
        """Test that audit report correctly adds findings."""
        report = agent_runner.AuditReport()
        finding = copilot_agents.Finding(
            agent="TestAgent",
            severity=copilot_agents.Severity.HIGH,
            message="Test issue",
            file_path="production.py",
        )

        report.add_finding(finding)

        assert report.total_findings == 1
        assert report.findings_by_severity["HIGH"] == 1
        assert report.findings_by_agent["TestAgent"] == 1
        assert report.requires_human_review is True

    def test_human_review_for_critical_findings(self):
        """Test that critical findings trigger human review."""
        report = agent_runner.AuditReport()
        report.add_finding(
            copilot_agents.Finding(
                agent="TestAgent",
                severity=copilot_agents.Severity.CRITICAL,
                message="Critical issue",
                file_path="production.py",
            )
        )

        assert report.requires_human_review is True

    def test_no_human_review_for_low_findings(self):
        """Test that low severity findings don't trigger human review."""
        report = agent_runner.AuditReport()
        report.add_finding(
            copilot_agents.Finding(
                agent="TestAgent",
                severity=copilot_agents.Severity.LOW,
                message="Minor issue",
                file_path="production.py",
            )
        )

        assert report.requires_human_review is False

    def test_summary_format(self):
        """Test that summary is properly formatted."""
        report = agent_runner.AuditReport()
        report.total_files_scanned = 5
        report.add_finding(
            copilot_agents.Finding(
                agent="TestAgent",
                severity=copilot_agents.Severity.MEDIUM,
                message="Test",
                file_path="production.py",
            )
        )

        summary = report.get_summary()

        assert "Files Scanned: 5" in summary
        assert "Total Findings: 1" in summary
        assert "MEDIUM: 1" in summary


class TestFinding:
    """Tests for Finding class."""

    def test_finding_str_representation(self):
        """Test that finding formats correctly as string."""
        finding = copilot_agents.Finding(
            agent="TestAgent",
            severity=copilot_agents.Severity.HIGH,
            message="Test issue",
            file_path="production.py",
            line_number=42,
            code_snippet="bad_code()",
            recommendation="Fix this",
        )

        output = str(finding)

        assert "HIGH" in output
        assert "TestAgent" in output
        assert "Test issue" in output
        assert "production.py:42" in output
        assert "bad_code()" in output
        assert "Fix this" in output
