# Durable Subagent Dispatch

Status: active

## Goal

The project orchestrator can split a project request into real persisted child-agent work. Child runs must be created only from a structured model decision, must have persisted assignments, and must complete through the same worker queue as root tasks.

## Requirements

- Root orchestrator worker calls use a provider-neutral JSON contract.
- The contract supports direct answers and child dispatch.
- Child dispatch is limited to approved application definitions: `reviewer` and `implementer`.
- Each child receives a persisted text assignment artifact referenced by `input_artifact_id`.
- Child `AgentRun` records and child `Task` records are persisted before workers can execute them.
- The parent run moves to `waiting` while child tasks are active.
- When all children complete, the root orchestrator summarizes child result artifacts and completes the run.
- Malformed root dispatch output fails the root task and run instead of leaving durable state in limbo.
- Failed child work fails the parent run.
- UI subagent inspection shows the persisted assignment and result artifact content.

## Non-Goals

- Filesystem, shell, git, browser, or sandbox tools.
- Autonomous code editing.
- Broad agent catalog management.
- External versioned definition storage.
- Postgres repository implementation.
- Root-project project-management tools.

## Acceptance

- Backend tests cover direct answer, child dispatch, join summary, malformed dispatch failure, persistence, API integration, and architecture boundaries.
- Frontend build succeeds against the current API contract.
- Docs and project state no longer claim explicit subagent dispatch is missing.
