# Session Handoff - 2026-06-16

This note is operational context for the next agent. It does not override the constitution, ADRs, active specs, or architecture docs.

## Current Direction

The old `specs/0001-foundation` dossier was removed because it encouraged synthetic behavior. The active dossier is now `specs/0005-proposal-only-write-tools`.

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
- Child agents can request one brokered round of read-only workspace tools.
- `WorkspaceReadPolicy` denies root-agent tool use, unsupported tools, oversized requests, and obvious secret paths.
- `LocalWorkspaceToolBroker` confines paths to the project workspace and supports `workspace.list_files` and `workspace.read_text_file`.
- `LocalWorkspaceToolBroker` also supports `workspace.propose_text_file_write`, which returns a persisted unified diff without changing the workspace file.
- Tool requests, denials, completions, failures, and outputs are persisted as events/artifacts.
- Tests were rewritten so project runs expect one real root orchestrator task, not fabricated reviewer/implementer subagents.
- Root dashboard activity remains empty unless real root activities are persisted.
- Architecture docs and `.project/state.yaml` now describe the real limits.

Latest implementation commit: `41723e4`.

## Validation

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest discover -s tests
```

Result: 34 tests passed.

```powershell
cd apps/web
npm.cmd run build
```

Result: build passed.

## Still Not Done

- No versioned external agent-definition store yet; reviewer/implementer definitions are application constants.
- No apply-write/edit, shell, git, browser, network, approval, or sandbox tools.
- No Postgres repository implementation.
- No project memory implementation.
- The root project can call the model gateway, but cannot yet autonomously create projects through brokered project-management tools.

## Next Best Slice

Implement approved write/apply tools:

1. Add explicit approval and policy records for mutable actions.
2. Add a sandbox-backed file-edit proposal/apply flow.
3. Persist diffs, approvals, and idempotency keys.
4. Add recovery tests around interrupted edits.
5. Only then allow agents to claim file edits.
