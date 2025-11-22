#!/usr/bin/env python3
"""
Agent Swarm Orchestration Script.

This script manages the instantiation and lifecycle of the 100-agent swarm
for monitoring and implementing all aspects of the Prep repository.
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add the repo root to the Python path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from agents.coordinators.swarm_coordinator import SwarmCoordinator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/tmp/agent-swarm.log"),
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
        
        await self.coordinator.stop_swarm()
        
        logger.info("Agent swarm stopped successfully")
    
    async def run(self) -> None:
        """Run the agent swarm with monitoring."""
        await self.start()
        
        try:
            # Start monitoring in the background
            monitor_task = asyncio.create_task(self.coordinator.monitor_swarm())
            
            # Keep running until interrupted
            while self.running:
                await asyncio.sleep(1)
            
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
        print(f"\nStatus Summary:")
        for status_name, count in status['summary'].items():
            print(f"  {status_name}: {count}")
        print("=" * 80 + "\n")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}")
    sys.exit(0)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Agent Swarm Orchestration for Prep Repository"
    )
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
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    orchestrator = SwarmOrchestrator(num_agents=args.num_agents)
    
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
