"""AI agent framework with safety and validation layers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class SafetyResult:
    """Result of a safety layer evaluation."""

    approved: bool
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of validating an agent response."""

    valid: bool
    issues: Optional[str] = None
    requires_review: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Primary content returned by an AI agent."""

    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SafeAgentResponse:
    """Response wrapper that captures safety and validation status."""

    content: Optional[AgentResponse] = None
    safety_checks_passed: bool = False
    validation_checks_passed: bool = False
    requires_human_review: bool = False
    error: Optional[str] = None


class SafetyLayer:
    """Minimal safety layer to demonstrate policy enforcement."""

    async def validate_task(self, task: str, context: Dict[str, Any]) -> SafetyResult:
        if "restricted" in task.lower():
            return SafetyResult(approved=False, reason="Task references restricted content")
        return SafetyResult(approved=True, metadata={"context_keys": list(context.keys())})


class ValidationLayer:
    """Validates agent responses before surfacing to end users."""

    async def validate_response(self, response: AgentResponse, task: str) -> ValidationResult:
        if not response.content:
            return ValidationResult(valid=False, issues="Empty response content")
        if "placeholder" in response.content.lower():
            return ValidationResult(valid=False, issues="Placeholder content detected", requires_review=True)
        return ValidationResult(valid=True)


class LLMClient:
    """Simplified LLM client placeholder."""

    async def generate_response(self, prompt: str, context: Dict[str, Any]) -> AgentResponse:
        enriched_context = ", ".join(f"{k}={v}" for k, v in sorted(context.items()))
        content = f"Task: {prompt}. Context: {enriched_context}".strip()
        return AgentResponse(content=content, metadata={"model": "prep-synthetic-llm"})


class AIAgent(ABC):
    def __init__(self, safety_layer: SafetyLayer, validation_layer: ValidationLayer) -> None:
        self.safety_layer = safety_layer
        self.validation_layer = validation_layer
        self.llm_client = LLMClient()

    @abstractmethod
    async def execute_task(self, task_description: str, context: Dict[str, Any]) -> AgentResponse:
        """Execute a domain-specific task and return an agent response."""
        raise NotImplementedError

    async def safe_execute(self, task: str, context: Dict[str, Any]) -> SafeAgentResponse:
        """Execute an agent task with safety and validation gates applied."""

        safety_result = await self.safety_layer.validate_task(task, context)
        if not safety_result.approved:
            return SafeAgentResponse(error=f"Task rejected: {safety_result.reason}")

        raw_response = await self.execute_task(task, context)

        validation_result = await self.validation_layer.validate_response(raw_response, task)
        if not validation_result.valid:
            return SafeAgentResponse(
                error=f"Response invalid: {validation_result.issues}",
                content=raw_response,
                safety_checks_passed=True,
                requires_human_review=validation_result.requires_review,
            )

        return SafeAgentResponse(
            content=raw_response,
            safety_checks_passed=True,
            validation_checks_passed=True,
            requires_human_review=validation_result.requires_review,
        )


class PrepChefAgent(AIAgent):
    """Commercial kitchen compliance assistant."""

    async def execute_task(self, task_description: str, context: Dict[str, Any]) -> AgentResponse:
        domain_context = {"module": "kitchen_compliance", **context}
        return await self.llm_client.generate_response(task_description, domain_context)


class AutoProjectionBot(AIAgent):
    """Financial forecasting and GAAP compliance assistant."""

    async def execute_task(self, task_description: str, context: Dict[str, Any]) -> AgentResponse:
        financial_context = {"module": "financial_compliance", **context}
        return await self.llm_client.generate_response(task_description, financial_context)


__all__ = [
    "AIAgent",
    "AgentResponse",
    "SafeAgentResponse",
    "SafetyLayer",
    "ValidationLayer",
    "LLMClient",
    "PrepChefAgent",
    "AutoProjectionBot",
]
