# Test plan

## Architecture

- Domain imports no framework or provider package.
- Application imports no adapter package.
- Agent definitions contain only model-profile names.

## Durability

- Kill API during run and restart.
- Kill child worker after lease and before completion.
- Verify task reclaim and single final child result.
- Close browser and reconnect.

## Parallelism

- Spawn two child runs.
- Verify concurrent leases.
- Verify parent waits for both.

## Isolation

- Deny workspace paths outside configured root.
- Deny project A access to project B records.

## Observability

- Verify lifecycle events for created, queued, leased, started, interrupted, completed, failed, and resumed states.


## Migrations

- Start from an empty database and reach the current schema.
- Start from a versioned synthetic previous schema and migrate automatically.
- Start API and worker concurrently and verify that only one migration coordinator executes.
- Fail a migration intentionally and verify no process reports ready.
- Restart after a recoverable migration interruption.
- Verify post-migration invariants and removal of the old representation.
- Verify domain and application code do not branch on the old schema version.
