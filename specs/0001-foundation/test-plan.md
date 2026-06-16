# Test plan

## Architecture

- Domain imports no framework or provider package.
- Application imports no adapter package.
- Agent definitions contain only model-profile names.
- Domain and application contain no historical-schema branches.
- UI contracts do not expose runtime-adapter internals.

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
- Start API and worker concurrently and verify readiness waits for migration completion.
- Verify post-migration invariants and removal of the old representation.
- Verify domain and application code do not branch on the old schema version.

## Deferred test areas

These are required before their corresponding adapters ship, but not before the walking skeleton:

- OpenRouter model-provider contract tests.
- LangGraph runtime recovery contract tests.
- Secret-store and credential-broker security tests.
- Docker sandbox escape tests.
- Memory backend contract tests.
