"""
Agent Swarm System for Repository Monitoring and Implementation.

This package provides a comprehensive agent framework for monitoring
and managing all aspects of the Prep repository.
"""

from .core.agent import Agent, AgentStatus
from .core.swarm import AgentSwarm
from .coordinators.swarm_coordinator import SwarmCoordinator

__all__ = [
    "Agent",
    "AgentStatus",
    "AgentSwarm",
    "SwarmCoordinator",
]

__version__ = "1.0.0"
