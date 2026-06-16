# Plan

## Implemented Slice

1. Extend tool policy support for proposal-only text writes.
2. Extend the local workspace broker with unified-diff proposals.
3. Teach prompts that write proposals are not applied edits.
4. Add adapter and worker tests proving no mutation occurs.
5. Add durable approval records for proposed text-file writes.
6. Add approved API application through the workspace broker.

## Next Slices

1. Add UI for reviewing, approving, and rejecting proposal approvals.
2. Add idempotency keys and recovery tests for interrupted apply operations.
3. Add sandbox isolation around apply.
4. Add multi-file patch proposals only after approval and recovery semantics are proven.
