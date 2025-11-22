"""Example runner for the agent swarm system.

This module demonstrates how to set up and run a swarm of agents that monitor
and maintain a repository.
"""

import asyncio
import logging
import sys
from pathlib import Path

from prep.ai.action_system import ActionExecutor
from prep.ai.swarm_config import SwarmFactory, create_default_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def run_swarm(config_path: str = "swarm_config.yaml", duration: int = 60) -> None:
    """Run the agent swarm for a specified duration.

    Args:
        config_path: Path to the swarm configuration file
        duration: How long to run the swarm in seconds (0 = infinite)
    """
    logger.info("Starting agent swarm...")

    # Load configuration
    config = SwarmFactory.load_config(config_path)
    logger.info(f"Loaded configuration: {config.name}")

    # Create swarm components
    coordinator, event_monitor, action_proposer = SwarmFactory.create_swarm(config)
    action_executor = ActionExecutor(root_dir=config.root_dir)

    try:
        # Start the swarm
        await coordinator.start()
        logger.info("Swarm coordinator started")

        # Start event monitoring if enabled
        if config.enable_event_monitoring:
            await event_monitor.start(poll_interval=config.monitor_poll_interval)
            logger.info(f"Event monitoring started (polling every {config.monitor_poll_interval}s)")

        # Print initial metrics
        metrics = coordinator.get_metrics()
        logger.info(
            f"Swarm running with {metrics.total_agents} agents "
            f"({metrics.idle_agents} idle, {metrics.active_agents} active)"
        )

        # Run for specified duration
        if duration > 0:
            logger.info(f"Running for {duration} seconds...")
            await asyncio.sleep(duration)
        else:
            logger.info("Running indefinitely (Ctrl+C to stop)...")
            # Run until interrupted
            try:
                while True:
                    await asyncio.sleep(10)

                    # Print periodic metrics
                    metrics = coordinator.get_metrics()
                    logger.info(
                        f"Metrics: {metrics.total_tasks_completed} completed, "
                        f"{metrics.total_tasks_failed} failed, "
                        f"{metrics.metadata.get('queued_tasks', 0)} queued"
                    )

                    # Check for pending approvals
                    pending = action_proposer.get_pending_approvals()
                    if pending:
                        logger.info(f"{len(pending)} actions pending approval:")
                        for action in pending[:5]:  # Show first 5
                            logger.info(
                                f"  - [{action.safety_level}] {action.description} "
                                f"by {action.agent_name}"
                            )

                    # Execute approved actions
                    approved = action_proposer.get_approved_actions()
                    for action in approved[:5]:  # Process up to 5 per cycle
                        logger.info(f"Executing: {action.description}")
                        result = await action_executor.execute_action(action)
                        if result.success:
                            logger.info(f"Success: {result.message}")
                        else:
                            logger.warning(f"Failed: {result.error}")

            except KeyboardInterrupt:
                logger.info("Received interrupt signal")

    finally:
        # Stop all components
        logger.info("Stopping swarm...")
        await coordinator.stop()
        await event_monitor.stop()

        # Print final metrics
        metrics = coordinator.get_metrics()
        logger.info("=" * 60)
        logger.info("FINAL SWARM METRICS")
        logger.info("=" * 60)
        logger.info(f"Total agents: {metrics.total_agents}")
        logger.info(f"Tasks completed: {metrics.total_tasks_completed}")
        logger.info(f"Tasks failed: {metrics.total_tasks_failed}")
        logger.info(f"Uptime: {metrics.uptime_seconds:.1f} seconds")
        logger.info("=" * 60)

        # Show pending approvals
        pending = action_proposer.get_pending_approvals()
        if pending:
            logger.info(f"\n{len(pending)} actions still pending approval")
            for action in pending:
                logger.info(
                    f"  - [{action.safety_level}] {action.description} "
                    f"(proposed by {action.agent_name})"
                )

        logger.info("Swarm stopped")


async def demo_swarm() -> None:
    """Run a quick demo of the swarm system."""
    logger.info("Running swarm demo...")

    # Create a demo config file if it doesn't exist
    config_path = Path("swarm_config.yaml")
    if not config_path.exists():
        logger.info("Creating default configuration...")
        create_default_config(config_path)

    # Run the swarm for 30 seconds
    await run_swarm(str(config_path), duration=30)


def main() -> None:
    """Main entry point for the swarm runner."""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "init":
            # Create default config
            output = sys.argv[2] if len(sys.argv) > 2 else "swarm_config.yaml"
            create_default_config(output)
            print(f"Created swarm configuration at {output}")
            print(
                "Edit the file to customize your swarm, "
                "then run: python -m prep.ai.swarm_runner run"
            )

        elif command == "run":
            # Run swarm with config
            config = sys.argv[2] if len(sys.argv) > 2 else "swarm_config.yaml"
            duration = int(sys.argv[3]) if len(sys.argv) > 3 else 0  # 0 = infinite

            if not Path(config).exists():
                print(f"Error: Configuration file not found: {config}")
                print("Run 'python -m prep.ai.swarm_runner init' to create a default config")
                sys.exit(1)

            asyncio.run(run_swarm(config, duration))

        elif command == "demo":
            # Run quick demo
            asyncio.run(demo_swarm())

        else:
            print(f"Unknown command: {command}")
            print_usage()
            sys.exit(1)
    else:
        print_usage()


def print_usage() -> None:
    """Print usage information."""
    print("Agent Swarm Runner")
    print()
    print("Usage:")
    print("  python -m prep.ai.swarm_runner init [config_file]")
    print("    Create a default swarm configuration file")
    print()
    print("  python -m prep.ai.swarm_runner run [config_file] [duration]")
    print("    Run the swarm with the specified configuration")
    print("    duration: seconds to run (default: infinite)")
    print()
    print("  python -m prep.ai.swarm_runner demo")
    print("    Run a quick 30-second demo of the swarm")
    print()
    print("Examples:")
    print("  python -m prep.ai.swarm_runner init my_swarm.yaml")
    print("  python -m prep.ai.swarm_runner run my_swarm.yaml 300")
    print("  python -m prep.ai.swarm_runner demo")


if __name__ == "__main__":
    main()
