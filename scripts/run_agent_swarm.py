#!/usr/bin/env python3
"""Agent Swarm Orchestration Script.

Manage the agent swarm that monitors the Prep repository.
"""

import argparse
import asyncio
import logging
import signal
import sys
import tempfile
from pathlib import Path


def _import_swarm_coordinator():
    repo_root = Path(__file__).parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from agents.coordinators.swarm_coordinator import SwarmCoordinator

    return SwarmCoordinator


SwarmCoordinator = _import_swarm_coordinator()

# Get platform-appropriate log directory
LOG_DIR = Path(tempfile.gettempdir())
LOG_FILE = LOG_DIR / "agent-swarm.log"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE),
    ],
)

logger = logging.getLogger("swarm.main")


class SwarmOrchestrator:
    """Main orchestrator for the agent swarm."""

    def __init__(self, num_agents: int = 100):
        """Initialize the orchestrator."""
        self.num_agents = num_agents
        self.coordinator = SwarmCoordinator()
        self.running = False
        self.stop_requested = False
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the agent swarm."""
        logger.info(f"Starting agent swarm with {self.num_agents} agents")

        # Create the swarm
        self.coordinator.create_swarm(num_agents=self.num_agents)

        # Start all agents
        await self.coordinator.start_swarm()

        self.running = True
        logger.info("Agent swarm started successfully")

    async def stop(self) -> None:
        """Stop the agent swarm."""
        logger.info("Stopping agent swarm")
        self.running = False
        self.stop_requested = True
        self._shutdown_event.set()

        await self.coordinator.stop_swarm()

        logger.info("Agent swarm stopped successfully")

    async def run(self) -> None:
        """Run the agent swarm with monitoring."""
        await self.start()

        try:
            # Start monitoring in the background
            monitor_task = asyncio.create_task(self.coordinator.monitor_swarm())

            # Wait for shutdown event
            await self._shutdown_event.wait()

            # Cancel monitoring task
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")

        finally:
            await self.stop()

    async def status(self) -> None:
        """Display swarm status."""
        status = await self.coordinator.get_swarm_status()

        print("\n" + "=" * 80)
        print(f"Agent Swarm Status: {status['swarm_name']}")
        print("=" * 80)
        print(f"Total Agents: {status['total_agents']}")
        print("\nStatus Summary:")
        for status_name, count in status["summary"].items():
            print(f"  {status_name}: {count}")
        print("=" * 80 + "\n")


# Global orchestrator instance for signal handling
_orchestrator_instance = None


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, requesting graceful shutdown")
    if _orchestrator_instance:
        asyncio.create_task(_orchestrator_instance.stop())


async def main():
    """Main entry point."""
    global _orchestrator_instance

    parser = argparse.ArgumentParser(description="Agent Swarm Orchestration for Prep Repository")
    parser.add_argument(
        "--num-agents",
        type=int,
        default=100,
        help="Number of agents to create (default: 100)",
    )
    parser.add_argument(
        "--command",
        choices=["start", "status"],
        default="start",
        help="Command to execute (default: start)",
    )

    args = parser.parse_args()

    orchestrator = SwarmOrchestrator(num_agents=args.num_agents)
    _orchestrator_instance = orchestrator

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.command == "start":
        logger.info("Starting agent swarm orchestration")
        await orchestrator.run()
    elif args.command == "status":
        # For status, we need to create and start briefly
        await orchestrator.start()
        await orchestrator.status()
        await orchestrator.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Orchestration interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error in orchestration: {e}", exc_info=True)
        sys.exit(1)
