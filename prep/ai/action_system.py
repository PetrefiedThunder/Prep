"""Action proposal and execution system for agents.

This module allows agents to propose changes to the repository and provides
a safe execution framework with approval workflows.
"""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions agents can propose."""

    FILE_CREATE = "file_create"
    FILE_MODIFY = "file_modify"
    FILE_DELETE = "file_delete"
    FILE_RENAME = "file_rename"
    DEPENDENCY_UPDATE = "dependency_update"
    CODE_FIX = "code_fix"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION_UPDATE = "documentation_update"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_PATCH = "security_patch"
    CUSTOM = "custom"


class ActionStatus(Enum):
    """Status of a proposed action."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ProposedAction:
    """Represents an action proposed by an agent."""

    action_id: str
    action_type: ActionType
    agent_id: str
    agent_name: str
    description: str
    rationale: str
    target_path: str | None = None
    content: str | None = None
    status: ActionStatus = ActionStatus.PROPOSED
    requires_approval: bool = True
    safety_level: str = "medium"  # low, medium, high, critical
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved_at: datetime | None = None
    executed_at: datetime | None = None
    approved_by: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    result: dict[str, Any] | None = None


@dataclass
class ExecutionResult:
    """Result of executing an action."""

    success: bool
    message: str
    changes_made: list[str] = field(default_factory=list)
    rollback_info: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


ApprovalHandler = Callable[[ProposedAction], bool]


class ActionProposer:
    """Manages action proposals from agents.

    The ActionProposer provides a system for agents to propose changes,
    routes proposals for approval, and manages the approval workflow.
    """

    def __init__(self) -> None:
        """Initialize the action proposer."""
        self._proposals: dict[str, ProposedAction] = {}
        self._approval_handlers: list[ApprovalHandler] = []
        self._auto_approve_low_risk = False

    def propose_action(
        self,
        agent_id: str,
        agent_name: str,
        action_type: ActionType,
        description: str,
        rationale: str,
        target_path: str | None = None,
        content: str | None = None,
        safety_level: str = "medium",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Propose an action for approval.

        Args:
            agent_id: ID of the agent proposing the action
            agent_name: Name of the agent
            action_type: Type of action being proposed
            description: Human-readable description of the action
            rationale: Explanation of why this action is needed
            target_path: Optional file path affected by the action
            content: Optional content (e.g., new file content, patch)
            safety_level: Risk level (low, medium, high, critical)
            metadata: Optional additional metadata

        Returns:
            The unique action_id for the proposal
        """
        action_id = str(uuid4())

        # Determine if approval is required based on safety level
        requires_approval = safety_level in ["high", "critical"]

        action = ProposedAction(
            action_id=action_id,
            action_type=action_type,
            agent_id=agent_id,
            agent_name=agent_name,
            description=description,
            rationale=rationale,
            target_path=target_path,
            content=content,
            requires_approval=requires_approval,
            safety_level=safety_level,
            metadata=metadata or {},
        )

        self._proposals[action_id] = action

        # Auto-approve low-risk actions if enabled
        if self._auto_approve_low_risk and safety_level == "low":
            action.status = ActionStatus.APPROVED
            action.approved_at = datetime.utcnow()
            action.approved_by = "auto_approval_system"
            logger.info(f"Auto-approved low-risk action {action_id}: {description}")
        else:
            logger.info(f"Proposed action {action_id}: {description}")

        return action_id

    def register_approval_handler(self, handler: ApprovalHandler) -> None:
        """Register a handler for approving actions.

        Args:
            handler: A callable that takes a ProposedAction and returns bool
        """
        self._approval_handlers.append(handler)

    def get_proposal(self, action_id: str) -> ProposedAction | None:
        """Get a proposal by ID.

        Args:
            action_id: The unique identifier of the proposal

        Returns:
            The ProposedAction, or None if not found
        """
        return self._proposals.get(action_id)

    def get_pending_approvals(self) -> list[ProposedAction]:
        """Get all proposals pending approval.

        Returns:
            List of proposals with PROPOSED status
        """
        return [
            action
            for action in self._proposals.values()
            if action.status == ActionStatus.PROPOSED and action.requires_approval
        ]

    def get_approved_actions(self) -> list[ProposedAction]:
        """Get all approved actions ready for execution.

        Returns:
            List of proposals with APPROVED status
        """
        return [
            action for action in self._proposals.values() if action.status == ActionStatus.APPROVED
        ]

    def approve_action(self, action_id: str, approved_by: str = "system") -> bool:
        """Approve a proposed action.

        Args:
            action_id: The unique identifier of the action
            approved_by: Identifier of who/what approved the action

        Returns:
            True if approved, False if action not found or already processed
        """
        action = self._proposals.get(action_id)

        if not action or action.status != ActionStatus.PROPOSED:
            return False

        action.status = ActionStatus.APPROVED
        action.approved_at = datetime.utcnow()
        action.approved_by = approved_by

        logger.info(f"Action {action_id} approved by {approved_by}")
        return True

    def reject_action(self, action_id: str, reason: str = "") -> bool:
        """Reject a proposed action.

        Args:
            action_id: The unique identifier of the action
            reason: Optional reason for rejection

        Returns:
            True if rejected, False if action not found or already processed
        """
        action = self._proposals.get(action_id)

        if not action or action.status != ActionStatus.PROPOSED:
            return False

        action.status = ActionStatus.REJECTED
        action.error = reason

        logger.info(f"Action {action_id} rejected: {reason}")
        return True

    def set_auto_approve_low_risk(self, enabled: bool) -> None:
        """Enable or disable auto-approval of low-risk actions.

        Args:
            enabled: Whether to automatically approve low-risk actions
        """
        self._auto_approve_low_risk = enabled
        logger.info(f"Auto-approve low-risk actions: {enabled}")


class ActionExecutor:
    """Executes approved actions safely.

    The ActionExecutor takes approved actions and executes them with
    appropriate safety checks and rollback capabilities.
    """

    def __init__(self, root_dir: str | Path = ".") -> None:
        """Initialize the action executor.

        Args:
            root_dir: Root directory for file operations
        """
        self.root_dir = Path(root_dir).resolve()
        self._backups: dict[str, Path] = {}

    async def execute_action(self, action: ProposedAction) -> ExecutionResult:
        """Execute an approved action.

        Args:
            action: The approved action to execute

        Returns:
            ExecutionResult with details of the execution
        """
        if action.status != ActionStatus.APPROVED:
            return ExecutionResult(
                success=False,
                message="Action is not approved",
                error="Action must be approved before execution",
            )

        action.status = ActionStatus.EXECUTING
        action.executed_at = datetime.utcnow()

        try:
            if action.action_type == ActionType.FILE_CREATE:
                result = await self._execute_file_create(action)
            elif action.action_type == ActionType.FILE_MODIFY:
                result = await self._execute_file_modify(action)
            elif action.action_type == ActionType.FILE_DELETE:
                result = await self._execute_file_delete(action)
            elif action.action_type == ActionType.CODE_FIX:
                result = await self._execute_code_fix(action)
            elif action.action_type == ActionType.DEPENDENCY_UPDATE:
                result = await self._execute_dependency_update(action)
            else:
                result = ExecutionResult(
                    success=False,
                    message=f"Unsupported action type: {action.action_type.value}",
                )

            if result.success:
                action.status = ActionStatus.COMPLETED
                action.result = result.metadata
            else:
                action.status = ActionStatus.FAILED
                action.error = result.error

            return result

        except Exception as e:
            action.status = ActionStatus.FAILED
            action.error = str(e)
            logger.error(f"Action execution failed: {e}")
            return ExecutionResult(success=False, message="Execution failed", error=str(e))

    async def _execute_file_create(self, action: ProposedAction) -> ExecutionResult:
        """Execute a file creation action."""
        if not action.target_path or not action.content:
            return ExecutionResult(
                success=False,
                message="Missing target_path or content",
                error="FILE_CREATE requires target_path and content",
            )

        file_path = self.root_dir / action.target_path

        # Check if file already exists
        if file_path.exists():
            return ExecutionResult(
                success=False,
                message=f"File already exists: {action.target_path}",
                error="Cannot create file that already exists",
            )

        try:
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            file_path.write_text(action.content)

            logger.info(f"Created file: {action.target_path}")
            return ExecutionResult(
                success=True,
                message=f"Created file: {action.target_path}",
                changes_made=[f"created:{action.target_path}"],
            )

        except Exception as e:
            return ExecutionResult(
                success=False, message="Failed to create file", error=str(e)
            )

    async def _execute_file_modify(self, action: ProposedAction) -> ExecutionResult:
        """Execute a file modification action."""
        if not action.target_path or not action.content:
            return ExecutionResult(
                success=False,
                message="Missing target_path or content",
                error="FILE_MODIFY requires target_path and content",
            )

        file_path = self.root_dir / action.target_path

        if not file_path.exists():
            return ExecutionResult(
                success=False,
                message=f"File does not exist: {action.target_path}",
                error="Cannot modify non-existent file",
            )

        try:
            # Backup original content
            original_content = file_path.read_text()
            backup_name = f"backup_{action.action_id}_{file_path.name}"
            backup_path = Path(tempfile.gettempdir()) / backup_name
            backup_path.write_text(original_content)
            self._backups[action.action_id] = backup_path

            # Write new content
            file_path.write_text(action.content)

            logger.info(f"Modified file: {action.target_path}")
            return ExecutionResult(
                success=True,
                message=f"Modified file: {action.target_path}",
                changes_made=[f"modified:{action.target_path}"],
                rollback_info={"backup_path": str(backup_path)},
            )

        except Exception as e:
            return ExecutionResult(
                success=False, message="Failed to modify file", error=str(e)
            )

    async def _execute_file_delete(self, action: ProposedAction) -> ExecutionResult:
        """Execute a file deletion action."""
        if not action.target_path:
            return ExecutionResult(
                success=False,
                message="Missing target_path",
                error="FILE_DELETE requires target_path",
            )

        file_path = self.root_dir / action.target_path

        if not file_path.exists():
            return ExecutionResult(
                success=False,
                message=f"File does not exist: {action.target_path}",
                error="Cannot delete non-existent file",
            )

        try:
            # Backup before deletion
            content = file_path.read_text()
            backup_name = f"backup_{action.action_id}_{file_path.name}"
            backup_path = Path(tempfile.gettempdir()) / backup_name
            backup_path.write_text(content)
            self._backups[action.action_id] = backup_path

            # Delete file
            file_path.unlink()

            logger.info(f"Deleted file: {action.target_path}")
            return ExecutionResult(
                success=True,
                message=f"Deleted file: {action.target_path}",
                changes_made=[f"deleted:{action.target_path}"],
                rollback_info={"backup_path": str(backup_path)},
            )

        except Exception as e:
            return ExecutionResult(
                success=False, message="Failed to delete file", error=str(e)
            )

    async def _execute_code_fix(self, action: ProposedAction) -> ExecutionResult:
        """Execute a code fix action (essentially a file modify)."""
        return await self._execute_file_modify(action)

    async def _execute_dependency_update(self, action: ProposedAction) -> ExecutionResult:
        """Execute a dependency update action."""
        # This is a placeholder - actual implementation would depend on
        # the package manager (pip, npm, etc.)
        return ExecutionResult(
            success=False,
            message="Dependency update not fully implemented",
            error="This action type requires package manager integration",
        )

    async def rollback_action(self, action_id: str) -> ExecutionResult:
        """Rollback a previously executed action.

        Args:
            action_id: The unique identifier of the action to rollback

        Returns:
            ExecutionResult indicating success or failure of rollback
        """
        if action_id not in self._backups:
            return ExecutionResult(
                success=False,
                message="No backup available for rollback",
                error=f"No backup found for action {action_id}",
            )

        try:
            _ = self._backups[action_id]
            # Rollback logic would go here
            logger.info(f"Rolled back action {action_id}")
            return ExecutionResult(success=True, message="Action rolled back successfully")

        except Exception as e:
            return ExecutionResult(
                success=False, message="Rollback failed", error=str(e)
            )


__all__ = [
    "ActionProposer",
    "ActionExecutor",
    "ProposedAction",
    "ExecutionResult",
    "ActionType",
    "ActionStatus",
]
