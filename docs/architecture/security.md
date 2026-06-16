# Security architecture

## Security goals

- No ambient host credentials.
- No workspace escape.
- No unauthorized external side effects.
- No raw secret disclosure.
- Auditable decisions and tool executions.
- Controlled network access.
- Recoverable operations without duplicate side effects.

## Required controls

- sandbox per project run or compatible isolation boundary
- least-privilege filesystem mounts
- network policy or destination allowlists
- central tool broker
- deny-by-default permission engine
- explicit approvals for destructive or externally visible actions
- secret broker and workload identity
- token, cost, time, and concurrency limits
- global kill switch
- immutable audit events

## Threats to test

- prompt injection requesting secret access
- agent reading host home directory
- symlink escape from project root
- command output leaking credentials
- retry duplicating Git push or external write
- child agent inheriting parent permissions incorrectly
- project A reading project B memory or secrets
- provider-specific request metadata leaking into persisted state
