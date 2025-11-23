"""Agent swarm management."""

import asyncio
import logging
from typing import Any

from .agent import Agent, AgentStatus


class AgentSwarm:
    """Manages a collection of agents working together."""

    def __init__(self, name: str = "prep-swarm"):
        """Initialize the agent swarm."""
        self.name = name
        self.agents: dict[str, Agent] = {}
        self.logger = logging.getLogger(f"swarm.{name}")
        self._running = False

    def register_agent(self, agent: Agent) -> None:
        """Register an agent with the swarm."""
        self.agents[agent.agent_id] = agent
        self.logger.info(f"Registered agent: {agent.config.name} (ID: {agent.agent_id})")

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from the swarm."""
        if agent_id in self.agents:
            agent = self.agents.pop(agent_id)
            self.logger.info(f"Unregistered agent: {agent.config.name}")

    async def start_all(self) -> None:
        """Start all registered agents."""
        self.logger.info(f"Starting swarm '{self.name}' with {len(self.agents)} agents")
        self._running = True

        start_tasks = [agent.start() for agent in self.agents.values()]
        await asyncio.gather(*start_tasks, return_exceptions=True)

        self.logger.info(f"All agents started in swarm '{self.name}'")

    async def stop_all(self) -> None:
        """Stop all agents gracefully."""
        self.logger.info(f"Stopping swarm '{self.name}'")
        self._running = False

        stop_tasks = [agent.stop() for agent in self.agents.values()]
        await asyncio.gather(*stop_tasks, return_exceptions=True)

        self.logger.info(f"All agents stopped in swarm '{self.name}'")

    async def health_check_all(self) -> dict[str, Any]:
        """Get health status of all agents."""
        health_tasks = [agent.health_check() for agent in self.agents.values()]
        health_results = await asyncio.gather(*health_tasks, return_exceptions=True)

        return {
            "swarm_name": self.name,
            "total_agents": len(self.agents),
            "agents": health_results,
            "summary": self._get_status_summary(),
        }

    def _get_status_summary(self) -> dict[str, int]:
        """Get summary of agent statuses."""
        summary: dict[str, int] = {}
        for agent in self.agents.values():
            status = agent.status.value
            summary[status] = summary.get(status, 0) + 1
        return summary

    def get_agents_by_type(self, agent_type: str) -> list[Agent]:
        """Get all agents of a specific type."""
        return [agent for agent in self.agents.values() if agent.config.agent_type == agent_type]

    def get_agents_by_status(self, status: AgentStatus) -> list[Agent]:
        """Get all agents with a specific status."""
        return [agent for agent in self.agents.values() if agent.status == status]

    async def restart_failed_agents(self) -> None:
        """Restart all agents in ERROR status."""
        failed_agents = self.get_agents_by_status(AgentStatus.ERROR)

        if not failed_agents:
            return

        self.logger.info(f"Restarting {len(failed_agents)} failed agents")

        for agent in failed_agents:
            try:
                await agent.stop()
                await asyncio.sleep(1)
                await agent.start()
            except Exception as e:
                self.logger.error(f"Failed to restart agent {agent.config.name}: {e}")

    def __len__(self) -> int:
        """Return the number of agents in the swarm."""
        return len(self.agents)

    def __repr__(self) -> str:
        """String representation of the swarm."""
        return f"AgentSwarm(name={self.name}, agents={len(self.agents)})"
