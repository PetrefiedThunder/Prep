"""Core Agent base class and status definitions."""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class AgentStatus(Enum):
    """Agent operational status."""
    
    INITIALIZING = "initializing"
    ACTIVE = "active"
    IDLE = "idle"
    WORKING = "working"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class AgentMetrics:
    """Agent performance and activity metrics."""
    
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time: float = 0.0
    last_activity: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    """Agent configuration."""
    
    name: str
    agent_type: str
    scope: List[str]
    capabilities: List[str]
    check_interval: int = 60  # seconds
    max_retries: int = 3
    timeout: int = 300  # seconds
    metadata: Dict[str, Any] = field(default_factory=dict)


class Agent(ABC):
    """Base class for all agents in the swarm."""
    
    def __init__(self, config: AgentConfig):
        """Initialize the agent."""
        self.config = config
        self.agent_id = str(uuid4())
        self.status = AgentStatus.INITIALIZING
        self.metrics = AgentMetrics()
        self.logger = logging.getLogger(f"agent.{config.name}")
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the agent."""
        self.logger.info(f"Starting agent {self.config.name} (ID: {self.agent_id})")
        self._running = True
        self.status = AgentStatus.ACTIVE
        self._task = asyncio.create_task(self._run_loop())
    
    async def stop(self) -> None:
        """Stop the agent gracefully."""
        self.logger.info(f"Stopping agent {self.config.name}")
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.status = AgentStatus.STOPPED
    
    async def _run_loop(self) -> None:
        """Main execution loop for the agent."""
        while self._running:
            try:
                self.status = AgentStatus.WORKING
                start_time = time.time()
                
                # Execute agent's monitoring/implementation logic
                await self.execute()
                
                execution_time = time.time() - start_time
                self.metrics.tasks_completed += 1
                self.metrics.total_execution_time += execution_time
                self.metrics.last_activity = datetime.now()
                
                self.status = AgentStatus.IDLE
                await asyncio.sleep(self.config.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in agent {self.config.name}: {e}")
                self.metrics.tasks_failed += 1
                self.metrics.errors.append(str(e))
                self.status = AgentStatus.ERROR
                await asyncio.sleep(self.config.check_interval)
    
    @abstractmethod
    async def execute(self) -> None:
        """Execute the agent's primary task. Must be implemented by subclasses."""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Return agent health status."""
        return {
            "agent_id": self.agent_id,
            "name": self.config.name,
            "type": self.config.agent_type,
            "status": self.status.value,
            "metrics": {
                "tasks_completed": self.metrics.tasks_completed,
                "tasks_failed": self.metrics.tasks_failed,
                "avg_execution_time": (
                    self.metrics.total_execution_time / self.metrics.tasks_completed
                    if self.metrics.tasks_completed > 0
                    else 0
                ),
                "last_activity": (
                    self.metrics.last_activity.isoformat()
                    if self.metrics.last_activity
                    else None
                ),
                "recent_errors": self.metrics.errors[-5:],
            },
        }
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"Agent(name={self.config.name}, id={self.agent_id}, status={self.status.value})"
