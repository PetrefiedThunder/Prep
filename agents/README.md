# Agent Swarm System

This directory contains the implementation of the 100-agent swarm system for continuous repository monitoring and automation.

## Directory Structure

```
agents/
├── __init__.py                 # Package initialization
├── core/                       # Core agent framework
│   ├── agent.py               # Base Agent class
│   └── swarm.py               # AgentSwarm management
├── coordinators/              # Swarm coordination
│   └── swarm_coordinator.py  # SwarmCoordinator
├── monitors/                  # Specialized agent implementations
│   ├── specialized_agents.py # Security, CodeQuality, Testing, etc.
│   └── monitoring_agents.py  # API, Database, Build, etc.
└── config/                    # Configuration files
    └── swarm_config.yaml     # Agent swarm configuration
```

## Quick Start

```bash
# Start the agent swarm (100 agents)
python scripts/run_agent_swarm.py

# Start with custom agent count
python scripts/run_agent_swarm.py --num-agents 50

# Check swarm status
python scripts/run_agent_swarm.py --command status
```

## Agent Types

The swarm consists of 10 different agent types, with 10 agents of each type:

1. **Security Monitoring Agents** - Monitor authentication, secrets, and vulnerabilities
2. **Code Quality Agents** - Check linting, typing, and code formatting
3. **Testing Agents** - Monitor test coverage and execution
4. **Documentation Agents** - Validate API docs, README, and inline documentation
5. **Compliance Agents** - Check license, privacy, and accessibility compliance
6. **API Monitor Agents** - Monitor API endpoints, performance, and errors
7. **Database Monitor Agents** - Check database connections, queries, and migrations
8. **Build Monitor Agents** - Monitor builds, deployments, and CI/CD workflows
9. **Performance Monitor Agents** - Track response times, resources, and bottlenecks
10. **Repository Monitor Agents** - Validate file structure, dependencies, and branches

## Architecture

Each agent:
- Runs independently in its own async task
- Performs periodic checks based on its check interval
- Collects metrics on tasks completed, failed, and execution time
- Reports health status to the swarm coordinator
- Automatically restarts on failure

The SwarmCoordinator:
- Creates and manages all agents
- Monitors swarm health
- Restarts failed agents
- Provides status reporting

## Configuration

Configuration is managed via `config/swarm_config.yaml`. You can customize:

- Agent count per type
- Check intervals
- Priority levels
- Logging settings
- Monitoring configuration

## Testing

Run the agent swarm tests:

```bash
pytest tests/agents/test_agent_swarm.py -v
```

## Documentation

See [docs/AGENT_SWARM.md](../docs/AGENT_SWARM.md) for complete documentation.

## Integration

The agent swarm can be integrated with:
- GitHub Actions workflows
- CI/CD pipelines
- Monitoring dashboards
- Alerting systems

## Development

To add a new agent type:

1. Create a new agent class in `monitors/` inheriting from `Agent`
2. Implement the `execute()` method with your monitoring logic
3. Register the agent in `coordinators/swarm_coordinator.py`
4. Update the configuration in `config/swarm_config.yaml`

Example:

```python
from agents.core.agent import Agent

class MyCustomAgent(Agent):
    async def execute(self) -> None:
        self.logger.info(f"Custom agent {self.config.name} executing")
        # Your monitoring logic here
```

## License

This agent swarm system is part of the Prep project and is licensed under the MIT License.
