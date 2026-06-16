# Rorven

Rorven is a self-hosted, durable, modular platform for long-running multi-agent project work.

This repository currently contains the product and architecture foundation. The first implementation target is a durable walking skeleton: small enough to finish, but real enough to prove ports, adapters, persisted runs, worker recovery, migrations, and UI reconstruction.

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
10. `specs/0001-foundation/spec.md`

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

## Bootstrap with Codex

Open this folder in VS Code and give Codex the prompt in `CODEX_BOOTSTRAP_PROMPT.md`. Agents should work in small validated steps, update the active feature evidence, and preserve the adapter boundaries rather than wiring providers directly into core code.

## Product identity

Canonical development identifiers are centralized in `.project/identity.yaml`. Branding must not leak into domain objects, database tables, event types, API paths, ports, or adapter contracts.
