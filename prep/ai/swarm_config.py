"""Swarm configuration and setup utilities.

This module provides utilities for configuring and deploying agent swarms
from YAML configuration files.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from prep.ai.action_system import ActionProposer
from prep.ai.agent_framework import SafetyLayer, ValidationLayer
from prep.ai.event_monitor import EventMonitor, EventType
from prep.ai.swarm_agents import (
    DependencyUpdateAgent,
    DocumentationAgent,
    LintingAgent,
    SecurityPatchAgent,
    TestGenerationAgent,
)
from prep.ai.swarm_coordinator import SwarmCoordinator

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for a single agent."""

    name: str
    type: str
    enabled: bool = True
    capabilities: list[str] | None = None
    monitored_paths: list[str] | None = None
    config: dict[str, Any] | None = None


@dataclass
class SwarmConfig:
    """Configuration for the entire swarm."""

    name: str
    max_concurrent_tasks: int = 10
    enable_event_monitoring: bool = True
    monitor_poll_interval: float = 2.0
    auto_approve_low_risk: bool = False
    agents: list[AgentConfig] | None = None
    root_dir: str = "."


class SwarmFactory:
    """Factory for creating and configuring agent swarms."""

    @staticmethod
    def load_config(config_path: str | Path) -> SwarmConfig:
        """Load swarm configuration from a YAML file.

        Args:
            config_path: Path to the YAML configuration file

        Returns:
            SwarmConfig object
        """
        with open(config_path) as f:
            data = yaml.safe_load(f)

        agents = []
        for agent_data in data.get("agents", []):
            agent_config = AgentConfig(
                name=agent_data["name"],
                type=agent_data["type"],
                enabled=agent_data.get("enabled", True),
                capabilities=agent_data.get("capabilities"),
                monitored_paths=agent_data.get("monitored_paths"),
                config=agent_data.get("config"),
            )
            agents.append(agent_config)

        return SwarmConfig(
            name=data.get("name", "default_swarm"),
            max_concurrent_tasks=data.get("max_concurrent_tasks", 10),
            enable_event_monitoring=data.get("enable_event_monitoring", True),
            monitor_poll_interval=data.get("monitor_poll_interval", 2.0),
            auto_approve_low_risk=data.get("auto_approve_low_risk", False),
            agents=agents,
            root_dir=data.get("root_dir", "."),
        )

    @staticmethod
    def create_swarm(config: SwarmConfig) -> tuple[SwarmCoordinator, EventMonitor, ActionProposer]:
        """Create a swarm from configuration.

        Args:
            config: SwarmConfig object

        Returns:
            Tuple of (coordinator, event_monitor, action_proposer)
        """
        # Create core components
        coordinator = SwarmCoordinator(max_concurrent_tasks=config.max_concurrent_tasks)
        event_monitor = EventMonitor(root_dir=config.root_dir)
        action_proposer = ActionProposer()
        action_proposer.set_auto_approve_low_risk(config.auto_approve_low_risk)

        # Create safety and validation layers
        safety_layer = SafetyLayer()
        validation_layer = ValidationLayer()

        # Create agents based on configuration
        if config.agents:
            for agent_config in config.agents:
                if not agent_config.enabled:
                    continue

                agent = SwarmFactory._create_agent(
                    agent_config, safety_layer, validation_layer, action_proposer
                )

                if agent:
                    agent_id = coordinator.register_agent(
                        agent=agent,
                        agent_name=agent_config.name,
                        agent_type=agent_config.type,
                        capabilities=agent_config.capabilities,
                        monitored_paths=agent_config.monitored_paths,
                    )

                    # Register event handler if agent has one
                    if hasattr(agent, "handle_event"):
                        # Register for relevant event types based on capabilities
                        event_types = SwarmFactory._get_event_types_for_agent(agent_config)
                        for event_type in event_types:
                            event_monitor.register_handler(event_type, agent.handle_event)

                    logger.info(f"Created agent: {agent_config.name} ({agent_id})")

        return coordinator, event_monitor, action_proposer

    @staticmethod
    def _create_agent(
        config: AgentConfig,
        safety_layer: SafetyLayer,
        validation_layer: ValidationLayer,
        action_proposer: ActionProposer,
    ):
        """Create an agent instance based on type.

        Args:
            config: Agent configuration
            safety_layer: Safety layer instance
            validation_layer: Validation layer instance
            action_proposer: Action proposer instance

        Returns:
            Agent instance or None if type is unknown
        """
        agent_map = {
            "linting": LintingAgent,
            "dependency_update": DependencyUpdateAgent,
            "documentation": DocumentationAgent,
            "test_generation": TestGenerationAgent,
            "security_patch": SecurityPatchAgent,
        }

        agent_class = agent_map.get(config.type)
        if agent_class:
            return agent_class(safety_layer, validation_layer, action_proposer)
        else:
            logger.warning(f"Unknown agent type: {config.type}")
            return None

    @staticmethod
    def _get_event_types_for_agent(config: AgentConfig) -> list[EventType]:
        """Determine which event types an agent should handle.

        Args:
            config: Agent configuration

        Returns:
            List of EventType values
        """
        # Map agent types to event types they should monitor
        type_map = {
            "linting": [EventType.FILE_MODIFIED],
            "dependency_update": [EventType.FILE_MODIFIED],
            "documentation": [EventType.FILE_CREATED, EventType.FILE_MODIFIED],
            "test_generation": [EventType.FILE_CREATED],
            "security_patch": [EventType.FILE_MODIFIED],
        }

        return type_map.get(config.type, [])


def create_default_config(output_path: str | Path = "swarm_config.yaml") -> None:
    """Create a default swarm configuration file.

    Args:
        output_path: Path where the config file should be created
    """
    default_config = {
        "name": "prep_agent_swarm",
        "max_concurrent_tasks": 10,
        "enable_event_monitoring": True,
        "monitor_poll_interval": 2.0,
        "auto_approve_low_risk": False,
        "root_dir": ".",
        "agents": [
            {
                "name": "linting_agent_01",
                "type": "linting",
                "enabled": True,
                "capabilities": ["code_fix", "linting"],
                "monitored_paths": ["prep/**/*.py", "tests/**/*.py"],
            },
            {
                "name": "security_agent_01",
                "type": "security_patch",
                "enabled": True,
                "capabilities": ["security_scan", "security_patch"],
                "monitored_paths": ["prep/**/*.py"],
            },
            {
                "name": "doc_agent_01",
                "type": "documentation",
                "enabled": True,
                "capabilities": ["documentation"],
                "monitored_paths": ["prep/**/*.py"],
            },
            {
                "name": "test_gen_agent_01",
                "type": "test_generation",
                "enabled": True,
                "capabilities": ["test_generation"],
                "monitored_paths": ["prep/**/*.py"],
            },
            {
                "name": "dependency_agent_01",
                "type": "dependency_update",
                "enabled": True,
                "capabilities": ["dependency_update"],
                "monitored_paths": ["requirements.txt", "package.json"],
            },
        ],
    }

    with open(output_path, "w") as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Created default configuration at {output_path}")


__all__ = [
    "SwarmConfig",
    "AgentConfig",
    "SwarmFactory",
    "create_default_config",
]
