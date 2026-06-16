# Tasks

- [x] Remove local deterministic runtime adapter from product composition.
- [x] Remove local model gateway from product composition.
- [x] Queue root orchestrator tasks on project submission.
- [x] Execute root project tasks through `ModelGateway`.
- [x] Persist worker artifacts and completion events.
- [x] Update tests away from fabricated reviewer/implementer runs.
- [x] Update architecture and state docs for the real execution slice.
- [x] Add explicit orchestrator child-dispatch contract. Superseded by `0003-durable-subagent-dispatch`.
- [x] Add policy-gated child task creation. Superseded by `0003-durable-subagent-dispatch` for reviewer/implementer dispatch validation.
- [ ] Add brokered project tools and sandbox execution.
- [ ] Replace local JSON persistence with Postgres repositories and migrations.
