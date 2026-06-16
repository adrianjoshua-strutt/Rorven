# Testing strategy

## Test layers

### Unit tests

Pure domain behavior, policy evaluation, profile resolution, memory rules, state transitions.

### Contract tests

Shared suites for every adapter port. A new adapter is not accepted until it passes the same behavioral contract as existing adapters.

### Integration tests

PostgreSQL repositories, runtime adapter, secret-store adapter, model-provider adapter, Docker sandbox, and API boundaries.

### Architecture tests

Import boundaries, forbidden dependencies, adapter registration, no provider IDs in agent definitions, no raw secret fields in domain schemas, and no historical schema/version conditionals in domain or application modules.

### Migration tests

- clean bootstrap to the latest schema
- upgrade from every supported source version
- restart during an interrupted migration
- concurrent process startup with one migration coordinator
- post-migration invariant validation
- destructive migration backup gate
- adapter-owned schema migration through adapter contracts
- proof that old runtime representations are no longer accepted
- CI failure for expired compatibility exceptions

### Recovery tests

- API termination during run
- worker termination during child task
- scheduler restart
- expired lease recovery
- resume after user interrupt
- no duplicate side effect after retry

### Security tests

- cross-project isolation
- path traversal and symlink escape
- secret exfiltration attempts
- permission escalation attempts
- unauthorized capability request
- redaction failures

### Evaluation tests

Agent quality scenarios are versioned separately from deterministic correctness tests.
