# Definition of Done

A feature is complete only when:

- acceptance criteria pass,
- unit tests pass,
- integration tests pass,
- adapter contract tests pass,
- architecture tests pass,
- security tests pass where relevant,
- recovery and idempotency tests pass where relevant,
- forward migrations are tested from every supported upgrade origin,
- migration restart, failure, and post-migration invariants are tested,
- destructive migrations verify backup or explicit operator acknowledgement,
- obsolete runtime branches and old representations are removed,
- any unavoidable compatibility layer has an accepted ADR, owner, telemetry, removal condition, and removal date,
- documentation is updated,
- validation evidence is recorded,
- project state and risks are updated,
- no raw secrets appear in logs, events, traces, fixtures, or snapshots,
- exact definition and profile versions are recorded for relevant runs.
