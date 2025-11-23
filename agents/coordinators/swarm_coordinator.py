"""Swarm coordinator for managing the agent swarm."""

import asyncio
import logging

from ..core.agent import AgentConfig
from ..core.swarm import AgentSwarm
from ..monitors import (
    APIMonitorAgent,
    BuildMonitorAgent,
    CodeQualityAgent,
    ComplianceAgent,
    DatabaseMonitorAgent,
    DocumentationAgent,
    PerformanceMonitorAgent,
    RepositoryMonitorAgent,
    SecurityMonitorAgent,
    TestingAgent,
)


class SwarmCoordinator:
    """Coordinates the creation and management of the agent swarm."""
    
    def __init__(self):
        """Initialize the swarm coordinator."""
        self.swarm = AgentSwarm(name="prep-agent-swarm")
        self.logger = logging.getLogger("swarm.coordinator")
    
    def create_swarm(self, num_agents: int = 100) -> None:
        """Create a swarm of agents."""
        self.logger.info(f"Creating swarm with {num_agents} agents")
        
        # Define agent distribution (10 of each type)
        agents_per_type = num_agents // 10
        
        # Create security monitoring agents
        for i in range(agents_per_type):
            config = AgentConfig(
                name=f"security-agent-{i+1}",
                agent_type="security",
                scope=["auth", "secrets", "vulnerabilities"],
                capabilities=["secret-scanning", "vulnerability-detection", "permission-check"],
                check_interval=300,  # 5 minutes
            )
            agent = SecurityMonitorAgent(config)
            self.swarm.register_agent(agent)
        
        # Create code quality agents
        for i in range(agents_per_type):
            config = AgentConfig(
                name=f"code-quality-agent-{i+1}",
                agent_type="code-quality",
                scope=["linting", "typing", "formatting"],
                capabilities=["lint-check", "type-check", "complexity-analysis"],
                check_interval=180,  # 3 minutes
            )
            agent = CodeQualityAgent(config)
            self.swarm.register_agent(agent)
        
        # Create testing agents
        for i in range(agents_per_type):
            config = AgentConfig(
                name=f"testing-agent-{i+1}",
                agent_type="testing",
                scope=["unit-tests", "integration-tests", "coverage"],
                capabilities=["test-execution", "coverage-analysis", "test-quality"],
                check_interval=240,  # 4 minutes
            )
            agent = TestingAgent(config)
            self.swarm.register_agent(agent)
        
        # Create documentation agents
        for i in range(agents_per_type):
            config = AgentConfig(
                name=f"documentation-agent-{i+1}",
                agent_type="documentation",
                scope=["api-docs", "readme", "inline-docs"],
                capabilities=["doc-generation", "doc-validation", "doc-quality"],
                check_interval=360,  # 6 minutes
            )
            agent = DocumentationAgent(config)
            self.swarm.register_agent(agent)
        
        # Create compliance monitoring agents
        for i in range(agents_per_type):
            config = AgentConfig(
                name=f"compliance-agent-{i+1}",
                agent_type="compliance",
                scope=["license", "privacy", "accessibility"],
                capabilities=["license-check", "privacy-check", "accessibility-check"],
                check_interval=600,  # 10 minutes
            )
            agent = ComplianceAgent(config)
            self.swarm.register_agent(agent)
        
        # Create API monitoring agents
        for i in range(agents_per_type):
            config = AgentConfig(
                name=f"api-monitor-agent-{i+1}",
                agent_type="api-monitor",
                scope=["endpoints", "performance", "errors"],
                capabilities=["health-check", "performance-monitor", "error-tracking"],
                check_interval=120,  # 2 minutes
            )
            agent = APIMonitorAgent(config)
            self.swarm.register_agent(agent)
        
        # Create database monitoring agents
        for i in range(agents_per_type):
            config = AgentConfig(
                name=f"database-monitor-agent-{i+1}",
                agent_type="database-monitor",
                scope=["connections", "queries", "migrations"],
                capabilities=["connection-monitor", "query-analysis", "migration-check"],
                check_interval=180,  # 3 minutes
            )
            agent = DatabaseMonitorAgent(config)
            self.swarm.register_agent(agent)
        
        # Create build/CI monitoring agents
        for i in range(agents_per_type):
            config = AgentConfig(
                name=f"build-monitor-agent-{i+1}",
                agent_type="build-monitor",
                scope=["builds", "deployments", "workflows"],
                capabilities=["build-monitor", "deployment-check", "workflow-health"],
                check_interval=300,  # 5 minutes
            )
            agent = BuildMonitorAgent(config)
            self.swarm.register_agent(agent)
        
        # Create performance monitoring agents
        for i in range(agents_per_type):
            config = AgentConfig(
                name=f"performance-monitor-agent-{i+1}",
                agent_type="performance-monitor",
                scope=["response-times", "resources", "bottlenecks"],
                capabilities=["performance-analysis", "resource-monitor", "bottleneck-detection"],
                check_interval=180,  # 3 minutes
            )
            agent = PerformanceMonitorAgent(config)
            self.swarm.register_agent(agent)
        
        # Create general repository monitoring agents
        for i in range(agents_per_type):
            config = AgentConfig(
                name=f"repository-monitor-agent-{i+1}",
                agent_type="repository-monitor",
                scope=["structure", "dependencies", "branches"],
                capabilities=["structure-check", "dependency-update", "branch-cleanup"],
                check_interval=420,  # 7 minutes
            )
            agent = RepositoryMonitorAgent(config)
            self.swarm.register_agent(agent)
        
        self.logger.info(f"Created {len(self.swarm)} agents")
    
    async def start_swarm(self) -> None:
        """Start all agents in the swarm."""
        self.logger.info("Starting agent swarm")
        await self.swarm.start_all()
    
    async def stop_swarm(self) -> None:
        """Stop all agents in the swarm."""
        self.logger.info("Stopping agent swarm")
        await self.swarm.stop_all()
    
    async def monitor_swarm(self) -> None:
        """Monitor swarm health and restart failed agents."""
        while True:
            try:
                health = await self.swarm.health_check_all()
                self.logger.info(f"Swarm health: {health['summary']}")
                
                # Restart failed agents
                await self.swarm.restart_failed_agents()
                
                # Wait before next health check
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error monitoring swarm: {e}")
                await asyncio.sleep(60)
    
    async def get_swarm_status(self) -> dict:
        """Get current status of the swarm."""
        return await self.swarm.health_check_all()
