# Agent Suite for Code Audit

This directory contains a comprehensive agent suite for automated code auditing, designed to identify security vulnerabilities, architectural issues, code quality problems, testing gaps, and operational risks.

## Components

### 1. `copilot_agents.py`
Contains five specialized agents for different aspects of code auditing:

#### SecurityAgent
Scans for security vulnerabilities including:
- Hardcoded secrets and API keys
- SQL injection vulnerabilities
- Insecure authentication patterns
- Command injection risks
- Unsafe file operations

#### BackendArchitectAgent
Reviews backend architecture and design patterns:
- Async/await usage patterns
- Database query optimization (N+1 queries)
- API endpoint design
- Error handling patterns

#### CodeQualityAgent
Assesses code quality metrics:
- Cyclomatic complexity
- Type hints presence
- Documentation (docstrings)
- Naming conventions

#### TestingAgent
Validates test coverage and quality:
- Test file presence for modules
- Assertion presence in tests
- Test naming conventions
- Test isolation

#### OperationsAgent
Flags destructive operations requiring human approval:
- File deletion operations
- Database table drops and deletions
- Production environment modifications

### 2. `agent_runner.py`
Utility for running agents across Python files:
- Discovers Python files in repository
- Applies all or selected agents
- Aggregates results with severity levels
- Generates comprehensive reports
- Supports filtering and parallel execution

## Usage

### Command Line

```bash
# Audit a single file
python -m prep.ai.agent_runner path/to/file.py

# Full repository audit (limited demo)
python -m prep.ai.agent_runner
```

### Python API

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

### Selective Agent Execution

```python
# Run only security and operations agents
runner = AgentRunner(
    root_dir="prep",
    agents=["security", "operations"]
)
report = await runner.run_audit()
```

### Filtering Files

```python
# Audit specific paths
runner = AgentRunner(root_dir="prep")
report = await runner.run_audit(
    file_patterns=["prep/auth/*", "prep/api/*"]
)
```

## Severity Levels

Findings are classified by severity:

- **CRITICAL**: Immediate security risks (hardcoded secrets, SQL injection)
- **HIGH**: Serious issues requiring attention (command injection, destructive operations)
- **MEDIUM**: Architectural or quality issues (N+1 queries, high complexity)
- **LOW**: Style and documentation issues (missing type hints, docstrings)
- **INFO**: Informational findings

## Human-in-the-Loop

The OperationsAgent flags operations requiring human approval:
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

## Future Enhancements

Planned improvements:
- Integration with GitHub PR bot for automated reviews
- Support for more file types (JavaScript, Go)
- ML-based anomaly detection
- Custom rule configuration
- Integration with existing linters (ruff, mypy)
