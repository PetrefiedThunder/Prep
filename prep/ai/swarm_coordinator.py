"""Swarm coordinator for managing multiple agents.

This module provides the core orchestration layer for a swarm of agents that can
monitor repository events, propose changes, and coordinate their actions.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from prep.ai.agent_framework import AIAgent, AgentResponse, SafeAgentResponse

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Status of an agent in the swarm."""

    IDLE = "idle"
    MONITORING = "monitoring"
    PROCESSING = "processing"
    PROPOSING = "proposing"
    EXECUTING = "executing"
    ERROR = "error"
    PAUSED = "paused"


@dataclass
class AgentInfo:
    """Information about an agent in the swarm."""

    agent_id: str
    agent_name: str
    agent_type: str
    agent: AIAgent
    status: AgentStatus = AgentStatus.IDLE
    capabilities: list[str] = field(default_factory=list)
    monitored_paths: list[str] = field(default_factory=list)
    last_activity: datetime | None = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SwarmTask:
    """A task to be executed by the swarm."""

    task_id: str
    task_type: str
    description: str
    context: dict[str, Any]
    priority: int = 5  # 1=highest, 10=lowest
    assigned_agent_id: str | None = None
    status: str = "pending"  # pending, assigned, in_progress, completed, failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    result: AgentResponse | None = None
    error: str | None = None


@dataclass
class SwarmMetrics:
    """Metrics for the swarm."""

    total_agents: int = 0
    active_agents: int = 0
    idle_agents: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    uptime_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentRegistry:
    """Registry for managing agents in the swarm."""

    def __init__(self) -> None:
        """Initialize the agent registry."""
        self._agents: dict[str, AgentInfo] = {}
        self._agents_by_type: dict[str, list[str]] = {}
        self._agents_by_capability: dict[str, list[str]] = {}

    def register(
        self,
        agent: AIAgent,
        agent_name: str,
        agent_type: str,
        capabilities: list[str] | None = None,
        monitored_paths: list[str] | None = None,
    ) -> str:
        """Register an agent in the swarm.

        Args:
            agent: The agent instance to register
            agent_name: Human-readable name for the agent
            agent_type: Type/category of the agent
            capabilities: List of capabilities the agent has
            monitored_paths: List of file paths the agent monitors

        Returns:
            The unique agent_id assigned to this agent
        """
        agent_id = str(uuid4())
        capabilities = capabilities or []
        monitored_paths = monitored_paths or []

        agent_info = AgentInfo(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type=agent_type,
            agent=agent,
            capabilities=capabilities,
            monitored_paths=monitored_paths,
        )

        self._agents[agent_id] = agent_info
        
        # Index by type
        if agent_type not in self._agents_by_type:
            self._agents_by_type[agent_type] = []
        self._agents_by_type[agent_type].append(agent_id)

        # Index by capabilities
        for capability in capabilities:
            if capability not in self._agents_by_capability:
                self._agents_by_capability[capability] = []
            self._agents_by_capability[capability].append(agent_id)

        logger.info(f"Registered agent {agent_name} ({agent_id}) with type {agent_type}")
        return agent_id

    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent from the swarm.

        Args:
            agent_id: The unique identifier of the agent to unregister

        Returns:
            True if agent was unregistered, False if not found
        """
        if agent_id not in self._agents:
            return False

        agent_info = self._agents[agent_id]

        # Remove from type index
        if agent_info.agent_type in self._agents_by_type:
            self._agents_by_type[agent_info.agent_type].remove(agent_id)

        # Remove from capability index
        for capability in agent_info.capabilities:
            if capability in self._agents_by_capability:
                self._agents_by_capability[capability].remove(agent_id)

        del self._agents[agent_id]
        logger.info(f"Unregistered agent {agent_info.agent_name} ({agent_id})")
        return True

    def get_agent(self, agent_id: str) -> AgentInfo | None:
        """Get agent info by ID."""
        return self._agents.get(agent_id)

    def get_agents_by_type(self, agent_type: str) -> list[AgentInfo]:
        """Get all agents of a specific type."""
        agent_ids = self._agents_by_type.get(agent_type, [])
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_agents_by_capability(self, capability: str) -> list[AgentInfo]:
        """Get all agents with a specific capability."""
        agent_ids = self._agents_by_capability.get(capability, [])
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_all_agents(self) -> list[AgentInfo]:
        """Get all registered agents."""
        return list(self._agents.values())

    def get_agents_by_status(self, status: AgentStatus) -> list[AgentInfo]:
        """Get all agents with a specific status."""
        return [info for info in self._agents.values() if info.status == status]

    def update_agent_status(self, agent_id: str, status: AgentStatus) -> None:
        """Update the status of an agent."""
        if agent_id in self._agents:
            self._agents[agent_id].status = status
            self._agents[agent_id].last_activity = datetime.utcnow()


class SwarmCoordinator:
    """Coordinator for managing a swarm of agents.

    The SwarmCoordinator manages the lifecycle of multiple agents, routes tasks
    to appropriate agents, and coordinates their activities.
    """

    def __init__(self, max_concurrent_tasks: int = 10) -> None:
        """Initialize the swarm coordinator.

        Args:
            max_concurrent_tasks: Maximum number of tasks to execute concurrently
        """
        self.registry = AgentRegistry()
        self.max_concurrent_tasks = max_concurrent_tasks
        self._task_queue: asyncio.Queue[SwarmTask] = asyncio.Queue()
        self._active_tasks: dict[str, SwarmTask] = {}
        self._completed_tasks: list[SwarmTask] = []
        self._running = False
        self._start_time: datetime | None = None
        self._worker_tasks: list[asyncio.Task] = []

    def register_agent(
        self,
        agent: AIAgent,
        agent_name: str,
        agent_type: str,
        capabilities: list[str] | None = None,
        monitored_paths: list[str] | None = None,
    ) -> str:
        """Register an agent with the coordinator.

        Args:
            agent: The agent instance to register
            agent_name: Human-readable name for the agent
            agent_type: Type/category of the agent
            capabilities: List of capabilities the agent has
            monitored_paths: List of file paths the agent monitors

        Returns:
            The unique agent_id assigned to this agent
        """
        return self.registry.register(agent, agent_name, agent_type, capabilities, monitored_paths)

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the coordinator.

        Args:
            agent_id: The unique identifier of the agent

        Returns:
            True if agent was unregistered, False if not found
        """
        return self.registry.unregister(agent_id)

    async def submit_task(
        self,
        task_type: str,
        description: str,
        context: dict[str, Any],
        priority: int = 5,
    ) -> str:
        """Submit a task to the swarm.

        Args:
            task_type: Type of task (e.g., "security_scan", "lint_fix")
            description: Human-readable description of the task
            context: Context information for the task
            priority: Priority level (1=highest, 10=lowest)

        Returns:
            The unique task_id for tracking the task
        """
        task = SwarmTask(
            task_id=str(uuid4()),
            task_type=task_type,
            description=description,
            context=context,
            priority=priority,
        )

        await self._task_queue.put(task)
        logger.info(f"Submitted task {task.task_id}: {description}")
        return task.task_id

    def _select_agent_for_task(self, task: SwarmTask) -> AgentInfo | None:
        """Select the best agent for a given task.

        Args:
            task: The task to assign

        Returns:
            The selected agent info, or None if no suitable agent found
        """
        # Try to find agents by capability matching the task type
        candidates = self.registry.get_agents_by_capability(task.task_type)

        # If no capability match, try type match
        if not candidates:
            candidates = self.registry.get_agents_by_type(task.task_type)

        # If still no match, try any idle agent
        if not candidates:
            candidates = self.registry.get_agents_by_status(AgentStatus.IDLE)

        # Filter to only idle agents
        idle_candidates = [c for c in candidates if c.status == AgentStatus.IDLE]

        if not idle_candidates:
            return None

        # Select the agent with the most completed tasks (most experienced)
        return max(idle_candidates, key=lambda a: a.tasks_completed)

    async def _execute_task(self, task: SwarmTask, agent_info: AgentInfo) -> None:
        """Execute a task using the assigned agent.

        Args:
            task: The task to execute
            agent_info: Information about the agent executing the task
        """
        task.assigned_agent_id = agent_info.agent_id
        task.status = "in_progress"
        self.registry.update_agent_status(agent_info.agent_id, AgentStatus.PROCESSING)

        try:
            # Execute the task using the agent's safe_execute method
            result = await agent_info.agent.safe_execute(task.description, task.context)

            if result.error:
                task.status = "failed"
                task.error = result.error
                agent_info.tasks_failed += 1
                logger.warning(f"Task {task.task_id} failed: {result.error}")
            else:
                task.status = "completed"
                task.result = result.content
                agent_info.tasks_completed += 1
                logger.info(f"Task {task.task_id} completed by {agent_info.agent_name}")

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            agent_info.tasks_failed += 1
            logger.error(f"Task {task.task_id} failed with exception: {e}")

        finally:
            task.completed_at = datetime.utcnow()
            self.registry.update_agent_status(agent_info.agent_id, AgentStatus.IDLE)
            self._completed_tasks.append(task)
            if task.task_id in self._active_tasks:
                del self._active_tasks[task.task_id]

    async def _worker(self) -> None:
        """Worker coroutine that processes tasks from the queue."""
        while self._running:
            try:
                # Get task from queue with timeout
                try:
                    task = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Select an agent for the task
                agent_info = self._select_agent_for_task(task)

                if agent_info is None:
                    # No suitable agent available, put task back in queue
                    await self._task_queue.put(task)
                    await asyncio.sleep(0.5)  # Wait a bit before retrying
                    continue

                # Track active task
                self._active_tasks[task.task_id] = task

                # Execute the task
                await self._execute_task(task, agent_info)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")

    async def start(self) -> None:
        """Start the swarm coordinator."""
        if self._running:
            logger.warning("Swarm coordinator already running")
            return

        self._running = True
        self._start_time = datetime.utcnow()

        # Start worker tasks
        for _ in range(self.max_concurrent_tasks):
            task = asyncio.create_task(self._worker())
            self._worker_tasks.append(task)

        logger.info(f"Swarm coordinator started with {self.max_concurrent_tasks} workers")

    async def stop(self) -> None:
        """Stop the swarm coordinator."""
        if not self._running:
            return

        self._running = False

        # Cancel all worker tasks
        for task in self._worker_tasks:
            task.cancel()

        # Wait for all workers to finish
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()

        logger.info("Swarm coordinator stopped")

    def get_metrics(self) -> SwarmMetrics:
        """Get current metrics for the swarm.

        Returns:
            SwarmMetrics object with current statistics
        """
        all_agents = self.registry.get_all_agents()

        total_completed = sum(a.tasks_completed for a in all_agents)
        total_failed = sum(a.tasks_failed for a in all_agents)

        uptime = 0.0
        if self._start_time:
            uptime = (datetime.utcnow() - self._start_time).total_seconds()

        active_count = len(self.registry.get_agents_by_status(AgentStatus.PROCESSING))
        idle_count = len(self.registry.get_agents_by_status(AgentStatus.IDLE))

        return SwarmMetrics(
            total_agents=len(all_agents),
            active_agents=active_count,
            idle_agents=idle_count,
            total_tasks_completed=total_completed,
            total_tasks_failed=total_failed,
            uptime_seconds=uptime,
            metadata={
                "active_tasks": len(self._active_tasks),
                "queued_tasks": self._task_queue.qsize(),
                "completed_tasks": len(self._completed_tasks),
            },
        )

    def get_task_status(self, task_id: str) -> SwarmTask | None:
        """Get the status of a task.

        Args:
            task_id: The unique identifier of the task

        Returns:
            The SwarmTask object, or None if not found
        """
        # Check active tasks
        if task_id in self._active_tasks:
            return self._active_tasks[task_id]

        # Check completed tasks
        for task in self._completed_tasks:
            if task.task_id == task_id:
                return task

        return None


__all__ = [
    "SwarmCoordinator",
    "AgentRegistry",
    "AgentInfo",
    "AgentStatus",
    "SwarmTask",
    "SwarmMetrics",
]
