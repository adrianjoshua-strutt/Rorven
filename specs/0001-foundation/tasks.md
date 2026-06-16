# Tasks

- [ ] Accept or revise the initial ADRs that directly govern this slice: modular monolith, ports/adapters, PostgreSQL system of record, React/Vite/FastAPI, durable task leases, and migration-first evolution.
- [x] Finalize the package/module map for the first slice only.
- [x] Define current domain entities for project, run, agent run, task, event, artifact metadata, and workspace binding.
- [ ] Define the first current PostgreSQL schema and migration coordinator.
- [ ] Implement clean bootstrap plus one synthetic previous-version migration at the migration boundary.
- [ ] Add readiness gating and post-migration invariants.
- [x] Add architecture checks for forbidden provider/framework imports and historical-schema branches in domain/application code.
- [x] Define the first ports: `RunRepository`, `EventRepository`, `TaskQueue`, `AgentRuntime`, `ArtifactStore`, and `Clock`.
- [ ] Add shared contract tests for the runtime adapter and task queue behavior used by this slice.
- [ ] Scaffold the FastAPI API and worker process.
- [ ] Scaffold the React/Vite project page and run tree.
- [ ] Implement PostgreSQL repositories and durable task leases.
- [x] Implement a local deterministic `AgentRuntime` adapter that creates one parent run and two child runs through platform-owned records.
- [ ] Implement run event retrieval and UI reconstruction from persisted state.
- [ ] Implement parent join and final artifact creation.
- [ ] Add API restart, worker lease-recovery, duplicate-result, UI reload, and migration tests.
- [ ] Record validation evidence and unresolved limitations.

## Deferred tasks

- [ ] Implement the LangGraph runtime adapter.
- [ ] Implement the OpenRouter model-provider adapter.
- [ ] Implement production secret-store integration and brokered external tools.
- [ ] Implement project memory UI and backend.
- [ ] Implement Docker sandbox isolation.
