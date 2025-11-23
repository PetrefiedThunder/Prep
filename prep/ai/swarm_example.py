#!/usr/bin/env python3
"""Example usage of the agent swarm system.

This script demonstrates how to programmatically create and run an agent swarm.
"""

import asyncio
import logging

from prep.ai.action_system import ActionProposer
from prep.ai.agent_framework import SafetyLayer, ValidationLayer
from prep.ai.swarm_agents import (
    DependencyUpdateAgent,
    DocumentationAgent,
    LintingAgent,
    SecurityPatchAgent,
)
from prep.ai.swarm_coordinator import SwarmCoordinator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def main():
    """Run a simple swarm example."""
    logger.info("Creating agent swarm...")

    # Initialize components
    coordinator = SwarmCoordinator(max_concurrent_tasks=5)
    action_proposer = ActionProposer()
    # ActionExecutor can be used for executing approved actions
    # action_executor = ActionExecutor()

    # Create shared layers
    safety_layer = SafetyLayer()
    validation_layer = ValidationLayer()

    # Create and register agents
    agents = [
        LintingAgent(safety_layer, validation_layer, action_proposer),
        SecurityPatchAgent(safety_layer, validation_layer, action_proposer),
        DocumentationAgent(safety_layer, validation_layer, action_proposer),
        DependencyUpdateAgent(safety_layer, validation_layer, action_proposer),
    ]

    for i, agent in enumerate(agents):
        agent_type = agent.__class__.__name__.replace("Agent", "").lower()
        agent_id = coordinator.register_agent(
            agent=agent,
            agent_name=f"{agent_type}_{i + 1:02d}",
            agent_type=agent_type,
            capabilities=[agent_type],
        )
        logger.info(f"Registered: {agent_type}_{i + 1:02d} ({agent_id})")

    # Start coordinator
    await coordinator.start()
    logger.info("Swarm started")

    # Submit some example tasks
    tasks = [
        {
            "task_type": "linting",
            "description": "Lint Python files",
            "context": {
                "file_path": "prep/ai/swarm_coordinator.py",
                "code_content": "def foo():  \n    pass\n",
            },
        },
        {
            "task_type": "security",
            "description": "Security scan",
            "context": {
                "file_path": "prep/api/auth.py",
                "code_content": 'api_key = "test123"\n',
            },
        },
    ]

    for task in tasks:
        task_id = await coordinator.submit_task(**task)
        logger.info(f"Submitted task: {task_id}")

    # Run for a bit
    logger.info("Processing tasks for 5 seconds...")
    await asyncio.sleep(5)

    # Check metrics
    metrics = coordinator.get_metrics()
    logger.info("=" * 60)
    logger.info("SWARM METRICS")
    logger.info("=" * 60)
    logger.info(f"Total agents: {metrics.total_agents}")
    logger.info(f"Active agents: {metrics.active_agents}")
    logger.info(f"Idle agents: {metrics.idle_agents}")
    logger.info(f"Tasks completed: {metrics.total_tasks_completed}")
    logger.info(f"Tasks failed: {metrics.total_tasks_failed}")
    logger.info(f"Active tasks: {metrics.metadata.get('active_tasks', 0)}")
    logger.info(f"Queued tasks: {metrics.metadata.get('queued_tasks', 0)}")
    logger.info("=" * 60)

    # Check for proposed actions
    pending = action_proposer.get_pending_approvals()
    if pending:
        logger.info(f"\n{len(pending)} actions pending approval:")
        for action in pending:
            logger.info(f"  - {action.description} (safety: {action.safety_level})")

    # Stop coordinator
    await coordinator.stop()
    logger.info("Swarm stopped")


if __name__ == "__main__":
    asyncio.run(main())
