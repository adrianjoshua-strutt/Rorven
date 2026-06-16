# ADR 0013: Prefer migration over backward-compatibility layers

Status: Accepted  
Date: 2026-06-16

## Context

Long-lived products often accumulate branches for historical schemas, configuration formats, event shapes, model definitions, and persisted state. Such branches increase test combinations, obscure the canonical model, and can prevent early users from receiving newer behavior.

Rorven controls its first-party persistence, configuration, and stored definitions. It can therefore transform them to the current canonical representation during upgrade instead of carrying indefinite legacy behavior in runtime code.

## Decision

Rorven follows a permanent **migration-first, current-model-only** evolution policy.

1. Runtime, domain, application, and UI code target the current canonical model.
2. Persisted data, configuration, definitions, and adapter-owned metadata are migrated before normal use.
3. Startup performs a migration preflight and applies all required ordered migrations before API, worker, or scheduler readiness is reported.
4. A migration failure blocks startup and must not silently fall back to legacy behavior.
5. Destructive or irreversible migrations require backup verification or an explicit operator acknowledgement.
6. Runtime branches such as `if schema_version < ...`, dual-read, dual-write, legacy DTOs, and old-model adapters are prohibited by default.
7. A backward-compatibility layer is allowed only when migration cannot reasonably solve the problem, commonly because an external consumer or protocol cannot be upgraded atomically.
8. Every compatibility exception requires an ADR containing scope, owner, rationale, telemetry, removal condition, and latest removal date.
9. Compatibility code must be isolated behind a dedicated adapter or translation boundary and must never spread through the domain model.

## Migration properties

Migrations must be:

- ordered and uniquely identified,
- repeat-safe or transactionally guarded,
- observable and auditable,
- tested from every supported upgrade origin,
- resumable or safely restartable,
- explicit about rollback or restore strategy,
- separate for platform-owned and adapter-owned schemas.

## Consequences

Positive:

- The runtime has one canonical representation.
- New features are not withheld from early users because their stored data is old.
- Test matrices remain bounded.
- Legacy complexity is removed rather than normalized.

Negative:

- Upgrade correctness becomes a critical operational capability.
- Some upgrades may take longer or require backups and maintenance windows.
- Downgrades are not guaranteed and generally require restoring a compatible backup.

## Enforcement

- Architecture tests reject version-conditionals in domain and application modules.
- Every persistence-affecting feature includes migration and upgrade tests.
- Definition of Done requires current-model cleanup after migration.
- Compatibility exceptions are searchable and fail CI after their removal date.
