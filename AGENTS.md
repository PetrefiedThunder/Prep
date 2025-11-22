# Agents, Scopes, and Capabilities

This document outlines the agents utilized in this repository along with their roles, scopes, and capabilities.

## Agent System Overview

The Prep repository now features two types of agent systems:

1. **GitHub Copilot Agents** - Manual, on-demand specialized agents
2. **Automated Agent Swarm** - 100 autonomous monitoring agents (NEW)

---

## GitHub Copilot Agents

These are specialized agents that can be invoked manually for specific tasks:

1. **Security**
   - **Agent:** `@prep-security`
   - **Scope:** `Auth, Secrets, OWASP`
   - **Capability:** Patches vulnerabilities

2. **Architect**
   - **Agent:** `@prep-architect`
   - **Scope:** `API, DB, Services`
   - **Capability:** Refactors schemas/interfaces

3. **Code Quality**
   - **Agent:** `@prep-reviewer`
   - **Scope:** `Linting, Typing`
   - **Capability:** Auto-formats & types

4. **Testing**
   - **Agent:** `@prep-qa`
   - **Scope:** `Tests, Fixtures`
   - **Capability:** Generates regression tests

5. **Operations**
   - **Agent:** `@prep-ops`
   - **Scope:** `Jobs, Retries, Alerts`
   - **Capability:** Fixes broken job logic

---

## Automated Agent Swarm (100 Agents)

A comprehensive swarm of 100 autonomous agents that continuously monitor and implement all aspects of the repository.

### Quick Start

```bash
# Start the agent swarm
python scripts/run_agent_swarm.py

# Check swarm status
python scripts/run_agent_swarm.py --command status
```

### Agent Distribution

- **10 Security Monitoring Agents** - Auth, secrets, vulnerabilities
- **10 Code Quality Agents** - Linting, typing, formatting
- **10 Testing Agents** - Unit tests, integration tests, coverage
- **10 Documentation Agents** - API docs, README, inline docs
- **10 Compliance Agents** - License, privacy, accessibility
- **10 API Monitor Agents** - Endpoints, performance, errors
- **10 Database Monitor Agents** - Connections, queries, migrations
- **10 Build Monitor Agents** - Builds, deployments, workflows
- **10 Performance Monitor Agents** - Response times, resources, bottlenecks
- **10 Repository Monitor Agents** - Structure, dependencies, branches

### Documentation

For detailed information about the agent swarm system, see:
- **[docs/AGENT_SWARM.md](./docs/AGENT_SWARM.md)** - Complete agent swarm documentation
- **[agents/config/swarm_config.yaml](./agents/config/swarm_config.yaml)** - Configuration file

### Architecture

```
SwarmCoordinator → AgentSwarm → 100 Specialized Agents
                                   ├── Security (10)
                                   ├── Code Quality (10)
                                   ├── Testing (10)
                                   ├── Documentation (10)
                                   ├── Compliance (10)
                                   ├── API Monitor (10)
                                   ├── Database Monitor (10)
                                   ├── Build Monitor (10)
                                   ├── Performance Monitor (10)
                                   └── Repository Monitor (10)
```
