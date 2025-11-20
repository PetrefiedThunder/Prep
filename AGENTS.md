# Agents, Scopes, and Capabilities

This document outlines the agents utilized in this repository along with their roles, scopes, and capabilities.

## Agents List

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
