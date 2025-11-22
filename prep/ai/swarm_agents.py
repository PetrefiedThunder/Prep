"""Specialized agents for automated repository maintenance.

This module contains example implementations of agents that demonstrate the
swarm pattern: monitoring repository events and proposing/implementing changes.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from prep.ai.action_system import ActionProposer, ActionType
from prep.ai.agent_framework import AIAgent, AgentResponse
from prep.ai.event_monitor import EventType, RepositoryEvent

logger = logging.getLogger(__name__)


class LintingAgent(AIAgent):
    """Agent that automatically fixes linting issues.

    Monitors Python files for common linting issues and proposes fixes.
    """

    def __init__(self, safety_layer, validation_layer, action_proposer: ActionProposer) -> None:
        """Initialize the linting agent.

        Args:
            safety_layer: Safety layer for validation
            validation_layer: Validation layer for responses
            action_proposer: Action proposer for proposing changes
        """
        super().__init__(safety_layer, validation_layer)
        self.action_proposer = action_proposer
        self.agent_id = "linting_agent"
        self.agent_name = "LintingAgent"

    async def execute_task(self, task_description: str, context: dict[str, Any]) -> AgentResponse:
        """Execute linting task on provided code.

        Args:
            task_description: Description of the linting task
            context: Must contain 'file_path' and optionally 'code_content'

        Returns:
            AgentResponse with linting results
        """
        file_path = context.get("file_path", "")
        code_content = context.get("code_content", "")

        if not code_content and file_path:
            try:
                code_content = Path(file_path).read_text()
            except Exception as e:
                return AgentResponse(
                    content=f"Unable to read file: {e}",
                    metadata={"error": str(e)},
                )

        # Find and fix linting issues
        fixes_made = []
        fixed_code = code_content

        # Fix trailing whitespace
        if re.search(r" +$", fixed_code, re.MULTILINE):
            fixed_code = re.sub(r" +$", "", fixed_code, flags=re.MULTILINE)
            fixes_made.append("removed_trailing_whitespace")

        # Fix missing blank lines at end of file
        if not fixed_code.endswith("\n"):
            fixed_code += "\n"
            fixes_made.append("added_final_newline")

        # Fix multiple blank lines
        if "\n\n\n" in fixed_code:
            fixed_code = re.sub(r"\n{3,}", "\n\n", fixed_code)
            fixes_made.append("reduced_multiple_blank_lines")

        if fixes_made:
            # Propose the fix
            action_id = self.action_proposer.propose_action(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                action_type=ActionType.CODE_FIX,
                description=f"Fix linting issues in {file_path}",
                rationale=f"Automatically fix linting issues: {', '.join(fixes_made)}",
                target_path=file_path,
                content=fixed_code,
                safety_level="low",
                metadata={"fixes": fixes_made},
            )

            return AgentResponse(
                content=f"Proposed {len(fixes_made)} linting fixes",
                metadata={"action_id": action_id, "fixes": fixes_made},
            )
        else:
            return AgentResponse(
                content="No linting issues found",
                metadata={"fixes": []},
            )

    async def handle_event(self, event: RepositoryEvent) -> None:
        """Handle repository events.

        Args:
            event: The repository event to handle
        """
        # Only process Python file modifications
        if event.event_type == EventType.FILE_MODIFIED and event.file_path:
            if event.file_path.endswith(".py"):
                logger.info(f"LintingAgent: Processing {event.file_path}")
                await self.execute_task(
                    f"Lint {event.file_path}", {"file_path": event.file_path}
                )


class DependencyUpdateAgent(AIAgent):
    """Agent that monitors and updates dependencies.

    Monitors package files (requirements.txt, package.json) and proposes updates
    for outdated dependencies.
    """

    def __init__(self, safety_layer, validation_layer, action_proposer: ActionProposer) -> None:
        """Initialize the dependency update agent.

        Args:
            safety_layer: Safety layer for validation
            validation_layer: Validation layer for responses
            action_proposer: Action proposer for proposing changes
        """
        super().__init__(safety_layer, validation_layer)
        self.action_proposer = action_proposer
        self.agent_id = "dependency_update_agent"
        self.agent_name = "DependencyUpdateAgent"

    async def execute_task(self, task_description: str, context: dict[str, Any]) -> AgentResponse:
        """Execute dependency check task.

        Args:
            task_description: Description of the task
            context: Must contain 'file_path'

        Returns:
            AgentResponse with update recommendations
        """
        file_path = context.get("file_path", "")

        if not file_path:
            return AgentResponse(
                content="No file path provided", metadata={"error": "Missing file_path"}
            )

        # Check for outdated dependencies (simplified example)
        if "requirements.txt" in file_path:
            return await self._check_python_dependencies(file_path)
        elif "package.json" in file_path:
            return await self._check_npm_dependencies(file_path)
        else:
            return AgentResponse(
                content="Unsupported dependency file",
                metadata={"file_path": file_path},
            )

    async def _check_python_dependencies(self, file_path: str) -> AgentResponse:
        """Check Python dependencies for updates."""
        try:
            content = Path(file_path).read_text()
            lines = content.split("\n")

            # Example: detect pinned versions that might need updating
            outdated = []
            for line in lines:
                if "==" in line:
                    pkg_name = line.split("==")[0].strip()
                    # In a real implementation, we'd check PyPI for latest version
                    # For demo purposes, we'll just flag packages with very old versions
                    if any(old in line for old in ["1.0.0", "0.1.0", "0.0.1"]):
                        outdated.append(pkg_name)

            if outdated:
                return AgentResponse(
                    content=f"Found {len(outdated)} potentially outdated dependencies",
                    metadata={
                        "outdated": outdated,
                        "recommendation": "Consider updating to latest stable versions",
                    },
                )
            else:
                return AgentResponse(
                    content="All dependencies appear up-to-date",
                    metadata={"outdated": []},
                )

        except Exception as e:
            return AgentResponse(
                content=f"Error checking dependencies: {e}",
                metadata={"error": str(e)},
            )

    async def _check_npm_dependencies(self, file_path: str) -> AgentResponse:
        """Check npm dependencies for updates."""
        try:
            content = Path(file_path).read_text()
            data = json.loads(content)

            dependencies = data.get("dependencies", {})
            outdated = []

            # Simple heuristic: check for very old version patterns
            for pkg, version in dependencies.items():
                if re.match(r"^\^?[0-1]\.", version):
                    outdated.append(pkg)

            if outdated:
                return AgentResponse(
                    content=f"Found {len(outdated)} potentially outdated npm packages",
                    metadata={"outdated": outdated},
                )
            else:
                return AgentResponse(
                    content="npm dependencies appear up-to-date",
                    metadata={"outdated": []},
                )

        except Exception as e:
            return AgentResponse(
                content=f"Error checking npm dependencies: {e}",
                metadata={"error": str(e)},
            )

    async def handle_event(self, event: RepositoryEvent) -> None:
        """Handle repository events.

        Args:
            event: The repository event to handle
        """
        if event.event_type == EventType.FILE_MODIFIED and event.file_path:
            if "requirements.txt" in event.file_path or "package.json" in event.file_path:
                logger.info(f"DependencyUpdateAgent: Processing {event.file_path}")
                await self.execute_task(
                    f"Check dependencies in {event.file_path}", {"file_path": event.file_path}
                )


class DocumentationAgent(AIAgent):
    """Agent that maintains documentation.

    Monitors code changes and ensures documentation stays up-to-date.
    """

    def __init__(self, safety_layer, validation_layer, action_proposer: ActionProposer) -> None:
        """Initialize the documentation agent.

        Args:
            safety_layer: Safety layer for validation
            validation_layer: Validation layer for responses
            action_proposer: Action proposer for proposing changes
        """
        super().__init__(safety_layer, validation_layer)
        self.action_proposer = action_proposer
        self.agent_id = "documentation_agent"
        self.agent_name = "DocumentationAgent"

    async def execute_task(self, task_description: str, context: dict[str, Any]) -> AgentResponse:
        """Execute documentation task.

        Args:
            task_description: Description of the task
            context: Must contain 'file_path' and optionally 'code_content'

        Returns:
            AgentResponse with documentation analysis
        """
        file_path = context.get("file_path", "")
        code_content = context.get("code_content", "")

        if not code_content and file_path:
            try:
                code_content = Path(file_path).read_text()
            except Exception as e:
                return AgentResponse(
                    content=f"Unable to read file: {e}",
                    metadata={"error": str(e)},
                )

        # Check for missing docstrings
        issues = []

        # Check for module docstring
        if not code_content.lstrip().startswith('"""') and not code_content.lstrip().startswith(
            "'''"
        ):
            issues.append("missing_module_docstring")

        # Check for function definitions without docstrings
        function_pattern = r"^(async\s+)?def\s+\w+\([^)]*\):"
        for i, line in enumerate(code_content.split("\n")):
            if re.match(function_pattern, line.strip()):
                # Check if next non-empty line is a docstring
                next_lines = code_content.split("\n")[i + 1 : i + 3]
                has_docstring = any(
                    '"""' in line or "'''" in line for line in next_lines if line.strip()
                )
                if not has_docstring:
                    func_name = re.search(r"def\s+(\w+)", line).group(1)
                    issues.append(f"missing_docstring_for_{func_name}")

        if issues:
            return AgentResponse(
                content=f"Found {len(issues)} documentation issues",
                metadata={"issues": issues, "file_path": file_path},
            )
        else:
            return AgentResponse(
                content="Documentation appears complete",
                metadata={"issues": []},
            )

    async def handle_event(self, event: RepositoryEvent) -> None:
        """Handle repository events.

        Args:
            event: The repository event to handle
        """
        # Process new or modified Python files
        if event.file_path and event.file_path.endswith(".py"):
            if event.event_type in [EventType.FILE_CREATED, EventType.FILE_MODIFIED]:
                logger.info(f"DocumentationAgent: Processing {event.file_path}")
                await self.execute_task(
                    f"Check documentation in {event.file_path}", {"file_path": event.file_path}
                )


class TestGenerationAgent(AIAgent):
    """Agent that generates missing tests.

    Monitors code files and proposes test generation for uncovered code.
    """

    def __init__(self, safety_layer, validation_layer, action_proposer: ActionProposer) -> None:
        """Initialize the test generation agent.

        Args:
            safety_layer: Safety layer for validation
            validation_layer: Validation layer for responses
            action_proposer: Action proposer for proposing changes
        """
        super().__init__(safety_layer, validation_layer)
        self.action_proposer = action_proposer
        self.agent_id = "test_generation_agent"
        self.agent_name = "TestGenerationAgent"

    async def execute_task(self, task_description: str, context: dict[str, Any]) -> AgentResponse:
        """Execute test generation task.

        Args:
            task_description: Description of the task
            context: Must contain 'file_path'

        Returns:
            AgentResponse with test generation recommendations
        """
        file_path = context.get("file_path", "")

        if not file_path or not file_path.endswith(".py"):
            return AgentResponse(
                content="Not a Python file",
                metadata={"file_path": file_path},
            )

        # Check if test file exists
        path = Path(file_path)
        test_file = Path("tests") / path.parent / f"test_{path.name}"

        if test_file.exists():
            return AgentResponse(
                content=f"Test file already exists: {test_file}",
                metadata={"test_file": str(test_file), "exists": True},
            )
        else:
            # Propose test generation
            action_id = self.action_proposer.propose_action(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                action_type=ActionType.TEST_GENERATION,
                description=f"Generate test file for {file_path}",
                rationale=f"No test file found for {path.name}",
                target_path=str(test_file),
                safety_level="medium",
                metadata={"source_file": file_path},
            )

            return AgentResponse(
                content=f"Proposed test generation for {file_path}",
                metadata={
                    "action_id": action_id,
                    "test_file": str(test_file),
                    "exists": False,
                },
            )

    async def handle_event(self, event: RepositoryEvent) -> None:
        """Handle repository events.

        Args:
            event: The repository event to handle
        """
        # Process newly created Python files
        if event.event_type == EventType.FILE_CREATED and event.file_path:
            if event.file_path.endswith(".py") and "test_" not in event.file_path:
                logger.info(f"TestGenerationAgent: Processing {event.file_path}")
                await self.execute_task(
                    f"Check tests for {event.file_path}", {"file_path": event.file_path}
                )


class SecurityPatchAgent(AIAgent):
    """Agent that automatically patches known security vulnerabilities.

    Monitors security advisories and proposes patches for vulnerable code.
    """

    def __init__(self, safety_layer, validation_layer, action_proposer: ActionProposer) -> None:
        """Initialize the security patch agent.

        Args:
            safety_layer: Safety layer for validation
            validation_layer: Validation layer for responses
            action_proposer: Action proposer for proposing changes
        """
        super().__init__(safety_layer, validation_layer)
        self.action_proposer = action_proposer
        self.agent_id = "security_patch_agent"
        self.agent_name = "SecurityPatchAgent"

    async def execute_task(self, task_description: str, context: dict[str, Any]) -> AgentResponse:
        """Execute security patch task.

        Args:
            task_description: Description of the task
            context: Must contain 'file_path' and optionally 'code_content'

        Returns:
            AgentResponse with security patch recommendations
        """
        file_path = context.get("file_path", "")
        code_content = context.get("code_content", "")

        if not code_content and file_path:
            try:
                code_content = Path(file_path).read_text()
            except Exception as e:
                return AgentResponse(
                    content=f"Unable to read file: {e}",
                    metadata={"error": str(e)},
                )

        # Look for known security anti-patterns
        vulnerabilities = []
        fixed_code = code_content

        # Check for eval/exec usage
        if re.search(r"\beval\(", code_content):
            vulnerabilities.append("eval_usage")

        # Check for shell=True in subprocess
        if re.search(r"shell\s*=\s*True", code_content):
            vulnerabilities.append("shell_true_usage")

        # Check for hardcoded secrets
        if re.search(r'(?i)(api[_-]?key|secret[_-]?key)\s*=\s*["\'][^"\']+["\']', code_content):
            vulnerabilities.append("hardcoded_secret")

        if vulnerabilities:
            # Propose security patch
            action_id = self.action_proposer.propose_action(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                action_type=ActionType.SECURITY_PATCH,
                description=f"Patch security vulnerabilities in {file_path}",
                rationale=f"Found vulnerabilities: {', '.join(vulnerabilities)}",
                target_path=file_path,
                content=fixed_code,
                safety_level="critical",
                metadata={"vulnerabilities": vulnerabilities},
            )

            return AgentResponse(
                content=f"Proposed security patch for {len(vulnerabilities)} vulnerabilities",
                metadata={"action_id": action_id, "vulnerabilities": vulnerabilities},
            )
        else:
            return AgentResponse(
                content="No known vulnerabilities detected",
                metadata={"vulnerabilities": []},
            )

    async def handle_event(self, event: RepositoryEvent) -> None:
        """Handle repository events.

        Args:
            event: The repository event to handle
        """
        # Process all Python file modifications
        if event.event_type == EventType.FILE_MODIFIED and event.file_path:
            if event.file_path.endswith(".py"):
                logger.info(f"SecurityPatchAgent: Processing {event.file_path}")
                await self.execute_task(
                    f"Security scan {event.file_path}", {"file_path": event.file_path}
                )


__all__ = [
    "LintingAgent",
    "DependencyUpdateAgent",
    "DocumentationAgent",
    "TestGenerationAgent",
    "SecurityPatchAgent",
]
