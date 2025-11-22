"""Tests for the agent swarm system."""

import asyncio
import pytest

from agents.coordinators.swarm_coordinator import SwarmCoordinator
from agents.core.agent import Agent, AgentConfig, AgentStatus


class MockAgent(Agent):
    """Mock agent for testing."""
    
    async def execute(self) -> None:
        """Mock execution."""
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_agent_creation():
    """Test agent creation and initialization."""
    config = AgentConfig(
        name="test-agent",
        agent_type="test",
        scope=["testing"],
        capabilities=["test-capability"],
    )
    agent = MockAgent(config)
    
    assert agent.config.name == "test-agent"
    assert agent.status == AgentStatus.INITIALIZING
    assert agent.metrics.tasks_completed == 0


@pytest.mark.asyncio
async def test_agent_start_stop():
    """Test agent start and stop lifecycle."""
    config = AgentConfig(
        name="test-agent",
        agent_type="test",
        scope=["testing"],
        capabilities=["test-capability"],
        check_interval=1,
    )
    agent = MockAgent(config)
    
    # Start agent
    await agent.start()
    assert agent.status in [AgentStatus.ACTIVE, AgentStatus.IDLE, AgentStatus.WORKING]
    
    # Wait a bit for execution
    await asyncio.sleep(2)
    
    # Check that agent executed
    assert agent.metrics.tasks_completed > 0
    
    # Stop agent
    await agent.stop()
    assert agent.status == AgentStatus.STOPPED


@pytest.mark.asyncio
async def test_swarm_coordinator():
    """Test swarm coordinator functionality."""
    coordinator = SwarmCoordinator()
    
    # Create swarm with small number for testing
    coordinator.create_swarm(num_agents=10)
    
    # Verify agents were created
    assert len(coordinator.swarm) == 10
    
    # Start swarm
    await coordinator.start_swarm()
    
    # Wait a bit
    await asyncio.sleep(2)
    
    # Check status
    status = await coordinator.get_swarm_status()
    assert status["total_agents"] == 10
    assert "summary" in status
    
    # Stop swarm
    await coordinator.stop_swarm()


@pytest.mark.asyncio
async def test_agent_health_check():
    """Test agent health check."""
    config = AgentConfig(
        name="test-agent",
        agent_type="test",
        scope=["testing"],
        capabilities=["test-capability"],
        check_interval=1,
    )
    agent = MockAgent(config)
    
    await agent.start()
    await asyncio.sleep(2)
    
    health = await agent.health_check()
    
    assert health["agent_id"] == agent.agent_id
    assert health["name"] == "test-agent"
    assert health["type"] == "test"
    assert health["status"] in [s.value for s in AgentStatus]
    assert "metrics" in health
    
    await agent.stop()


def test_swarm_creation_distribution():
    """Test that swarm creates correct distribution of agents."""
    coordinator = SwarmCoordinator()
    coordinator.create_swarm(num_agents=100)
    
    # Check total
    assert len(coordinator.swarm) == 100
    
    # Check distribution (10 of each type)
    agent_types = {}
    for agent in coordinator.swarm.agents.values():
        agent_type = agent.config.agent_type
        agent_types[agent_type] = agent_types.get(agent_type, 0) + 1
    
    # Should have 10 types with 10 agents each
    assert len(agent_types) == 10
    for count in agent_types.values():
        assert count == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
