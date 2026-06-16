# Runtime architecture

## Principle

LangGraph is an implementation detail behind `AgentRuntime`. The platform owns run IDs, agent-run IDs, parent-child relationships, task records, events, budgets, approvals, and artifacts.

The current runtime adapter uses LangGraph behind `AgentRuntime`. There is no product fallback runtime. Tests may inject in-memory fakes at service boundaries, but composition must create the same graph-backed runtime used by the API and worker.

## Parent-child execution

Each project message creates a durable run and one root orchestrator `agent_run` before execution begins. A task is queued for that root agent. A worker leases the task and asks the orchestrator for a structured dispatch decision through the model gateway.

The orchestrator may answer directly or dispatch approved child subagents. Dispatch is represented as provider-neutral JSON parsed in the application layer. The platform persists child assignments as artifacts, creates child `agent_run` records and tasks, marks the parent run waiting, then lets workers execute the child tasks. When all child runs complete, the root orchestrator summarizes their artifacts and completes the run.

The platform only creates child runs from a real orchestrator dispatch decision, not from hardcoded reviewer/implementer placeholders.

An agent run contains:

- project ID
- parent agent-run ID
- agent-definition version
- workflow version
- model-profile version
- permission-profile version
- memory-policy version
- runtime thread/checkpoint reference
- status
- heartbeat and lease metadata
- input and result artifact references
- usage and cost

## Parallel work

The orchestrator can create multiple child runs in one repository transaction. Workers lease them independently. A durable join condition determines when the parent becomes summarizable again.

The current implementation supports reviewer and implementer child runs. Tool authority, sandbox execution, broad agent catalogs, and permission-profile evaluation remain separate slices.

## Recovery

- Worker leases expire after missed heartbeats.
- Recoverable work returns to the queue.
- Side-effecting tool calls use idempotency keys.
- Parent runs wait on persisted child states, not in-memory Python futures.
- Runtime checkpoints are mapped to platform run IDs but are not the platform domain model.

## Interrupts

Interrupts are first-class records with type, requested input, target user, status, response, and resume token/reference.
