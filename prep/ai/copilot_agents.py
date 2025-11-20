"""Copilot agents for automated code auditing.

This module provides specialized AI agents for comprehensive code audits:
- SecurityAgent: Scans for security vulnerabilities
- BackendArchitectAgent: Reviews API design and database patterns
- CodeQualityAgent: Checks code style, complexity, and documentation
- TestingAgent: Validates test coverage and test patterns
- OperationsAgent: Flags destructive operations requiring human approval

Each agent uses AST parsing for static code analysis and returns structured
findings with severity levels for integration into CI/CD pipelines.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from prep.ai.agent_framework import AgentResponse, AIAgent


class Severity(Enum):
    """Severity levels for audit findings."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class Finding:
    """Represents a single audit finding."""

    agent: str
    severity: Severity
    message: str
    file_path: str
    line_number: int | None = None
    code_snippet: str | None = None
    recommendation: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Format finding as a readable string."""
        location = f"{self.file_path}"
        if self.line_number:
            location += f":{self.line_number}"
        result = f"[{self.severity.value}] {self.agent}: {self.message}\n  Location: {location}"
        if self.recommendation:
            result += f"\n  Recommendation: {self.recommendation}"
        if self.code_snippet:
            result += f"\n  Code: {self.code_snippet}"
        return result


class SecurityAgent(AIAgent):
    """Agent for detecting security vulnerabilities in code.

    Scans for:
    - SQL injection vulnerabilities
    - Hardcoded secrets and API keys
    - Insecure authentication patterns
    - Missing input validation
    - Unsafe file operations
    - Command injection risks
    """

    async def execute_task(
        self, task_description: str, context: dict[str, Any]
    ) -> AgentResponse:
        """Execute security audit on provided code.

        Args:
            task_description: Description of the audit task
            context: Must contain 'file_path' and optionally 'code_content'

        Returns:
            AgentResponse with security findings
        """
        file_path = context.get("file_path", "")
        code_content = context.get("code_content", "")

        if not code_content and file_path:
            try:
                code_content = Path(file_path).read_text()
            except Exception:
                return AgentResponse(
                    content="Unable to read file",
                    metadata={"error": "File read failed"},
                )

        findings = self._scan_code(code_content, file_path)
        return AgentResponse(
            content=f"Security scan complete: {len(findings)} issues found",
            metadata={"findings": [f.__dict__ for f in findings], "count": len(findings)},
        )

    def _scan_code(self, code: str, file_path: str) -> list[Finding]:
        """Scan code for security vulnerabilities."""
        findings: list[Finding] = []

        # Check for hardcoded secrets
        findings.extend(self._check_hardcoded_secrets(code, file_path))

        # Check for SQL injection risks
        findings.extend(self._check_sql_injection(code, file_path))

        # Check for insecure authentication
        findings.extend(self._check_auth_patterns(code, file_path))

        # Check for unsafe file operations
        findings.extend(self._check_file_operations(code, file_path))

        # Check for command injection
        findings.extend(self._check_command_injection(code, file_path))

        return findings

    def _check_hardcoded_secrets(self, code: str, file_path: str) -> list[Finding]:
        """Check for hardcoded secrets and API keys."""
        findings: list[Finding] = []
        lines = code.split("\n")

        # Patterns for potential secrets
        secret_patterns = [
            (r'(?i)(api[_-]?key|secret[_-]?key|password)\s*=\s*["\'][^"\']{8,}["\']', "API key or secret"),
            (r'(?i)token\s*=\s*["\'][^"\']{20,}["\']', "Authentication token"),
            (r'(?i)aws[_-]?(access|secret)[_-]?key[_-]?id?\s*=\s*["\'][^"\']+["\']', "AWS credentials"),
            (r'(?i)stripe[_-]?key\s*=\s*["\'][^"\']+["\']', "Stripe API key"),
        ]

        for line_num, line in enumerate(lines, 1):
            # Skip comments and test files
            if line.strip().startswith("#") or "test" in file_path.lower():
                continue

            for pattern, secret_type in secret_patterns:
                if re.search(pattern, line):
                    findings.append(
                        Finding(
                            agent="SecurityAgent",
                            severity=Severity.CRITICAL,
                            message=f"Potential hardcoded {secret_type} detected",
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=line.strip()[:80],
                            recommendation="Use environment variables or secure secret management",
                        )
                    )

        return findings

    def _check_sql_injection(self, code: str, file_path: str) -> list[Finding]:
        """Check for SQL injection vulnerabilities."""
        findings: list[Finding] = []
        lines = code.split("\n")

        # Patterns indicating potential SQL injection
        sql_patterns = [
            (r'execute\([^)]*%s[^)]*%', "String formatting in SQL query"),
            (r'execute\([^)]*\.format\(', "format() in SQL query"),
            (r'execute\([^)]*\+\s*["\']', "String concatenation in SQL query"),
            (r'(?i)f["\'].*?select.*?\{.*?\}.*?["\']', "f-string in SQL query"),
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern, issue_type in sql_patterns:
                if re.search(pattern, line):
                    findings.append(
                        Finding(
                            agent="SecurityAgent",
                            severity=Severity.HIGH,
                            message=f"Potential SQL injection: {issue_type}",
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=line.strip()[:80],
                            recommendation="Use parameterized queries or ORM methods",
                        )
                    )

        return findings

    def _check_auth_patterns(self, code: str, file_path: str) -> list[Finding]:
        """Check for insecure authentication patterns."""
        findings: list[Finding] = []
        lines = code.split("\n")

        auth_issues = [
            (r'(?i)jwt\.decode\([^)]*verify\s*=\s*False', "JWT verification disabled"),
            (r'(?i)auth.*=.*None', "Authentication bypass"),
            (r'(?i)password.*==.*["\'].*["\']', "Hardcoded password comparison"),
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern, issue_type in auth_issues:
                if re.search(pattern, line):
                    findings.append(
                        Finding(
                            agent="SecurityAgent",
                            severity=Severity.CRITICAL,
                            message=f"Insecure authentication: {issue_type}",
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=line.strip()[:80],
                            recommendation="Always verify JWT signatures and use secure authentication",
                        )
                    )

        return findings

    def _check_file_operations(self, code: str, file_path: str) -> list[Finding]:
        """Check for unsafe file operations."""
        findings: list[Finding] = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return findings

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "open":
                    # Check if mode includes 'w' or 'a' without proper validation
                    if len(node.args) >= 2:
                        findings.append(
                            Finding(
                                agent="SecurityAgent",
                                severity=Severity.MEDIUM,
                                message="File write operation detected - ensure path validation",
                                file_path=file_path,
                                line_number=getattr(node, "lineno", None),
                                recommendation="Validate file paths to prevent directory traversal",
                            )
                        )

        return findings

    def _check_command_injection(self, code: str, file_path: str) -> list[Finding]:
        """Check for command injection vulnerabilities."""
        findings: list[Finding] = []
        lines = code.split("\n")

        cmd_patterns = [
            (r'os\.system\(', "os.system() call"),
            (r'subprocess\.(call|run|Popen)\([^)]*shell\s*=\s*True', "shell=True in subprocess"),
            (r'eval\(', "eval() usage"),
            (r'exec\(', "exec() usage"),
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern, issue_type in cmd_patterns:
                if re.search(pattern, line):
                    findings.append(
                        Finding(
                            agent="SecurityAgent",
                            severity=Severity.HIGH,
                            message=f"Potential command injection: {issue_type}",
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=line.strip()[:80],
                            recommendation="Avoid shell=True and validate all inputs",
                        )
                    )

        return findings


class BackendArchitectAgent(AIAgent):
    """Agent for reviewing backend architecture and design patterns.

    Reviews:
    - API endpoint design and RESTful patterns
    - Database query optimization
    - Async/await usage
    - Service layer boundaries
    - Error handling patterns
    """

    async def execute_task(
        self, task_description: str, context: dict[str, Any]
    ) -> AgentResponse:
        """Execute architecture review on provided code.

        Args:
            task_description: Description of the review task
            context: Must contain 'file_path' and optionally 'code_content'

        Returns:
            AgentResponse with architecture findings
        """
        file_path = context.get("file_path", "")
        code_content = context.get("code_content", "")

        if not code_content and file_path:
            try:
                code_content = Path(file_path).read_text()
            except Exception:
                return AgentResponse(
                    content="Unable to read file",
                    metadata={"error": "File read failed"},
                )

        findings = self._review_architecture(code_content, file_path)
        return AgentResponse(
            content=f"Architecture review complete: {len(findings)} issues found",
            metadata={"findings": [f.__dict__ for f in findings], "count": len(findings)},
        )

    def _review_architecture(self, code: str, file_path: str) -> list[Finding]:
        """Review code architecture and design patterns."""
        findings: list[Finding] = []

        # Check async patterns
        findings.extend(self._check_async_patterns(code, file_path))

        # Check database patterns
        findings.extend(self._check_database_patterns(code, file_path))

        # Check API design
        findings.extend(self._check_api_design(code, file_path))

        # Check error handling
        findings.extend(self._check_error_handling(code, file_path))

        return findings

    def _check_async_patterns(self, code: str, file_path: str) -> list[Finding]:
        """Check async/await usage patterns."""
        findings: list[Finding] = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return findings

        for node in ast.walk(tree):
            # Check for blocking I/O in async functions
            if isinstance(node, ast.AsyncFunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        # Check for blocking operations
                        if isinstance(child.func, ast.Attribute):
                            if child.func.attr in ["read", "write", "execute", "query"]:
                                # Check if it's awaited
                                parent_is_await = any(
                                    isinstance(p, ast.Await) for p in ast.walk(node)
                                )
                                if not parent_is_await:
                                    findings.append(
                                        Finding(
                                            agent="BackendArchitectAgent",
                                            severity=Severity.MEDIUM,
                                            message="Potential blocking I/O in async function",
                                            file_path=file_path,
                                            line_number=getattr(child, "lineno", None),
                                            recommendation="Use await for I/O operations",
                                        )
                                    )

        return findings

    def _check_database_patterns(self, code: str, file_path: str) -> list[Finding]:
        """Check database access patterns."""
        findings: list[Finding] = []
        lines = code.split("\n")

        in_loop = False
        loop_line = 0

        for line_num, line in enumerate(lines, 1):
            if "for " in line and " in " in line:
                in_loop = True
                loop_line = line_num
            elif in_loop and (".query(" in line or ".execute(" in line):
                findings.append(
                    Finding(
                        agent="BackendArchitectAgent",
                        severity=Severity.MEDIUM,
                        message="Potential N+1 query pattern detected",
                        file_path=file_path,
                        line_number=line_num,
                        recommendation="Consider using batch queries or eager loading",
                        metadata={"loop_line": loop_line},
                    )
                )
                in_loop = False
            elif in_loop and line.strip() and not line.strip().startswith((" ", "\t")):
                in_loop = False

        return findings

    def _check_api_design(self, code: str, file_path: str) -> list[Finding]:
        """Check API endpoint design patterns."""
        findings: list[Finding] = []

        if "api" not in file_path and "route" not in file_path:
            return findings

        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Check for proper HTTP status codes
            if "return" in line and "dict" in line and "status" not in line:
                if "@router." in "\n".join(lines[max(0, line_num - 10) : line_num]):
                    findings.append(
                        Finding(
                            agent="BackendArchitectAgent",
                            severity=Severity.LOW,
                            message="API endpoint may not specify status code",
                            file_path=file_path,
                            line_number=line_num,
                            recommendation="Explicitly set HTTP status codes",
                        )
                    )

        return findings

    def _check_error_handling(self, code: str, file_path: str) -> list[Finding]:
        """Check error handling patterns."""
        findings: list[Finding] = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return findings

        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                # Check for bare except
                for handler in node.handlers:
                    if handler.type is None:
                        findings.append(
                            Finding(
                                agent="BackendArchitectAgent",
                                severity=Severity.MEDIUM,
                                message="Bare except clause detected",
                                file_path=file_path,
                                line_number=getattr(handler, "lineno", None),
                                recommendation="Catch specific exceptions",
                            )
                        )

        return findings


class CodeQualityAgent(AIAgent):
    """Agent for assessing code quality and style.

    Checks:
    - Code complexity (cyclomatic complexity)
    - Type hints presence
    - Documentation (docstrings)
    - Naming conventions
    - Code duplication patterns
    """

    async def execute_task(
        self, task_description: str, context: dict[str, Any]
    ) -> AgentResponse:
        """Execute code quality assessment.

        Args:
            task_description: Description of the assessment task
            context: Must contain 'file_path' and optionally 'code_content'

        Returns:
            AgentResponse with quality findings
        """
        file_path = context.get("file_path", "")
        code_content = context.get("code_content", "")

        if not code_content and file_path:
            try:
                code_content = Path(file_path).read_text()
            except Exception:
                return AgentResponse(
                    content="Unable to read file",
                    metadata={"error": "File read failed"},
                )

        findings = self._assess_quality(code_content, file_path)
        return AgentResponse(
            content=f"Code quality assessment complete: {len(findings)} issues found",
            metadata={"findings": [f.__dict__ for f in findings], "count": len(findings)},
        )

    def _assess_quality(self, code: str, file_path: str) -> list[Finding]:
        """Assess code quality metrics."""
        findings: list[Finding] = []

        # Check complexity
        findings.extend(self._check_complexity(code, file_path))

        # Check type hints
        findings.extend(self._check_type_hints(code, file_path))

        # Check documentation
        findings.extend(self._check_documentation(code, file_path))

        # Check naming conventions
        findings.extend(self._check_naming(code, file_path))

        return findings

    def _check_complexity(self, code: str, file_path: str) -> list[Finding]:
        """Check code complexity."""
        findings: list[Finding] = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return findings

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Simple complexity check based on decision points
                complexity = self._calculate_complexity(node)
                if complexity > 10:
                    findings.append(
                        Finding(
                            agent="CodeQualityAgent",
                            severity=Severity.MEDIUM,
                            message=f"High complexity function: {node.name} (complexity: {complexity})",
                            file_path=file_path,
                            line_number=node.lineno,
                            recommendation="Consider breaking down into smaller functions",
                            metadata={"complexity": complexity},
                        )
                    )

        return findings

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With, ast.Assert)
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _check_type_hints(self, code: str, file_path: str) -> list[Finding]:
        """Check for missing type hints."""
        findings: list[Finding] = []

        # Skip test files
        if "test" in file_path.lower():
            return findings

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return findings

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private methods and __init__
                if node.name.startswith("_"):
                    continue

                # Check return type annotation
                if node.returns is None and node.name != "__init__":
                    findings.append(
                        Finding(
                            agent="CodeQualityAgent",
                            severity=Severity.LOW,
                            message=f"Function '{node.name}' missing return type hint",
                            file_path=file_path,
                            line_number=node.lineno,
                            recommendation="Add return type annotation",
                        )
                    )

                # Check parameter type annotations
                for arg in node.args.args:
                    if arg.annotation is None and arg.arg != "self" and arg.arg != "cls":
                        findings.append(
                            Finding(
                                agent="CodeQualityAgent",
                                severity=Severity.LOW,
                                message=f"Parameter '{arg.arg}' in '{node.name}' missing type hint",
                                file_path=file_path,
                                line_number=node.lineno,
                                recommendation="Add parameter type annotation",
                            )
                        )

        return findings

    def _check_documentation(self, code: str, file_path: str) -> list[Finding]:
        """Check for missing documentation."""
        findings: list[Finding] = []

        # Skip test files and init files
        if "test" in file_path.lower() or "__init__" in file_path:
            return findings

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return findings

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Skip private methods
                if node.name.startswith("_") and not node.name.startswith("__"):
                    continue

                docstring = ast.get_docstring(node)
                if docstring is None:
                    severity = Severity.LOW
                    if isinstance(node, ast.ClassDef):
                        severity = Severity.MEDIUM

                    findings.append(
                        Finding(
                            agent="CodeQualityAgent",
                            severity=severity,
                            message=f"{node.__class__.__name__} '{node.name}' missing docstring",
                            file_path=file_path,
                            line_number=node.lineno,
                            recommendation="Add comprehensive docstring",
                        )
                    )

        return findings

    def _check_naming(self, code: str, file_path: str) -> list[Finding]:
        """Check naming conventions."""
        findings: list[Finding] = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return findings

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check snake_case for functions
                if not re.match(r"^[a-z_][a-z0-9_]*$", node.name) and not node.name.startswith(
                    "__"
                ):
                    findings.append(
                        Finding(
                            agent="CodeQualityAgent",
                            severity=Severity.LOW,
                            message=f"Function '{node.name}' does not follow snake_case convention",
                            file_path=file_path,
                            line_number=node.lineno,
                            recommendation="Use snake_case for function names",
                        )
                    )

            elif isinstance(node, ast.ClassDef):
                # Check PascalCase for classes
                if not re.match(r"^[A-Z][a-zA-Z0-9]*$", node.name):
                    findings.append(
                        Finding(
                            agent="CodeQualityAgent",
                            severity=Severity.LOW,
                            message=f"Class '{node.name}' does not follow PascalCase convention",
                            file_path=file_path,
                            line_number=node.lineno,
                            recommendation="Use PascalCase for class names",
                        )
                    )

        return findings


class TestingAgent(AIAgent):
    """Agent for validating test coverage and test quality.

    Validates:
    - Test file presence for modules
    - Test naming conventions
    - Assertion presence
    - Test isolation
    - Mock usage patterns
    """

    async def execute_task(
        self, task_description: str, context: dict[str, Any]
    ) -> AgentResponse:
        """Execute test validation.

        Args:
            task_description: Description of the validation task
            context: Must contain 'file_path' and optionally 'code_content'

        Returns:
            AgentResponse with testing findings
        """
        file_path = context.get("file_path", "")
        code_content = context.get("code_content", "")

        if not code_content and file_path:
            try:
                code_content = Path(file_path).read_text()
            except Exception:
                return AgentResponse(
                    content="Unable to read file",
                    metadata={"error": "File read failed"},
                )

        findings = self._validate_tests(code_content, file_path)
        return AgentResponse(
            content=f"Test validation complete: {len(findings)} issues found",
            metadata={"findings": [f.__dict__ for f in findings], "count": len(findings)},
        )

    def _validate_tests(self, code: str, file_path: str) -> list[Finding]:
        """Validate test code quality."""
        findings: list[Finding] = []

        is_test_file = "test_" in file_path or "_test.py" in file_path

        if not is_test_file:
            # Check if production code has corresponding tests
            findings.extend(self._check_test_coverage(file_path))
        else:
            # Validate test file quality
            findings.extend(self._check_test_quality(code, file_path))

        return findings

    def _check_test_coverage(self, file_path: str) -> list[Finding]:
        """Check if production code has corresponding tests."""
        findings: list[Finding] = []

        # Skip certain directories
        skip_dirs = ["migrations", "alembic", "__pycache__", "scripts", "data"]
        if any(skip_dir in file_path for skip_dir in skip_dirs):
            return findings

        # Check if test file exists
        path = Path(file_path)
        if path.suffix != ".py":
            return findings

        # Construct expected test file path
        test_dir = Path("tests")
        rel_path = path.relative_to(Path("prep")) if "prep" in str(path) else path
        test_file = test_dir / rel_path.parent / f"test_{rel_path.name}"

        if not test_file.exists():
            findings.append(
                Finding(
                    agent="TestingAgent",
                    severity=Severity.MEDIUM,
                    message=f"No test file found for {path.name}",
                    file_path=file_path,
                    recommendation=f"Create test file at {test_file}",
                    metadata={"expected_test_file": str(test_file)},
                )
            )

        return findings

    def _check_test_quality(self, code: str, file_path: str) -> list[Finding]:
        """Check test code quality."""
        findings: list[Finding] = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return findings

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    # Check for assertions
                    has_assertion = self._has_assertion(node)
                    if not has_assertion:
                        findings.append(
                            Finding(
                                agent="TestingAgent",
                                severity=Severity.HIGH,
                                message=f"Test function '{node.name}' has no assertions",
                                file_path=file_path,
                                line_number=node.lineno,
                                recommendation="Add assertions to validate behavior",
                            )
                        )

        return findings

    def _has_assertion(self, node: ast.AST) -> bool:
        """Check if a test function has assertions."""
        for child in ast.walk(node):
            if isinstance(child, ast.Assert):
                return True
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr.startswith("assert"):
                        return True
        return False


class OperationsAgent(AIAgent):
    """Agent for flagging destructive operations requiring human approval.

    Detects:
    - File deletion operations
    - Database table drops
    - Data deletion queries
    - Production environment modifications
    - Irreversible state changes
    """

    async def execute_task(
        self, task_description: str, context: dict[str, Any]
    ) -> AgentResponse:
        """Execute operations audit.

        Args:
            task_description: Description of the audit task
            context: Must contain 'file_path' and optionally 'code_content'

        Returns:
            AgentResponse with operations findings
        """
        file_path = context.get("file_path", "")
        code_content = context.get("code_content", "")

        if not code_content and file_path:
            try:
                code_content = Path(file_path).read_text()
            except Exception:
                return AgentResponse(
                    content="Unable to read file",
                    metadata={"error": "File read failed"},
                )

        findings = self._audit_operations(code_content, file_path)

        # Check if any findings require human approval
        requires_human = any(f.severity in [Severity.CRITICAL, Severity.HIGH] for f in findings)

        return AgentResponse(
            content=f"Operations audit complete: {len(findings)} operations flagged",
            metadata={
                "findings": [f.__dict__ for f in findings],
                "count": len(findings),
                "requires_human_approval": requires_human,
            },
        )

    def _audit_operations(self, code: str, file_path: str) -> list[Finding]:
        """Audit code for destructive operations."""
        findings: list[Finding] = []

        # Check file operations
        findings.extend(self._check_file_deletion(code, file_path))

        # Check database operations
        findings.extend(self._check_database_deletion(code, file_path))

        # Check production modifications
        findings.extend(self._check_production_operations(code, file_path))

        return findings

    def _check_file_deletion(self, code: str, file_path: str) -> list[Finding]:
        """Check for file deletion operations."""
        findings: list[Finding] = []
        lines = code.split("\n")

        deletion_patterns = [
            (r"os\.remove\(", "os.remove()"),
            (r"os\.unlink\(", "os.unlink()"),
            (r"shutil\.rmtree\(", "shutil.rmtree()"),
            (r"Path\([^)]+\)\.unlink\(", "Path.unlink()"),
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern, operation in deletion_patterns:
                if re.search(pattern, line):
                    findings.append(
                        Finding(
                            agent="OperationsAgent",
                            severity=Severity.HIGH,
                            message=f"File deletion operation detected: {operation}",
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=line.strip()[:80],
                            recommendation="Requires human approval before execution",
                        )
                    )

        return findings

    def _check_database_deletion(self, code: str, file_path: str) -> list[Finding]:
        """Check for database deletion operations."""
        findings: list[Finding] = []
        lines = code.split("\n")

        db_deletion_patterns = [
            (r"(?i)DROP\s+TABLE", "DROP TABLE statement"),
            (r"(?i)DELETE\s+FROM", "DELETE FROM statement"),
            (r"(?i)TRUNCATE\s+TABLE", "TRUNCATE TABLE statement"),
            (r"\.delete\(\)", "ORM delete operation"),
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern, operation in db_deletion_patterns:
                if re.search(pattern, line):
                    findings.append(
                        Finding(
                            agent="OperationsAgent",
                            severity=Severity.CRITICAL,
                            message=f"Database deletion operation detected: {operation}",
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=line.strip()[:80],
                            recommendation="Requires human approval and backup verification",
                        )
                    )

        return findings

    def _check_production_operations(self, code: str, file_path: str) -> list[Finding]:
        """Check for operations that modify production environment."""
        findings: list[Finding] = []
        lines = code.split("\n")

        prod_patterns = [
            (r'(?i)environment.*=.*["\']production["\']', "Production environment reference"),
            (r"(?i)PROD", "Production constant"),
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern, operation in prod_patterns:
                if re.search(pattern, line):
                    # Only flag if it's being set or modified
                    if "=" in line and not line.strip().startswith("#"):
                        findings.append(
                            Finding(
                                agent="OperationsAgent",
                                severity=Severity.HIGH,
                                message=f"Production environment modification: {operation}",
                                file_path=file_path,
                                line_number=line_num,
                                code_snippet=line.strip()[:80],
                                recommendation="Verify this change in production carefully",
                            )
                        )

        return findings


__all__ = [
    "Severity",
    "Finding",
    "SecurityAgent",
    "BackendArchitectAgent",
    "CodeQualityAgent",
    "TestingAgent",
    "OperationsAgent",
]
