# Session Handoff - 2026-06-16

This note is operational context for the next agent. It does not override the constitution, ADRs, active specs, or architecture docs.

## Current Direction

The old `specs/0001-foundation` dossier was removed because it encouraged synthetic behavior. The active dossier is now `specs/0003-durable-subagent-dispatch`.

The product should keep the adapter-based architecture, but product composition must not use local deterministic model/runtime shims to make a demo look alive.

## Implemented This Session

- Product composition now creates `LangGraphAgentRuntime` only.
- The local deterministic runtime adapter was deleted.
- The local model gateway adapter was deleted.
- Project message submission now creates a durable run, root orchestrator `AgentRun`, and queued `Task`.
- `WorkerService.work_once()` now leases that task, calls `ModelGateway`, persists the response artifact, completes the task, completes the root agent, and completes the run.
- Root project workers now parse a structured JSON dispatch decision.
- The orchestrator can dispatch reviewer and implementer child runs with persisted assignment artifacts.
- Workers execute child tasks independently; when all children complete, the root orchestrator summarizes their persisted result artifacts.
- Malformed dispatch output and failed child work now fail the overall run instead of leaving it waiting.
- Tests were rewritten so project runs expect one real root orchestrator task, not fabricated reviewer/implementer subagents.
- Root dashboard activity remains empty unless real root activities are persisted.
- Architecture docs and `.project/state.yaml` now describe the real limits.

Latest implementation commit: `c2ab911`.

## Validation

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest discover -s tests
```

Result: 28 tests passed.

```powershell
cd apps/web
npm.cmd run build
```

Result: build passed.

## Still Not Done

- No versioned external agent-definition store yet; reviewer/implementer definitions are application constants.
- No brokered filesystem, shell, git, browser, or sandbox tools.
- No Postgres repository implementation.
- No project memory implementation.
- The root project can call the model gateway, but cannot yet autonomously create projects through brokered project-management tools.

## Next Best Slice

Implement brokered project tools:

1. Define permission profiles and a minimal policy evaluator for tool calls.
2. Add a provider-neutral tool broker port.
3. Add sandbox-backed read-only workspace inspection first.
4. Persist tool calls, outputs, approvals, and audit events.
5. Only then allow agents to claim file inspection or edits.
