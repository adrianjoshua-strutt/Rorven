# Agent instructions

## Required reading

Before changing code or documentation, read:

1. `.specify/memory/constitution.md`
2. `.project/state.yaml`
3. `.project/identity.yaml`
4. `.project/evolution.yaml`
5. `docs/product/identity.md`
6. `docs/architecture/README.md`
7. `docs/architecture/evolution-and-migrations.md`
8. the active feature dossier under `specs/`

## Normative precedence

When sources conflict, use this order:

1. Constitution
2. Accepted ADRs
3. Approved feature specification
4. Architecture documentation
5. Project state
6. Agent memory
7. Chat history

Agent memory and chat history are never normative project truth.

## Mandatory engineering rules

- The provisional product name is Rorven; use identifiers from `.project/identity.yaml`.
- All replaceable infrastructure is accessed through domain-owned ports.
- New external behavior extends an existing adapter, adds a new adapter, or introduces a new port through an ADR.
- No provider-specific imports are allowed in domain, application, API contracts, UI contracts, or agent definitions.
- No raw secret value may enter prompts, messages, checkpoints, memory, events, traces, logs, artifacts, or UI state.
- Agents request only a model profile. They never select model IDs or provider parameters.
- Agent definitions, workflows, prompts, permission profiles, model profiles, and memory policies are immutable and versioned.
- Destructive or externally visible actions require explicit policy evaluation and, where configured, approval.
- Runtime code targets only the current canonical data and configuration model.
- Prefer automatic, versioned migration of first-party data over backward-compatibility branches.
- Do not introduce dual-read, dual-write, legacy DTO, old-schema, or version-conditional runtime paths without an accepted exception ADR.
- Every compatibility exception must be isolated, have an owner, telemetry where practical, a removal condition, and a latest removal date.
- Every persistence-affecting feature must include startup/upgrade migration tests and prove that obsolete runtime code was removed.
- Every feature must have specification, plan, tests, validation evidence, and documentation updates.
- Every adapter must pass a shared contract-test suite.
- Do not mark work complete when validation evidence is missing.

## Completion sequence

1. Run unit, integration, contract, architecture, migration, recovery, and security tests relevant to the change.
2. Update the feature validation document with evidence.
3. Update affected architecture documentation.
4. Add or supersede ADRs where needed.
5. Update `.project/state.yaml` and `.project/risks.yaml`.
6. Remove obsolete compatibility code and old representations unless an approved exception applies.
7. Record unresolved limitations explicitly.
