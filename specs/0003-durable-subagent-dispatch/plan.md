# Plan

## Implemented Slice

1. Add a typed application dispatch contract and parser.
2. Add approved reviewer and implementer definitions with model-profile references only.
3. Change root worker execution to request a dispatch decision.
4. Persist child assignments, child agent runs, and child tasks.
5. Mark root runs waiting while child work is active.
6. Join completed child results through a root summary call.
7. Fail malformed dispatches and child failures explicitly.
8. Show assignment artifacts in subagent inspection.

## Next Slices

1. Move agent definitions and workflow versions into immutable definition storage.
2. Add permission-profile evaluation for brokered tools.
3. Add a read-only workspace inspection tool through a sandbox adapter.
4. Replace local JSON persistence with Postgres repositories and migrations.
