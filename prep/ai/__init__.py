"""AI agent framework for repository management.

This package provides a comprehensive framework for managing swarms of AI agents
that can monitor, analyze, and maintain codebases.
"""

from prep.ai import (
    action_system,
    agent_framework,
    agent_runner,
    copilot_agents,
    event_monitor,
    swarm_agents,
    swarm_config,
    swarm_coordinator,
)

__all__ = [
    "agent_framework",
    "agent_runner",
    "copilot_agents",
    "event_monitor",
    "action_system",
    "swarm_coordinator",
    "swarm_agents",
    "swarm_config",
]
