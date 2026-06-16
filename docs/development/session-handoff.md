# Session Handoff - 2026-06-16

This note is operational context for the next agent. It does not override the constitution, ADRs, active specs, or architecture docs.

## Current Direction

The old `specs/0001-foundation` dossier was removed because it encouraged synthetic behavior. The active dossier is now `specs/0002-real-project-execution`.

The product should keep the adapter-based architecture, but product composition must not use local deterministic model/runtime shims to make a demo look alive.

## Implemented This Session

- Product composition now creates `LangGraphAgentRuntime` only.
- The local deterministic runtime adapter was deleted.
- The local model gateway adapter was deleted.
- Project message submission now creates a durable run, root orchestrator `AgentRun`, and queued `Task`.
- `WorkerService.work_once()` now leases that task, calls `ModelGateway`, persists the response artifact, completes the task, completes the root agent, and completes the run.
- Tests were rewritten so project runs expect one real root orchestrator task, not fabricated reviewer/implementer subagents.
- Root dashboard activity remains empty unless real root activities are persisted.
- Architecture docs and `.project/state.yaml` now describe the real limits.

Implementation commit: `597486a`.

## Validation

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest discover -s tests
```

Result: 23 tests passed.

```powershell
cd apps/web
npm.cmd run build
```

Result: build passed.

## Still Not Done

- No explicit orchestrator child-dispatch contract.
- No policy-gated subagent creation.
- No brokered filesystem, shell, git, browser, or sandbox tools.
- No Postgres repository implementation.
- No project memory implementation.
- The root project can call the model gateway, but cannot yet autonomously create projects through brokered project-management tools.

## Next Best Slice

Implement real orchestrator dispatch:

1. Define the provider-neutral dispatch output contract.
2. Add an application service that validates dispatch decisions against policy.
3. Persist child `AgentRun` records and tasks transactionally.
4. Extend worker join behavior so the root orchestrator can summarize child results.
5. Add contract, recovery, and API tests before exposing the UI as autonomous subagent work.
