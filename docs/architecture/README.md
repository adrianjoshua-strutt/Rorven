# Architecture index

## Style

The system is a modular monolith using ports and adapters.

## Stable platform concepts

- Projects
- Conversations
- Runs and agent runs
- Agent definitions and workflows
- Permissions and capabilities
- Secret references and bindings
- Model profiles
- Memory records and policies
- Artifacts
- Events and approvals

## Replaceable subsystems

- Agent runtime
- Model provider
- Memory backend
- Secret store
- Sandbox provider
- Artifact store
- Event transport
- Scheduler and task queue implementation

The first implementation slice should exercise real ports and adapters without requiring every planned subsystem to be production-ready. Deferred adapters stay behind the same boundaries and are added when their feature slice needs them.

## Initial process topology

- `web`: React/Vite static application using Mantine for component primitives
- `api`: FastAPI control plane
- `worker`: durable agent and tool execution
- `scheduler`: delayed and recurring work
- `postgres`: system of record and queue foundation
- optional reverse proxy for TLS and routing

For local single-machine operation, the API starts an embedded worker supervisor by
default. It calls the same application `WorkerService` as the standalone worker
entrypoint, so queued project work progresses without a second process while the
separate worker topology remains available for production isolation and scaling.

## Source organization

- The web app entrypoint only mounts React providers and the top-level app.
- Console behavior is split into screen components, layout components, chat components, settings components, controller hooks, typed utilities, and API contracts.
- The API app factory only assembles middleware and routes. Request schemas, response serializers, and route handlers live in separate modules.
- Long-running chat and subagent transcripts must stay inside fixed-height scroll regions and wrap long content inside their pane.

## Required architecture documents

- `system-context.md`
- `module-boundaries.md`
- `runtime.md`
- `persistence.md`
- `permissions-and-secrets.md`
- `memory.md`
- `model-layer.md`
- `security.md`
- `evolution-and-migrations.md`
- `decisions/`

## Product identity boundary

The provisional product name is **Rorven**, but product branding does not alter domain ports, persistence names, event types, API contracts, or adapter contracts. Canonical identifiers live in `.project/identity.yaml`; the rationale and naming rules live in `docs/product/identity.md`.
