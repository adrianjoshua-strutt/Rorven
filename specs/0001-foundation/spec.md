# Feature 0001 - Durable walking skeleton

Status: Draft

## Problem

The project needs a small working system that proves the core architecture without pretending to be the finished platform. The first implementation should be real enough for agents to iterate on: durable state, explicit boundaries, reloadable UI, and a worker model that can recover from process loss.

The slice must keep the adapter-first architecture. It should not bake LangGraph, OpenRouter, PostgreSQL driver details, filesystem artifacts, or any future provider into domain or application code. It also should not require every planned adapter to be production-ready before the first loop works.

## User story

As a user, I can create a project bound to an allowed workspace, submit a task, observe a parent run with two child runs, close and reopen the UI, restart a worker, and still receive a persisted final result.

## Acceptance criteria

1. A project can be created and bound to an allowed workspace root.
2. A task submission creates a durable parent run.
3. The parent creates at least two durable child runs in one committed transition.
4. Child work is stored before execution and leased by workers through a `TaskQueue` port.
5. Closing the browser does not stop execution.
6. Restarting the API does not lose project, run, task, event, or artifact metadata.
7. Terminating a worker causes recoverable work to be reclaimed after lease expiry without duplicate final child results.
8. The parent resumes only after the durable join condition is satisfied.
9. The UI can reconstruct the run tree from persisted state and events.
10. No raw secret value is required for the demonstration.
11. Agent definitions and run records use model profiles only; no concrete model IDs appear in agent definitions.
12. The first child work may use a local deterministic runtime adapter. LangGraph remains the planned production runtime adapter, not a prerequisite for this slice.
13. Domain and application code contain no LangGraph, OpenRouter, FastAPI, SQLAlchemy, PostgreSQL driver, React, Docker, or secret-store imports.
14. Architecture tests enforce the import boundaries.
15. Startup applies the current platform schema before readiness.
16. A synthetic previous-schema migration is specified and tested at the migration boundary, but runtime code targets only the current model.
17. Validation evidence is recorded before completion.

## Non-goals

- Full memory system.
- Production secret-store integration.
- Real external model calls.
- Production LangGraph runtime behavior.
- Large agent registry.
- Distributed multi-host execution.
- Complete visual design.
- General-purpose workflow builder.
