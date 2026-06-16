# Plan

## Implemented Slice

1. Add provider-neutral tool request, decision, and result objects.
2. Add `ToolPolicy` and `ToolBroker` ports.
3. Add `WorkspaceReadPolicy`.
4. Add `LocalWorkspaceToolBroker`.
5. Extend child worker execution to parse one round of tool calls.
6. Persist tool execution artifacts and lifecycle events.
7. Keep root orchestrators blocked from workspace tools.

## Next Slices

1. Add approval records and UI for mutable actions.
2. Add sandbox-backed edit proposal tools.
3. Add diff artifacts and idempotency keys.
4. Add recovery tests around interrupted tool execution.
