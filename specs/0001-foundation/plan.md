# Implementation plan

## Slice

Implement one complete path:

```text
React project page
-> FastAPI command
-> migration preflight and current PostgreSQL schema
-> PostgreSQL run and task records
-> AgentRuntime adapter
-> deterministic parent orchestrator
-> two durable local child runs
-> persisted join
-> final artifact
-> live and reloadable UI state
```

This is a walking skeleton, not a throwaway proof of concept. It must use the same module boundaries, ports, repository interfaces, run/event model, task leases, and validation habits that later LangGraph/OpenRouter-backed agents will use.

The first runtime adapter may be local and deterministic so durability, recovery, project isolation, and UI reconstruction can be proven before model/provider behavior is introduced. LangGraph and OpenRouter stay behind accepted adapter decisions and are implemented in later slices.

## Required ports

- RunRepository
- EventRepository
- TaskQueue
- AgentRuntime
- ArtifactStore
- Clock

## Deferred ports

These remain part of the architecture but are not required for the first executable slice:

- ModelGateway
- ModelProvider
- MemoryBackend
- SecretStore
- CredentialBroker
- PermissionEngine
- SandboxProvider

## Required adapters

- PostgreSQL migration coordinator, repositories, and queue
- local deterministic runtime adapter
- local filesystem artifact store
- system clock

## Deferred adapters

- LangGraph runtime
- OpenRouter model provider
- PostgreSQL memory backend
- secret-store adapter
- Docker sandbox adapter

## Required tests

- architecture import tests
- shared runtime adapter contract for the local adapter
- shared task queue behavior tests
- API integration test
- parallel child-run test
- API restart test
- worker lease-recovery test
- duplicate-result protection test using synthetic child work
- UI reload reconstruction test
- clean-start and previous-schema automatic migration tests
- migration readiness test
