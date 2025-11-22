"""Tests for the agent swarm system."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from prep.ai import swarm_agents
from prep.ai.action_system import ActionExecutor, ActionProposer, ActionType
from prep.ai.agent_framework import SafetyLayer, ValidationLayer
from prep.ai.event_monitor import EventMonitor, EventType, RepositoryEvent
from prep.ai.swarm_config import AgentConfig, SwarmConfig, SwarmFactory
from prep.ai.swarm_coordinator import AgentRegistry, AgentStatus, SwarmCoordinator


@pytest.fixture
def safety_layer():
    """Create a safety layer for testing."""
    return SafetyLayer()


@pytest.fixture
def validation_layer():
    """Create a validation layer for testing."""
    return ValidationLayer()


@pytest.fixture
def action_proposer():
    """Create an action proposer for testing."""
    return ActionProposer()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestAgentRegistry:
    """Tests for AgentRegistry."""

    def test_register_agent(self, safety_layer, validation_layer, action_proposer):
        """Test agent registration."""
        registry = AgentRegistry()
        agent = swarm_agents.LintingAgent(safety_layer, validation_layer, action_proposer)

        agent_id = registry.register(
            agent=agent,
            agent_name="test_linter",
            agent_type="linting",
            capabilities=["linting", "code_fix"],
        )

        assert agent_id is not None
        assert len(agent_id) > 0

        # Verify agent is registered
        agent_info = registry.get_agent(agent_id)
        assert agent_info is not None
        assert agent_info.agent_name == "test_linter"
        assert agent_info.agent_type == "linting"
        assert "linting" in agent_info.capabilities

    def test_get_agents_by_type(self, safety_layer, validation_layer, action_proposer):
        """Test retrieving agents by type."""
        registry = AgentRegistry()

        # Register multiple agents of same type
        agent1 = swarm_agents.LintingAgent(safety_layer, validation_layer, action_proposer)
        agent2 = swarm_agents.LintingAgent(safety_layer, validation_layer, action_proposer)

        registry.register(agent1, "linter1", "linting")
        registry.register(agent2, "linter2", "linting")

        # Get agents by type
        linting_agents = registry.get_agents_by_type("linting")
        assert len(linting_agents) == 2

    def test_get_agents_by_capability(self, safety_layer, validation_layer, action_proposer):
        """Test retrieving agents by capability."""
        registry = AgentRegistry()

        agent = swarm_agents.LintingAgent(safety_layer, validation_layer, action_proposer)
        registry.register(agent, "linter", "linting", capabilities=["linting", "code_fix"])

        # Get agents by capability
        capable_agents = registry.get_agents_by_capability("code_fix")
        assert len(capable_agents) == 1
        assert capable_agents[0].agent_name == "linter"

    def test_unregister_agent(self, safety_layer, validation_layer, action_proposer):
        """Test agent unregistration."""
        registry = AgentRegistry()
        agent = swarm_agents.LintingAgent(safety_layer, validation_layer, action_proposer)

        agent_id = registry.register(agent, "linter", "linting")
        assert registry.get_agent(agent_id) is not None

        # Unregister
        result = registry.unregister(agent_id)
        assert result is True
        assert registry.get_agent(agent_id) is None

    def test_update_agent_status(self, safety_layer, validation_layer, action_proposer):
        """Test updating agent status."""
        registry = AgentRegistry()
        agent = swarm_agents.LintingAgent(safety_layer, validation_layer, action_proposer)

        agent_id = registry.register(agent, "linter", "linting")

        # Update status
        registry.update_agent_status(agent_id, AgentStatus.PROCESSING)

        agent_info = registry.get_agent(agent_id)
        assert agent_info.status == AgentStatus.PROCESSING
        assert agent_info.last_activity is not None


class TestSwarmCoordinator:
    """Tests for SwarmCoordinator."""

    @pytest.mark.asyncio
    async def test_register_and_unregister(self, safety_layer, validation_layer, action_proposer):
        """Test agent registration with coordinator."""
        coordinator = SwarmCoordinator()
        agent = swarm_agents.LintingAgent(safety_layer, validation_layer, action_proposer)

        agent_id = coordinator.register_agent(agent, "linter", "linting")
        assert agent_id is not None

        # Unregister
        result = coordinator.unregister_agent(agent_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_submit_and_process_task(self, safety_layer, validation_layer, action_proposer):
        """Test submitting and processing a task."""
        coordinator = SwarmCoordinator()
        agent = swarm_agents.LintingAgent(safety_layer, validation_layer, action_proposer)

        coordinator.register_agent(agent, "linter", "linting", capabilities=["linting"])

        # Start coordinator
        await coordinator.start()

        try:
            # Submit task
            task_id = await coordinator.submit_task(
                task_type="linting",
                description="Lint test file",
                context={"file_path": "test.py", "code_content": "def foo():  \n    pass\n"},
            )

            # Wait for processing
            await asyncio.sleep(0.5)

            # Check task status
            task = coordinator.get_task_status(task_id)
            assert task is not None
            # Task should be completed or in progress
            assert task.status in ["completed", "in_progress", "assigned"]

        finally:
            await coordinator.stop()

    @pytest.mark.asyncio
    async def test_metrics(self, safety_layer, validation_layer, action_proposer):
        """Test swarm metrics."""
        coordinator = SwarmCoordinator()
        agent = swarm_agents.LintingAgent(safety_layer, validation_layer, action_proposer)

        coordinator.register_agent(agent, "linter", "linting")

        await coordinator.start()

        try:
            metrics = coordinator.get_metrics()
            assert metrics.total_agents == 1
            assert metrics.idle_agents >= 0

        finally:
            await coordinator.stop()


class TestEventMonitor:
    """Tests for EventMonitor."""

    @pytest.mark.asyncio
    async def test_detect_file_creation(self, temp_dir):
        """Test detecting file creation."""
        monitor = EventMonitor(root_dir=temp_dir)

        events_received = []

        def handler(event):
            events_received.append(event)

        monitor.register_handler(EventType.FILE_CREATED, handler)

        # Start monitoring
        await monitor.start(poll_interval=0.5)

        try:
            # Wait for initial scan
            await asyncio.sleep(0.6)

            # Create a file
            test_file = temp_dir / "test.txt"
            test_file.write_text("hello")

            # Wait for detection (need at least 2 poll cycles)
            await asyncio.sleep(1.5)

            # Check if event was received
            assert len(events_received) > 0
            assert any(e.event_type == EventType.FILE_CREATED for e in events_received)

        finally:
            await monitor.stop()

    @pytest.mark.asyncio
    async def test_detect_file_modification(self, temp_dir):
        """Test detecting file modification."""
        monitor = EventMonitor(root_dir=temp_dir)

        # Create initial file
        test_file = temp_dir / "test.txt"
        test_file.write_text("initial")

        events_received = []

        def handler(event):
            events_received.append(event)

        monitor.register_handler(EventType.FILE_MODIFIED, handler)

        # Start monitoring
        await monitor.start(poll_interval=0.5)

        try:
            # Wait for initial scan
            await asyncio.sleep(0.6)

            # Modify the file
            test_file.write_text("modified")

            # Wait for detection
            await asyncio.sleep(1.5)

            # Check if event was received
            assert len(events_received) > 0
            assert any(e.event_type == EventType.FILE_MODIFIED for e in events_received)

        finally:
            await monitor.stop()


class TestActionSystem:
    """Tests for action proposal and execution."""

    def test_propose_action(self, action_proposer):
        """Test proposing an action."""
        action_id = action_proposer.propose_action(
            agent_id="test_agent",
            agent_name="TestAgent",
            action_type=ActionType.FILE_CREATE,
            description="Create test file",
            rationale="Testing action proposal",
            target_path="test.txt",
            content="test content",
            safety_level="low",
        )

        assert action_id is not None

        # Get proposal
        action = action_proposer.get_proposal(action_id)
        assert action is not None
        assert action.description == "Create test file"

    def test_approve_action(self, action_proposer):
        """Test approving an action."""
        action_id = action_proposer.propose_action(
            agent_id="test",
            agent_name="Test",
            action_type=ActionType.FILE_CREATE,
            description="Test",
            rationale="Test",
            safety_level="medium",
        )

        # Approve
        result = action_proposer.approve_action(action_id, "tester")
        assert result is True

        # Check status
        action = action_proposer.get_proposal(action_id)
        assert action.status.value == "approved"

    def test_reject_action(self, action_proposer):
        """Test rejecting an action."""
        action_id = action_proposer.propose_action(
            agent_id="test",
            agent_name="Test",
            action_type=ActionType.FILE_CREATE,
            description="Test",
            rationale="Test",
            safety_level="medium",
        )

        # Reject
        result = action_proposer.reject_action(action_id, "Not needed")
        assert result is True

        # Check status
        action = action_proposer.get_proposal(action_id)
        assert action.status.value == "rejected"

    @pytest.mark.asyncio
    async def test_execute_file_create(self, action_proposer, temp_dir):
        """Test executing a file creation action."""
        executor = ActionExecutor(root_dir=temp_dir)

        # Propose and approve action
        action_id = action_proposer.propose_action(
            agent_id="test",
            agent_name="Test",
            action_type=ActionType.FILE_CREATE,
            description="Create test file",
            rationale="Testing",
            target_path="test.txt",
            content="hello world",
            safety_level="low",
        )

        action_proposer.approve_action(action_id)
        action = action_proposer.get_proposal(action_id)

        # Execute
        result = await executor.execute_action(action)

        assert result.success is True
        assert (temp_dir / "test.txt").exists()
        assert (temp_dir / "test.txt").read_text() == "hello world"


class TestSwarmAgents:
    """Tests for specialized swarm agents."""

    @pytest.mark.asyncio
    async def test_linting_agent_detects_issues(
        self, safety_layer, validation_layer, action_proposer
    ):
        """Test that linting agent detects issues."""
        agent = swarm_agents.LintingAgent(safety_layer, validation_layer, action_proposer)

        # Code with trailing whitespace
        code = "def foo():  \n    pass\n"

        result = await agent.execute_task(
            "Lint code", {"file_path": "test.py", "code_content": code}
        )

        assert "linting" in result.content.lower() or "fix" in result.content.lower()

    @pytest.mark.asyncio
    async def test_documentation_agent_detects_missing_docstrings(
        self, safety_layer, validation_layer, action_proposer
    ):
        """Test that documentation agent detects missing docstrings."""
        agent = swarm_agents.DocumentationAgent(safety_layer, validation_layer, action_proposer)

        # Code without docstrings
        code = "def foo():\n    pass\n"

        result = await agent.execute_task(
            "Check docs", {"file_path": "test.py", "code_content": code}
        )

        assert result.metadata.get("issues") is not None

    @pytest.mark.asyncio
    async def test_security_agent_detects_vulnerabilities(
        self, safety_layer, validation_layer, action_proposer
    ):
        """Test that security agent detects vulnerabilities."""
        agent = swarm_agents.SecurityPatchAgent(safety_layer, validation_layer, action_proposer)

        # Code with security issue
        code = 'api_key = "sk-test123456789"\n'

        result = await agent.execute_task(
            "Security scan", {"file_path": "test.py", "code_content": code}
        )

        # Should detect issue
        assert result.metadata.get("vulnerabilities") is not None


class TestSwarmConfig:
    """Tests for swarm configuration."""

    def test_create_swarm_from_config(self, safety_layer, validation_layer, action_proposer):
        """Test creating a swarm from configuration."""
        config = SwarmConfig(
            name="test_swarm",
            max_concurrent_tasks=5,
            agents=[
                AgentConfig(
                    name="linter1",
                    type="linting",
                    capabilities=["linting"],
                )
            ],
        )

        coordinator, event_monitor, action_proposer = SwarmFactory.create_swarm(config)

        assert coordinator is not None
        assert event_monitor is not None
        assert action_proposer is not None

        # Check that agent was registered
        metrics = coordinator.get_metrics()
        assert metrics.total_agents == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
