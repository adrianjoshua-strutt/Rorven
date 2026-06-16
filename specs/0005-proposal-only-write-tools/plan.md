# Plan

## Implemented Slice

1. Extend tool policy support for proposal-only text writes.
2. Extend the local workspace broker with unified-diff proposals.
3. Teach prompts that write proposals are not applied edits.
4. Add adapter and worker tests proving no mutation occurs.

## Next Slices

1. Add approval records and UI for mutable actions.
2. Add an apply-approved-diff tool with idempotency keys.
3. Add sandbox isolation around apply.
4. Add recovery tests for interrupted apply operations.
