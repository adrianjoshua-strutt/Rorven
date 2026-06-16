# Evolution and migration architecture

## Core rule

Rorven supports one canonical internal model at a time. Old persisted representations are upgraded into that model before the system uses them.

This applies permanently, not only before the first stable release.

## Definition immutability

Migrations may change the storage envelope or schema of versioned definitions, but they must preserve the immutable semantic snapshot used by historical runs. A migration must not silently rewrite which prompt, policy, workflow, or model-profile version a completed run resolved.

## What is migrated

- PostgreSQL schemas and data
- project configuration
- global configuration
- versioned agent, workflow, prompt, permission, memory-policy, and model-profile definitions
- serialized runtime state where the owning adapter supports migration
- indexes and derived repository knowledge
- adapter-owned metadata

Derived data that is safe to rebuild should be regenerated instead of migrated.

## Startup sequence

```text
process starts
-> acquire migration lock
-> inspect platform and adapter schema versions
-> validate upgrade path
-> verify required backup/space/preconditions
-> apply ordered migrations
-> run post-migration invariants
-> record migration audit events
-> release lock
-> report readiness
```

API, worker, and scheduler processes must not accept normal work until the required migration version is reached. Only one migration coordinator may execute a migration set.

## Canonical-model rule

After a migration lands:

- repositories return only current domain objects,
- services accept only current commands and DTOs,
- UI consumes only current API contracts,
- old fields and fallback branches are removed in the same feature unless an approved exception exists.

A migration must not merely add a new representation while leaving all old representations indefinitely supported.

## Compatibility exceptions

Migration may be insufficient for independently deployed external clients, public protocols, rolling multi-process upgrades, or third-party files that cannot be rewritten safely.

An exception requires:

- a dedicated ADR,
- an isolated translation adapter,
- supported version range,
- usage telemetry where possible,
- owner,
- removal condition,
- removal date,
- tests proving both isolation and eventual removal.

The exception must not introduce legacy concepts into the domain layer.

## Upgrade and downgrade policy

Forward upgrades are supported through migrations from documented source versions. Downgrade-in-place is not guaranteed. Recovery from a failed or unwanted upgrade uses transaction rollback where possible or restoration of a pre-upgrade backup.

## Migration ownership

- Platform-owned tables: platform migration package
- LangGraph tables: LangGraph runtime adapter
- Memory backend tables: configured memory adapter
- Secret-store metadata: secret-store adapter
- Sandbox metadata: sandbox adapter

Adapters publish their current schema version and migration steps through a migration capability. The application migration coordinator orders platform and adapter migrations without querying adapter-owned tables directly.

## Required evidence

Each migration-producing feature records:

- supported source versions,
- transformed records and invariants,
- runtime and storage estimates where relevant,
- backup requirement,
- failure behavior,
- restart behavior,
- post-migration validation,
- proof that legacy runtime code was removed.
