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

## Next Slices

1. Add idempotency keys and recovery tests for interrupted apply operations.
2. Add sandbox isolation around apply.
3. Add multi-file patch proposals only after approval and recovery semantics are proven.
