# AI Agent Framework

This directory contains a comprehensive AI agent framework with two main capabilities:

1. **Code Audit Agents**: Static analysis agents for security, quality, and architecture reviews
2. **Agent Swarm System**: A scalable framework for deploying swarms of agents that monitor and maintain repositories

---

## 🚀 Quick Start

### Run Code Audit
```bash
# Audit a single file
python -m prep.ai.agent_runner path/to/file.py

# Full repository audit
python -m prep.ai.agent_runner
```

### Run Agent Swarm
```bash
# Create configuration
python -m prep.ai.swarm_runner init swarm_config.yaml

# Run the swarm
python -m prep.ai.swarm_runner run swarm_config.yaml

# Quick demo (30 seconds)
python -m prep.ai.swarm_runner demo
```

---

## 📦 Components

### Code Audit System

#### 1. `copilot_agents.py`
Contains five specialized agents for different aspects of code auditing:

##### SecurityAgent
Scans for security vulnerabilities including:
- Hardcoded secrets and API keys
- SQL injection vulnerabilities
- Insecure authentication patterns
- Command injection risks
- Unsafe file operations

##### BackendArchitectAgent
Reviews backend architecture and design patterns:
- Async/await usage patterns
- Database query optimization (N+1 queries)
- API endpoint design
- Error handling patterns

##### CodeQualityAgent
Assesses code quality metrics:
- Cyclomatic complexity
- Type hints presence
- Documentation (docstrings)
- Naming conventions

##### TestingAgent
Validates test coverage and quality:
- Test file presence for modules
- Assertion presence in tests
- Test naming conventions
- Test isolation

##### OperationsAgent
Flags destructive operations requiring human approval:
- File deletion operations
- Database table drops and deletions
- Production environment modifications

#### 2. `agent_runner.py`
Utility for running agents across Python files:
- Discovers Python files in repository
- Applies all or selected agents
- Aggregates results with severity levels
- Generates comprehensive reports
- Supports filtering and parallel execution

---

### Agent Swarm System

The swarm system enables deployment of multiple agents that actively monitor and maintain your repository.

#### 3. `swarm_coordinator.py`
Core orchestration for agent swarms:
- **SwarmCoordinator**: Manages agent lifecycle and task routing
- **AgentRegistry**: Dynamic agent registration and discovery
- **Task Queue**: Distributes work across agents
- **Metrics**: Real-time monitoring of swarm activity

#### 4. `event_monitor.py`
Repository event monitoring:
- File system change detection
- Event type classification (created, modified, deleted)
- Handler registration and dispatch
- Configurable polling intervals

#### 5. `action_system.py`
Safe change proposal and execution:
- **ActionProposer**: Agents propose changes for approval
- **ActionExecutor**: Executes approved changes safely
- **Approval Workflow**: Human-in-the-loop for high-risk changes
- **Rollback Support**: Backups for safe rollback

#### 6. `swarm_agents.py`
Specialized maintenance agents:
- **LintingAgent**: Auto-fixes code style issues
- **SecurityPatchAgent**: Patches known vulnerabilities
- **DocumentationAgent**: Maintains documentation
- **TestGenerationAgent**: Generates missing tests
- **DependencyUpdateAgent**: Monitors package updates

#### 7. `swarm_config.py`
Configuration and deployment:
- YAML-based agent configuration
- SwarmFactory for easy setup
- Scaling configuration
- Path monitoring rules

#### 8. `swarm_runner.py`
Command-line interface for swarms:
- Initialize swarm configurations
- Run swarms with monitoring
- Demo mode for quick testing

---

## Usage

### Code Audit System

#### Command Line

```bash
# Audit a single file
python -m prep.ai.agent_runner path/to/file.py

# Full repository audit (limited demo)
python -m prep.ai.agent_runner
```

#### Python API

```python
import asyncio
from prep.ai.agent_runner import AgentRunner

async def audit_code():
    # Create runner with all agents
    runner = AgentRunner(root_dir="prep")
    
    # Run full audit
    report = await runner.run_audit(max_files=50)
    
    # Display results
    print(report.get_detailed_report(max_findings=20))
    
    # Check if human review required
    if report.requires_human_review:
        print("⚠️  Critical issues require human review!")

asyncio.run(audit_code())
```

#### Selective Agent Execution

```python
# Run only security and operations agents
runner = AgentRunner(
    root_dir="prep",
    agents=["security", "operations"]
)
report = await runner.run_audit()
```

#### Filtering Files

```python
# Audit specific paths
runner = AgentRunner(root_dir="prep")
report = await runner.run_audit(
    file_patterns=["prep/auth/*", "prep/api/*"]
)
```

---

### Agent Swarm System

#### Quick Start

```bash
# Create configuration
python -m prep.ai.swarm_runner init my_swarm.yaml

# Edit configuration to customize agents
# vim my_swarm.yaml

# Run the swarm
python -m prep.ai.swarm_runner run my_swarm.yaml

# Or run for specific duration (5 minutes)
python -m prep.ai.swarm_runner run my_swarm.yaml 300
```

#### Configuration Example

```yaml
name: prep_agent_swarm
max_concurrent_tasks: 10
enable_event_monitoring: true
monitor_poll_interval: 2.0
auto_approve_low_risk: false
root_dir: "."

agents:
  - name: linting_agent_01
    type: linting
    enabled: true
    capabilities: ["code_fix", "linting"]
    monitored_paths: ["prep/**/*.py"]
  
  - name: security_agent_01
    type: security_patch
    enabled: true
    capabilities: ["security_scan"]
    monitored_paths: ["prep/**/*.py"]
  
  # Add 98 more agents to reach 100!
```

#### Programmatic API

```python
from prep.ai.swarm_config import SwarmFactory, SwarmConfig, AgentConfig
from prep.ai.action_system import ActionExecutor

async def run_my_swarm():
    # Create configuration
    config = SwarmConfig(
        name="my_swarm",
        max_concurrent_tasks=10,
        agents=[
            AgentConfig(
                name="linter_01",
                type="linting",
                capabilities=["linting"],
                monitored_paths=["src/**/*.py"]
            )
            # Add more agents...
        ]
    )

    # Create swarm components
    coordinator, event_monitor, action_proposer = SwarmFactory.create_swarm(config)
    action_executor = ActionExecutor()

    # Start the swarm
    await coordinator.start()
    await event_monitor.start()

    # Run for a while
    await asyncio.sleep(60)

    # Check metrics
    metrics = coordinator.get_metrics()
    print(f"Tasks completed: {metrics.total_tasks_completed}")

    # Stop the swarm
    await coordinator.stop()
    await event_monitor.stop()
```

#### Scaling to 100+ Agents

To create a true swarm of 100+ agents:

```python
# Programmatically create 100 agents
agents = []
for i in range(100):
    agents.append(AgentConfig(
        name=f"agent_{i:03d}",
        type="linting",  # or other types
        capabilities=["linting"],
        monitored_paths=[f"prep/**/*.py"]
    ))

config = SwarmConfig(
    name="massive_swarm",
    max_concurrent_tasks=50,
    agents=agents
)
```

See [SWARM_README.md](./SWARM_README.md) for comprehensive swarm documentation.

---

## Severity Levels

Findings are classified by severity:

- **CRITICAL**: Immediate security risks (hardcoded secrets, SQL injection)
- **HIGH**: Serious issues requiring attention (command injection, destructive operations)
- **MEDIUM**: Architectural or quality issues (N+1 queries, high complexity)
- **LOW**: Style and documentation issues (missing type hints, docstrings)
- **INFO**: Informational findings

## Human-in-the-Loop

The OperationsAgent and swarm action system flag operations requiring human approval:
- Any finding with CRITICAL or HIGH severity triggers `requires_human_review`
- Destructive operations (file/database deletions) always require approval
- Production environment modifications are flagged for review

## Integration with CI/CD

The agent suite is designed for CI/CD integration:

```yaml
# Example GitHub Actions workflow
- name: Run Code Audit
  run: |
    python -m prep.ai.agent_runner > audit_report.txt
    # Parse report and fail if critical issues found
```

## Extending the Agents

To add a new agent:

1. Create a class inheriting from `AIAgent`
2. Implement `execute_task()` method
3. Return findings with appropriate severity
4. Add to `AgentRunner.available_agents`

Example:

```python
class PerformanceAgent(AIAgent):
    async def execute_task(self, task_description: str, context: dict[str, Any]) -> AgentResponse:
        code = context.get("code_content", "")
        findings = self._check_performance(code, context.get("file_path", ""))
        return AgentResponse(
            content=f"Performance check complete: {len(findings)} issues",
            metadata={"findings": [f.__dict__ for f in findings]}
        )
```

## Testing

Comprehensive test suite in `tests/prep/test_copilot_agents.py`:

```bash
pytest tests/prep/test_copilot_agents.py -v
```

27 tests covering:
- Individual agent detection capabilities
- Agent runner functionality
- Report generation
- Finding serialization
- Human-in-the-loop triggers

### Swarm System Tests

Comprehensive test suite in `tests/prep/test_swarm_system.py`:

```bash
pytest tests/prep/test_swarm_system.py -v
```

18 tests covering:
- Agent registry and coordination
- Event monitoring and detection
- Action proposal and execution
- Swarm agent functionality
- Configuration and factory patterns

## Documentation

- **[SWARM_README.md](./SWARM_README.md)**: Comprehensive swarm system documentation
- **[agent_framework.py](./agent_framework.py)**: Base agent framework with safety layers
- **[copilot_agents.py](./copilot_agents.py)**: Static analysis agents
- **[swarm_coordinator.py](./swarm_coordinator.py)**: Swarm orchestration
- **[event_monitor.py](./event_monitor.py)**: Event monitoring system
- **[action_system.py](./action_system.py)**: Action proposal and execution

## Future Enhancements

Planned improvements:

**Code Audit System:**
- Integration with GitHub PR bot for automated reviews
- Support for more file types (JavaScript, Go, TypeScript)
- ML-based anomaly detection
- Custom rule configuration
- Integration with existing linters (ruff, mypy, eslint)

**Agent Swarm System:**
- Git hook integration for real-time monitoring
- WebSocket/REST API for external integrations
- Agent-to-agent communication protocols
- Distributed swarm coordination
- Performance monitoring and optimization
- Advanced conflict resolution between agents
- Plugin system for custom agent types
