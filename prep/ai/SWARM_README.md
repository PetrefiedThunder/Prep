# Agent Swarm Framework

A comprehensive framework for managing swarms of AI agents that monitor and maintain repositories.

## Overview

The Agent Swarm Framework enables you to deploy a "swarm of 100 agents" (or any number) that work together to monitor repository changes, identify issues, propose fixes, and automatically implement improvements. The system is built on several core components:

1. **SwarmCoordinator**: Orchestrates multiple agents and manages their lifecycle
2. **EventMonitor**: Monitors repository for file changes and other events
3. **ActionProposer**: Allows agents to propose changes with approval workflows
4. **ActionExecutor**: Safely executes approved changes
5. **Specialized Agents**: Pre-built agents for common tasks

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Swarm Coordinator                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Agent Registry                            │   │
│  │  • Registers/unregisters agents                     │   │
│  │  • Indexes by type and capability                   │   │
│  │  • Tracks agent status                              │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Task Queue & Dispatcher                   │   │
│  │  • Routes tasks to appropriate agents               │   │
│  │  • Manages concurrent execution                     │   │
│  │  • Tracks task status                               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────────┐
│                    Event Monitor                            │
│  • Watches for file system changes                          │
│  • Detects repository events                                │
│  • Dispatches events to registered handlers                 │
└─────────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────────┐
│                   Agent Swarm (100+ agents)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Linting  │  │ Security │  │   Docs   │  │  Tests   │   │
│  │  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│       ↓              ↓              ↓             ↓          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              Action Proposal & Execution System             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Action Proposer                             │   │
│  │  • Collects proposed changes                        │   │
│  │  • Routes for approval                              │   │
│  │  • Auto-approves low-risk changes                   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Action Executor                             │   │
│  │  • Executes approved changes                        │   │
│  │  • Creates backups for rollback                     │   │
│  │  • Tracks execution results                         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Create a Swarm Configuration

```bash
python -m prep.ai.swarm_runner init my_swarm.yaml
```

This creates a default configuration file that you can customize.

### 2. Run the Swarm

```bash
# Run indefinitely
python -m prep.ai.swarm_runner run my_swarm.yaml

# Run for 5 minutes (300 seconds)
python -m prep.ai.swarm_runner run my_swarm.yaml 300
```

### 3. Run a Quick Demo

```bash
python -m prep.ai.swarm_runner demo
```

## Configuration

Example `swarm_config.yaml`:

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
    monitored_paths: ["prep/**/*.py", "tests/**/*.py"]

  - name: security_agent_01
    type: security_patch
    enabled: true
    capabilities: ["security_scan", "security_patch"]
    monitored_paths: ["prep/**/*.py"]

  - name: doc_agent_01
    type: documentation
    enabled: true
    capabilities: ["documentation"]
    monitored_paths: ["prep/**/*.py"]

  - name: test_gen_agent_01
    type: test_generation
    enabled: true
    capabilities: ["test_generation"]
    monitored_paths: ["prep/**/*.py"]

  - name: dependency_agent_01
    type: dependency_update
    enabled: true
    capabilities: ["dependency_update"]
    monitored_paths: ["requirements.txt", "package.json"]
```

### Configuration Options

- **name**: Name for your swarm
- **max_concurrent_tasks**: Maximum number of tasks to execute concurrently
- **enable_event_monitoring**: Whether to monitor file system changes
- **monitor_poll_interval**: How often to check for changes (in seconds)
- **auto_approve_low_risk**: Automatically approve low-risk actions
- **root_dir**: Root directory to monitor and operate on
- **agents**: List of agent configurations

## Built-in Agents

### LintingAgent
Automatically fixes common linting issues:
- Trailing whitespace
- Missing final newlines
- Multiple consecutive blank lines

**Capabilities**: `code_fix`, `linting`

### SecurityPatchAgent
Detects and patches security vulnerabilities:
- Hardcoded secrets
- Use of `eval()` and `exec()`
- `shell=True` in subprocess calls

**Capabilities**: `security_scan`, `security_patch`

### DocumentationAgent
Ensures code is properly documented:
- Checks for module docstrings
- Validates function docstrings
- Proposes documentation improvements

**Capabilities**: `documentation`

### TestGenerationAgent
Generates missing tests:
- Detects files without corresponding tests
- Proposes test file generation

**Capabilities**: `test_generation`

### DependencyUpdateAgent
Monitors and updates dependencies:
- Checks `requirements.txt` and `package.json`
- Identifies outdated packages
- Proposes updates

**Capabilities**: `dependency_update`

## Programmatic Usage

### Basic Example

```python
import asyncio
from prep.ai.swarm_config import SwarmFactory, SwarmConfig, AgentConfig
from prep.ai.action_system import ActionExecutor

async def run_my_swarm():
    # Create configuration
    config = SwarmConfig(
        name="my_swarm",
        max_concurrent_tasks=5,
        agents=[
            AgentConfig(
                name="linter_01",
                type="linting",
                capabilities=["linting"],
                monitored_paths=["src/**/*.py"]
            )
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

    # Stop the swarm
    await coordinator.stop()
    await event_monitor.stop()

asyncio.run(run_my_swarm())
```

### Manual Agent Registration

```python
from prep.ai.swarm_coordinator import SwarmCoordinator
from prep.ai.swarm_agents import LintingAgent
from prep.ai.action_system import ActionProposer
from prep.ai.agent_framework import SafetyLayer, ValidationLayer

# Create coordinator
coordinator = SwarmCoordinator(max_concurrent_tasks=10)

# Create agent
safety_layer = SafetyLayer()
validation_layer = ValidationLayer()
action_proposer = ActionProposer()

linting_agent = LintingAgent(safety_layer, validation_layer, action_proposer)

# Register agent
agent_id = coordinator.register_agent(
    agent=linting_agent,
    agent_name="linter_01",
    agent_type="linting",
    capabilities=["linting", "code_fix"],
    monitored_paths=["src/**/*.py"]
)

print(f"Registered agent: {agent_id}")
```

### Submitting Tasks

```python
# Submit a task to the swarm
task_id = await coordinator.submit_task(
    task_type="linting",
    description="Lint all Python files",
    context={"file_path": "prep/api/auth.py"},
    priority=5
)

# Check task status
task = coordinator.get_task_status(task_id)
print(f"Task status: {task.status}")
```

### Handling Action Proposals

```python
from prep.ai.action_system import ActionProposer, ActionExecutor

action_proposer = ActionProposer()
action_executor = ActionExecutor()

# Get pending approvals
pending = action_proposer.get_pending_approvals()
for action in pending:
    print(f"Action: {action.description}")
    print(f"Rationale: {action.rationale}")
    print(f"Safety level: {action.safety_level}")

    # Approve or reject
    if action.safety_level == "low":
        action_proposer.approve_action(action.action_id, "human_reviewer")

# Execute approved actions
approved = action_proposer.get_approved_actions()
for action in approved:
    result = await action_executor.execute_action(action)
    print(f"Result: {result.message}")
```

## Scaling to 100+ Agents

To create a true swarm of 100+ agents:

1. **Duplicate agent configurations** with different names but same type
2. **Adjust max_concurrent_tasks** based on your system resources
3. **Partition monitored paths** to reduce overlap

Example for 100 linting agents:

```yaml
agents:
  # Generate 100 linting agents
  - name: linting_agent_001
    type: linting
    monitored_paths: ["prep/ai/**/*.py"]
  - name: linting_agent_002
    type: linting
    monitored_paths: ["prep/api/**/*.py"]
  # ... 98 more agents ...
  - name: linting_agent_100
    type: linting
    monitored_paths: ["tests/**/*.py"]
```

Or programmatically:

```python
agents = []
for i in range(100):
    agents.append(AgentConfig(
        name=f"linting_agent_{i:03d}",
        type="linting",
        capabilities=["linting"],
        monitored_paths=[f"prep/**/*.py"]
    ))

config = SwarmConfig(
    name="massive_swarm",
    max_concurrent_tasks=50,
    agents=agents
)
```

## Event Monitoring

The EventMonitor watches for repository changes and notifies agents:

```python
from prep.ai.event_monitor import EventMonitor, EventType

monitor = EventMonitor(root_dir=".")

# Register handler
def handle_file_change(event):
    print(f"File changed: {event.file_path}")

monitor.register_handler(EventType.FILE_MODIFIED, handle_file_change)

# Start monitoring
await monitor.start(poll_interval=2.0)
```

### Supported Event Types

- `FILE_CREATED`: New file created
- `FILE_MODIFIED`: Existing file modified
- `FILE_DELETED`: File deleted
- `FILE_RENAMED`: File renamed
- `DIRECTORY_CREATED`: New directory created
- `DIRECTORY_DELETED`: Directory deleted
- `GIT_COMMIT`: Git commit event
- `GIT_PUSH`: Git push event
- `GIT_PR_OPENED`: Pull request opened
- `GIT_PR_UPDATED`: Pull request updated
- `DEPENDENCY_UPDATED`: Dependency file changed
- `TEST_FAILED`: Test failure detected
- `BUILD_FAILED`: Build failure detected
- `CUSTOM`: Custom event type

## Creating Custom Agents

```python
from prep.ai.agent_framework import AIAgent, AgentResponse
from prep.ai.action_system import ActionProposer, ActionType

class MyCustomAgent(AIAgent):
    def __init__(self, safety_layer, validation_layer, action_proposer):
        super().__init__(safety_layer, validation_layer)
        self.action_proposer = action_proposer
        self.agent_id = "my_custom_agent"
        self.agent_name = "MyCustomAgent"

    async def execute_task(self, task_description: str, context: dict) -> AgentResponse:
        # Your custom logic here
        file_path = context.get("file_path", "")

        # Analyze file
        issues = self._analyze_file(file_path)

        if issues:
            # Propose a fix
            action_id = self.action_proposer.propose_action(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                action_type=ActionType.CODE_FIX,
                description=f"Fix issues in {file_path}",
                rationale="Found issues that need fixing",
                target_path=file_path,
                content=self._generate_fix(file_path, issues),
                safety_level="medium"
            )

            return AgentResponse(
                content=f"Proposed fix for {len(issues)} issues",
                metadata={"action_id": action_id, "issues": issues}
            )

        return AgentResponse(
            content="No issues found",
            metadata={"issues": []}
        )

    def _analyze_file(self, file_path: str) -> list:
        # Your analysis logic
        return []

    def _generate_fix(self, file_path: str, issues: list) -> str:
        # Your fix generation logic
        return ""

    async def handle_event(self, event):
        """Handle repository events."""
        if event.event_type == EventType.FILE_MODIFIED:
            await self.execute_task(
                f"Analyze {event.file_path}",
                {"file_path": event.file_path}
            )
```

## Metrics and Monitoring

```python
# Get swarm metrics
metrics = coordinator.get_metrics()

print(f"Total agents: {metrics.total_agents}")
print(f"Active agents: {metrics.active_agents}")
print(f"Idle agents: {metrics.idle_agents}")
print(f"Tasks completed: {metrics.total_tasks_completed}")
print(f"Tasks failed: {metrics.total_tasks_failed}")
print(f"Uptime: {metrics.uptime_seconds}s")
```

## Safety and Approval Workflows

Actions are categorized by safety level:

- **low**: Auto-approved (if enabled)
- **medium**: Requires approval
- **high**: Requires approval + human review
- **critical**: Requires approval + human review + backup

```python
# Enable auto-approval for low-risk actions
action_proposer.set_auto_approve_low_risk(True)

# Manual approval
action_proposer.approve_action(action_id, approved_by="alice")

# Rejection
action_proposer.reject_action(action_id, reason="Not safe")
```

## Integration with Existing Tools

The swarm framework integrates with existing agent tools:

```python
from prep.ai.copilot_agents import SecurityAgent, CodeQualityAgent
from prep.ai.agent_runner import AgentRunner

# Use existing copilot agents in the swarm
security_agent = SecurityAgent(safety_layer, validation_layer)
coordinator.register_agent(
    agent=security_agent,
    agent_name="security_scanner",
    agent_type="security",
    capabilities=["security_scan"]
)

# Use existing agent runner for comprehensive audits
runner = AgentRunner(root_dir="prep")
report = await runner.run_audit(max_files=100)
print(report.get_summary())
```

## Best Practices

1. **Start small**: Begin with 5-10 agents and scale up
2. **Monitor resource usage**: Each agent consumes memory and CPU
3. **Partition workload**: Assign different paths to different agents
4. **Use capabilities**: Leverage the capability system for smart task routing
5. **Set appropriate priorities**: Critical tasks should have lower priority numbers
6. **Review proposals**: Don't auto-approve everything blindly
7. **Test in isolation**: Test custom agents individually before adding to swarm
8. **Log everything**: Use Python logging to track agent activities
9. **Handle failures gracefully**: Agents should not crash the entire swarm
10. **Regular maintenance**: Periodically review and update agent configurations

## Troubleshooting

### Agents not processing events

- Check that event monitoring is enabled in config
- Verify monitored_paths patterns match your files
- Ensure poll_interval is appropriate for your use case

### High memory usage

- Reduce max_concurrent_tasks
- Limit number of active agents
- Increase poll_interval to reduce file scanning frequency

### Actions not being executed

- Check if actions require approval
- Verify auto_approve_low_risk setting
- Manually approve pending actions

### Agents conflicting with each other

- Partition monitored_paths to avoid overlap
- Use different capabilities for different agent types
- Adjust priorities to control execution order

## API Reference

See individual module documentation:
- `prep.ai.swarm_coordinator` - Core orchestration
- `prep.ai.event_monitor` - Event monitoring
- `prep.ai.action_system` - Action proposals and execution
- `prep.ai.swarm_agents` - Pre-built specialized agents
- `prep.ai.swarm_config` - Configuration and factory
- `prep.ai.agent_framework` - Base agent framework

## Examples

See `prep/ai/swarm_runner.py` for a complete working example.

## License

Part of the Prep platform - see main LICENSE file.
