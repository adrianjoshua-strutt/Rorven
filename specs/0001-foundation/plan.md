# Implementation plan

## Slice

Implement one complete path:

```text
React project page
-> FastAPI command
-> migration preflight and current PostgreSQL schema
-> PostgreSQL run and task records
-> AgentRuntime adapter
-> parent orchestrator
-> two durable child runs
-> persisted join
-> final artifact
-> live and reloadable UI state
```

## Required ports

- RunRepository
- EventRepository
- TaskQueue
- AgentRuntime
- ModelGateway
- ModelProvider
- ArtifactStore
- Clock

## Required adapters

- PostgreSQL migration coordinator, repositories, and queue
- LangGraph runtime
- OpenRouter model provider
- local filesystem artifact store
- system clock

## Required tests

- architecture import tests
- shared runtime adapter contract
- shared model-provider contract
- API integration test
- parallel child-run test
- API restart test
- worker lease-recovery test
- duplicate-side-effect protection test using a synthetic tool
- UI reload reconstruction test
- clean-start and previous-schema automatic migration tests
- migration lock and failed-migration readiness tests
