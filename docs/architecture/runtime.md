# Runtime architecture

## Principle

LangGraph is an implementation detail behind `AgentRuntime`. The platform owns run IDs, agent-run IDs, parent-child relationships, task records, events, budgets, approvals, and artifacts.

The first walking skeleton may use a local deterministic `AgentRuntime` adapter. That adapter is not a shortcut around the architecture; it exists to prove platform-owned durability, worker leasing, parent-child joins, and UI reconstruction before model-provider behavior is introduced.

## Parent-child execution

Each spawned agent creates a durable `agent_run` record before execution begins.

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

The orchestrator may create multiple child runs in one transaction. Workers lease them independently. A durable join condition determines when the parent becomes runnable again.

## Recovery

- Worker leases expire after missed heartbeats.
- Recoverable work returns to the queue.
- Side-effecting tool calls use idempotency keys.
- Parent runs wait on persisted child states, not in-memory Python futures.
- Runtime checkpoints are mapped to platform run IDs but are not the platform domain model.

## Interrupts

Interrupts are first-class records with type, requested input, target user, status, response, and resume token/reference.
