# Feature 0001 — Foundation and durable vertical slice

Status: Draft

## Problem

The project needs a production-grade foundation before agent features are expanded. The first implementation must demonstrate architecture boundaries, durability, parallel subagents, project isolation, and observability.

## User story

As a user, I can create a project bound to a workspace, send a task to its orchestrator, observe two parallel child agents, restart the API or a worker, reopen the project, and receive a final persisted result.

## Acceptance criteria

1. A project can be created and bound to an allowed workspace root.
2. A project conversation can create a durable parent run.
3. The parent can create at least two child agent runs in parallel.
4. Child work is stored before execution and leased by workers.
5. Closing the browser does not stop execution.
6. Restarting the API does not lose state.
7. Terminating a worker causes recoverable work to be reclaimed after lease expiry.
8. The parent resumes only after the durable join condition is satisfied.
9. The UI can reconstruct the run tree from persisted state and events.
10. No raw secret value is required for the demonstration.
11. Model calls use one abstract profile and the OpenRouter adapter.
12. Domain and application code contain no LangGraph or OpenRouter imports.
13. Architecture tests enforce the import boundaries.
14. Validation evidence is recorded before completion.
15. Startup automatically migrates a synthetic older platform schema to the current schema before reporting readiness.
16. Domain and application code contain no branch that supports the synthetic historical schema.
17. A failed migration blocks readiness and leaves a recoverable database state.

## Non-goals

- Full memory system.
- Production secret-store integration.
- Large agent registry.
- Distributed multi-host execution.
- Complete visual design.
