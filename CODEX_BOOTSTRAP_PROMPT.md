# Codex bootstrap prompt

Read, in order:

1. `AGENTS.md`
2. `.specify/memory/constitution.md`
3. `.project/state.yaml`
4. `.project/identity.yaml`
5. `.project/evolution.yaml`
6. `docs/product/PDD.md`
7. `docs/product/identity.md`
8. all files under `docs/architecture/`
9. all files under `docs/development/`
10. `specs/0001-foundation/`

Do not write implementation code yet.

First produce:

1. a contradiction and ambiguity report,
2. a proposed final module map,
3. any missing ADRs,
4. a dependency-ordered implementation plan for the first vertical slice,
5. the initial database and definition migration architecture,
6. the contract-test matrix for every port,
7. the threat model gaps,
8. the exact acceptance tests for crash recovery, parallel subagents, project isolation, secret non-disclosure, model-profile resolution, and automatic upgrade migration,
9. proposed architecture checks that prevent legacy compatibility branches from leaking into domain and application code.

Product identity:

- The provisional product name is **Rorven** and the canonical slug is `rorven`.
- Preserve the identifiers in `.project/identity.yaml`.
- Do not introduce themed subsystem names or rename domain ports for branding.
- Keep the codebase mechanically renameable.

Hard rules:

- Never place provider-, framework-, memory-, secret-store-, sandbox-, or runtime-specific logic outside adapters.
- Never let agents access raw secrets.
- Never make UI or API contracts depend on LangGraph internals.
- Never implement a feature without an approved specification and validation plan.
- Never change module boundaries without an ADR and architecture tests.
- Never preserve obsolete first-party data models through scattered runtime conditionals when a migration can transform the data.
- Treat backward compatibility as an exceptional, time-bounded translation adapter requiring an ADR.
- Startup must migrate to the current canonical model before normal readiness.
- Preserve a modular monolith: one repository and one database, with separate API, worker, and scheduler processes.
