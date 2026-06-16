# Rorven

Rorven is a self-hosted, durable, modular platform for long-running multi-agent project work.

This repository contains the product and architecture foundation plus the first real execution slice: project messages create durable orchestrator work, workers call the configured OpenRouter model gateway, and results are persisted back into the project run.

> Rorven is a provisional development name. It may be used for the public source repository, but no trademark exclusivity is claimed.

## Read first

1. `AGENTS.md`
2. `.specify/memory/constitution.md`
3. `.project/state.yaml`
4. `.project/identity.yaml`
5. `.project/evolution.yaml`
6. `docs/product/PDD.md`
7. `docs/product/identity.md`
8. `docs/architecture/README.md`
9. `docs/architecture/evolution-and-migrations.md`
10. `specs/0003-durable-subagent-dispatch/spec.md`

## Core idea

Rorven owns projects, agents, permissions, secrets, memory, runs, artifacts, model profiles, APIs, and UI concepts. Replaceable technologies such as LangGraph, OpenRouter, a secret store, a memory backend, a sandbox provider, or an object store are integrated only through adapters.

The system targets one current canonical model. Updates migrate first-party data and configuration before startup instead of accumulating historical behavior throughout runtime code.

## Initial target stack

- React + Vite + TypeScript
- FastAPI + Python
- PostgreSQL
- LangGraph behind an `AgentRuntime` adapter
- OpenRouter behind a `ModelProvider` adapter
- Self-hosted secret store behind a `SecretStore` adapter
- Docker-based project sandboxes
- API, worker, and scheduler as separate processes in one modular monolith

## Run with OpenRouter

Rorven loads a root `.env` file for local API and worker processes. Create `.env` from
`.env.example`, then set:

```powershell
RORVEN_OPENROUTER_API_KEY=sk-or-v1-...
```

Optional model-profile pins can be set with:

```powershell
RORVEN_MODEL_PROFILE_BALANCED=provider/model-id
RORVEN_MODEL_PROFILE_REASONING=provider/model-id
```

If no profile model is pinned, the OpenRouter adapter omits `model` and lets the
provider route the request. Without `RORVEN_OPENROUTER_API_KEY`, the API and worker
refuse to start the model gateway.

The current worker executes durable project-orchestrator tasks, can dispatch real
reviewer/implementer subagent tasks from a structured orchestrator decision, stores
assignments and results as artifacts, and summarizes completed child work. This is
not yet a tool-capable coding agent: filesystem, shell, sandbox, memory, and
brokered tool execution are separate slices.

Local development uses three processes:

```powershell
$env:PYTHONPATH="src;apps/api;apps/worker"
.venv\Scripts\python.exe -m uvicorn rorven_api.main:create_app --factory --reload
```

```powershell
$env:PYTHONPATH="src;apps/api;apps/worker"
.venv\Scripts\python.exe -m rorven_worker.main --loop
```

```powershell
cd apps/web
npm.cmd run dev
```

## Bootstrap with Codex

Open this folder in VS Code and give Codex the prompt in `CODEX_BOOTSTRAP_PROMPT.md`. Agents should work in small validated steps, update the active feature evidence, and preserve the adapter boundaries rather than wiring providers directly into core code.

## Product identity

Canonical development identifiers are centralized in `.project/identity.yaml`. Branding must not leak into domain objects, database tables, event types, API paths, ports, or adapter contracts.
