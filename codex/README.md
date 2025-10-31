# Codex Execution Contract

Codex must:
- Read task specs in `codex/tasks/*.yaml`
- Respect constraints in `codex/constraints.md`
- Use prompts in `codex/prompts/*.md` when generating or editing code
- Never introduce secrets; all credentials come from env or Helm values
- Produce code that passes `make codex-verify`

Success == all checks green:
- `make policy.build`
- `make opa.up` (sidecar in Docker)
- `make db.migrate`
- `make test`
- `make codex-verify`
