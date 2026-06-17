# Persistence architecture

## PostgreSQL responsibilities

PostgreSQL is the system of record for:

- projects and workspace bindings
- conversations, user messages, and inspectable agent transcript entries
- runs and agent runs
- durable task queue and leases
- events
- approvals and interrupts
- artifacts metadata
- agent and workflow versions
- model-profile versions and resolved usage
- permission profiles and grants
- secret references and bindings, never secret values
- memory records for the initial memory adapter
- scheduler entries

LangGraph checkpoint tables may exist in the same database but remain adapter-owned.

## Transactional rules

- A child task is committed before a worker may execute it.
- Events describing a state transition are written in the same transaction as the state change.
- Outbound side effects use an outbox or equivalent idempotent dispatch mechanism.
- Leases use database time and explicit expiration.
- Mutable workspace proposals produce durable approval records before application.
- Approval decisions and their lifecycle events are committed with the approval
  state transition.
- Agent transcript entries record inspectable prompts, model-visible decisions,
  tool requests/results, approvals, errors, and final answers. Private
  chain-of-thought is not persisted.

## Data ownership

Domain tables are migration-controlled by the platform. Adapter-owned tables are isolated by schema or naming and must not be queried directly by UI or application logic.


## Migration-first evolution

The application reads and writes only the current canonical platform schema. Historical platform schemas are transformed by ordered migrations before normal process readiness.

Migration coordination must:

- use a database-backed global migration lock,
- inspect platform and adapter schema versions,
- apply platform-owned migrations without querying adapter internals,
- invoke adapter-owned migration capabilities for adapter schemas,
- record start, completion, duration, source version, target version, and failure,
- block API, worker, and scheduler readiness until successful completion,
- require backup verification for destructive or irreversible transformations,
- run post-migration invariants before serving work.

Runtime repositories must not branch on historical schema versions. Downgrade-in-place is not guaranteed; restoration from a compatible backup is the default rollback strategy.
