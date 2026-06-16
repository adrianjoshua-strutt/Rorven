# Module boundaries

## Dependency rule

Dependencies point inward:

```text
UI/API adapters -> application -> domain
Infrastructure adapters -> application ports/domain ports
```

The domain layer has no framework imports.

## Proposed repository modules

```text
apps/
  web/
  api/
  worker/
  scheduler/

packages/
  domain/
  application/
  contracts/
  agent-runtime/
  permissions/
  tools/
  memory/
  models/
  secrets/
  sandboxes/
  artifacts/
  persistence/
  observability/

adapters/
  runtime/langgraph/
  models/openrouter/
  memory/postgres/
  secrets/<initial-store>/
  sandbox/docker/
  artifacts/filesystem/
  persistence/postgres/
```

## Forbidden imports

`domain` and `application` must not import:

- LangGraph or LangChain
- FastAPI
- SQLAlchemy or PostgreSQL drivers
- OpenRouter or model-provider SDKs
- secret-store SDKs
- Docker SDK
- React or frontend packages

## Ports

First-slice ports:

- `AgentRuntime`
- `ArtifactStore`
- `RunRepository`
- `EventRepository`
- `TaskQueue`
- `Clock`

Planned platform ports:

- `ModelGateway`
- `ModelProvider`
- `MemoryBackend`
- `SecretStore`
- `CredentialBroker`
- `PermissionEngine`
- `ToolExecutor`
- `SandboxProvider`

Ports should remain small. Provider-specific optional features use capability interfaces rather than widening every implementation.
