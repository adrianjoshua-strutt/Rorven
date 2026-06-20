# Plan

## Implemented Slice

1. Extend tool policy support for proposal-only text writes.
2. Extend the local workspace broker with unified-diff proposals.
3. Teach prompts that write proposals are not applied edits.
4. Add adapter and worker tests proving no mutation occurs.
5. Add durable approval records for proposed text-file writes.
6. Add approved API application through the workspace broker.
7. Add durable agent transcript entries for user messages, assignments, tool
   results, approvals, and final answers.
8. Add console approval ingestion and approve/reject controls in the subagent
   work view.
9. Add an API-managed local worker supervisor so local project chat progresses
   without manually starting a separate worker process.
10. Allow child agents to use bounded multi-round workspace tools, so they can
    inspect files before proposing text changes.
11. Render project chat as root user/orchestrator turns and surface subagent
    work as inspectable returned work instead of blending assignments into the
    main conversation.

## Next Slices

1. Add idempotency keys and recovery tests for interrupted apply operations.
2. Add sandbox isolation around apply.
3. Add multi-file patch proposals only after approval and recovery semantics are proven.
