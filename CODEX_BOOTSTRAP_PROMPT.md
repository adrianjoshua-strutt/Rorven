# Codex bootstrap prompt

You are working in the Rorven repository. Rorven is a provisional product name; keep the canonical identifiers in `.project/identity.yaml` and do not leak branding into domain, persistence, event, API, port, or adapter contracts.

## Read first

Read these before changing code or documentation:

1. `AGENTS.md`
2. `.specify/memory/constitution.md`
3. `.project/state.yaml`
4. `.project/identity.yaml`
5. `.project/evolution.yaml`
6. `docs/product/identity.md`
7. `docs/architecture/README.md`
8. `docs/architecture/evolution-and-migrations.md`
9. the active feature dossier under `specs/`

Read additional architecture, development, ADR, or product docs only when they affect the change you are making.

## How to work

1. Identify the active feature from `.project/state.yaml`.
2. Read that feature's `spec.md`, `plan.md`, `tasks.md`, `test-plan.md`, and `validation.md`.
3. Make the smallest useful change that advances the active feature.
4. Preserve the modular architecture: domain/application code must stay provider-, framework-, runtime-, database-, secret-store-, sandbox-, and UI-agnostic.
5. Prefer adding or exercising a port/adapter boundary over wiring a provider directly into core code.
6. Run the relevant tests or checks for the change.
7. Update the feature validation evidence with what passed, what was not run, and any unresolved limitation.
8. Update project state, risks, ADRs, or architecture docs only when the change makes them stale.

## Current slice

The active feature is a durable walking skeleton, not a throwaway proof of concept and not the finished platform.

The first implementation should prove:

- project creation and workspace binding,
- durable parent and child run records,
- worker leasing and recovery,
- persisted events and artifacts,
- reloadable UI reconstruction,
- migration to the current schema before readiness,
- architecture tests that protect domain/application boundaries.

The first runtime adapter may be local and deterministic. LangGraph, OpenRouter, production secrets, memory, and sandboxing remain adapter-backed architecture decisions, but they are deferred until the walking skeleton proves the platform loop.

## Hard rules

- Agents request model profiles only; they never select concrete model IDs or provider parameters.
- Raw secret values must not enter prompts, messages, checkpoints, memory, events, traces, logs, artifacts, fixtures, or UI state.
- Externally visible or destructive actions require policy evaluation and approval where configured.
- Runtime code targets only the current canonical data and configuration model.
- Do not add dual-read, dual-write, legacy DTO, old-schema, or version-conditional runtime paths without an accepted exception ADR.
- Do not mark work complete without validation evidence.
