# Real Project Execution

Status: active

## Goal

Project chat must perform real durable work. A user message creates a project run, persists a root orchestrator agent run, queues one executable task, lets a worker call the configured model gateway, stores the model response as an artifact, and completes the run.

This slice replaces the previous placeholder direction. It must not fabricate reviewer, implementer, or other subagent work.

## Requirements

- Project submission creates exactly one root orchestrator `AgentRun` and one queued `Task`.
- Worker execution leases that task, sends the request through `ModelGateway`, stores a text artifact, completes the task, completes the root agent run, and completes the run.
- Product composition uses `LangGraphAgentRuntime` and `OpenRouterModelGateway`.
- Missing `RORVEN_OPENROUTER_API_KEY` is a startup/configuration error for model-backed processes.
- Tests may use service-level test gateways or patched adapter calls, but no local product gateway or local deterministic runtime may be registered in composition.
- Root project activities and project subagent lists show only persisted real activity. They must not synthesize projects, reviewers, implementers, or status cards.

## Non-Goals

- Explicit child/subagent dispatch.
- Filesystem, shell, git, browser, or other brokered tools.
- Sandbox enforcement.
- Project memory.
- Postgres repository implementation.
- Autonomous overnight execution.

## Acceptance

- Backend tests prove persistence across reopen, API submission, worker execution, root chat persistence, settings safety, and runtime contract behavior.
- Frontend build succeeds against the current API contract.
- Architecture docs and project state describe the real limitations plainly.
