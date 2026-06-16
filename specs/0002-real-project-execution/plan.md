# Plan

## Implemented Slice

1. Remove product-local model and runtime shims.
2. Keep `AgentRuntime` as the runtime port, backed by LangGraph in composition.
3. Submit project messages as durable root orchestrator runs.
4. Queue a task for the root orchestrator agent.
5. Let the worker lease the task, call `ModelGateway`, persist an artifact, and complete the run.
6. Update tests that previously asserted fabricated subagents.

## Next Slices

1. Define the orchestrator dispatch output contract for real child agents.
2. Add policy evaluation before child task creation.
3. Add brokered tools and sandbox authority before any agent can inspect or mutate files.
4. Move persistence from local JSON to Postgres with startup migration tests.
5. Add recovery tests for interrupted root and child task execution.
