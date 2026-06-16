# Session handoff — 2026-06-16

This document records the state of implementation at the end of the session.
An incoming agent must read `AGENTS.md` and the normative precedence chain before
continuing. This file provides the _what_ and _why_ of changes made; it does not
override normative documents.

---

## What was implemented

### 1. Model profile persistence (`src/rorven/adapters/persistence/local_file.py`)

Model profile IDs are now stored in `.rorven/state.json` under
`settings.model_profiles`, not in environment variables.

- Added `get_model_profile_ids()` and `set_model_profile_ids()` on
  `LocalFilePlatformStore`.
- `_empty_state()` seeds the four tiers with empty strings.
- `_migrate_state()` reads legacy env vars on first migration and seeds from them.
- `load_model_profile_config()` in `src/rorven/adapters/model/profiles.py` accepts
  `profile_overrides` dict from the store.
- Startup raises `RuntimeError` with a clear message if the OpenRouter key env var
  is empty or absent (`src/rorven/composition.py`, `_create_model_gateway`).

**Active model slugs as of this session** (stored in `.rorven/state.json`):
- `utility` → `meta-llama/llama-3.2-3b-instruct`
- `balanced` / `reasoning` / `frontier` → `qwen/qwen3-8b`

> Note: `qwen/qwen3-8b:free` and `deepseek/deepseek-r1:free` were tried and are
> 404 in the TXL region. Use paid slugs without `:free` suffix.

---

### 2. Settings API endpoint (`apps/api/rorven_api/`)

- `GET /settings` reads model profile IDs from the store and reports `source: state.json`.
- `POST /settings/model-profiles` accepts `{utility, balanced, reasoning, frontier}`
  and persists to the store. Schema in `schemas.py`, handler in `routes.py`.

---

### 3. Root orchestrator — real model calls, no mocks

- `RootService.submit_message` in `src/rorven/application/services.py` now makes a
  real `ModelGateway.complete()` call with a live project inventory prompt.
- All synthetic/canned messages (`root-orchestrator-ready`, welcome text, etc.) are
  filtered out by `_filtered_root_messages()`.
- `_build_activities()` and `_summarize_projects()` helpers were deleted entirely.
- Route handler wraps gateway failures in `HTTPException(502)` instead of letting
  unhandled exceptions surface as browser `NetworkError`.

---

### 4. Project chat — mocks removed

**`src/rorven/adapters/runtime/local.py` and `langgraph.py`**

`plan_child_runs()` previously hardcoded two fake `AgentRun` records (`reviewer`,
`implementer`) that were immediately written to state and stuck in `WAITING` forever.
Both implementations now return `[]`.

`submit_task()` in `services.py` no longer calls `plan_child_runs()` or
`_root_agent_run()` at all.

**`apps/web/src/utils/chat.ts`**

`buildProjectChat()` previously fabricated the message
`"I started N subagents. N still running, 0 finished."`.  
It now shows:
- Real result artifact content if the run has a `result_artifact_id`.
- `"M subagents running, N finished."` when real child runs exist.
- `"Working…"` when the orchestrator is queued/started with no child runs yet.
- `"Done."` or `"Queued."` for completed/other states.

---

### 5. Frontend — optimistic submit + pending state

`apps/web/src/hooks/useRootProjectController.ts`:

- Optimistic user message is prepended immediately on Send.
- `isPending` state tracks the in-flight model call.
- On success, full server response replaces the optimistic entry.
- On failure, a `GET /root` reload ensures the persisted user message is visible; the
  input is restored with the original text; the optimistic message is removed on total
  network failure.

`apps/web/src/components/projects/RootProjectView.tsx`:

- Composer is `disabled` while `isPending`.
- `ConnectionState` shows `loading` during the call.
- An animated `···` thinking bubble appears below the last message while pending.

---

### 6. Layout and scroll — fixed

The entire scroll chain was broken: views were expanding past the viewport instead of
being constrained. Fixed in `apps/web/src/styles.css`:

- `html` and `body` now use `height: 100%; overflow: hidden`.
- `.app-shell` has `max-height: 100vh`.
- `.chat-pane` uses `display: flex; flex-direction: column; height: 100vh`.
- `.root-view`, `.agent-work-view`, `.settings-view` use `flex: 1; min-height: 0` so
  they fill the pane without overflowing.
- `.message-list` inside each view has `flex: 1; min-height: 0; overflow-y: auto`.
- `.composer` has `flex: 0 0 auto` so it stays pinned to the bottom.

The old `grid-template-rows: auto minmax(0,1fr) auto` approach on `.chat-pane` and
view containers was replaced wholesale with the flex column pattern. The now-redundant
`grid-row: 1/-1` rule was removed.

---

### 7. API error surfacing

`apps/web/src/api.ts`:

- `fetch()` is wrapped in a try/catch; raw browser `NetworkError` is replaced with
  `"API request failed for <path>: <reason>"`.
- HTTP error responses are JSON-parsed for a `.detail` field before falling back to
  raw text.

---

### 8. Tests updated

All tests that assumed mocked behavior were rewritten:

| File | Change |
|---|---|
| `tests/test_root_dashboard.py` | Asserts empty `activities` and `messages` on fresh state; removed broken double-`main()` structure. |
| `tests/test_api_settings.py` | Covers key-presence-only security and persisted model profile round-trip. |
| `tests/test_local_runtime_contract.py` | `plan_child_runs` returns `[]`; test renamed accordingly. |
| `tests/test_langgraph_runtime_contract.py` | Same as above. |

All four tests pass under `python -m unittest` with the project's PYTHONPATH.

---

## What is NOT done (next agent pickup)

### Primary gap: worker task execution loop

The most critical missing piece is that project runs are created and persisted but
nothing executes them. The `state: queued` orchestrator `AgentRun` sits indefinitely.

**Location of work**: `apps/worker/rorven_worker/` and the `WorkerService` in
`src/rorven/application/worker_service.py`.

**What it needs to do**:
1. Poll the task queue for leased tasks.
2. For each task, resolve the agent definition and run the appropriate model call.
3. Write result artifacts and transition the `AgentRun` to `completed`.
4. Handle parent run status transitions when all child runs finish.

The `POST /worker/work-once` endpoint already exists in routes.py as the driver
interface.

### Secondary gap: project chat shows static status

Until the worker loop runs, the project chat always shows `"Working…"` or
`"Queued."`. The frontend polls `GET /projects/{id}/runs/{runId}` every 2.5 seconds
(see `useConsoleController.ts`), so once the worker transitions status the UI will
update automatically.

### Cleanup debt

- `.rorven/state.json` contains ~28 duplicate projects from test runs. A cleanup pass
  or migration should deduplicate by `workspace_root` before the next demo.
- `_plan_children_graph` and its supporting `_PlanChildrenState` type in
  `langgraph.py` are now dead code — the graph is never compiled or invoked.
  Remove them when refactoring the runtime adapter.
- `LocalFilePlatformStore` is the system of record; it must be replaced by the
  PostgreSQL adapter (ADR 0004) before M2.

---

## Running the application

```bash
# API
cd D:/Cloud/Dropbox/GitHub/rorven
env PYTHONPATH='.;src;apps/api;apps/worker' \
  D:/temp/rorven-validate/Scripts/python.exe \
  -m uvicorn rorven_api.main:app --host 127.0.0.1 --port 8000

# Frontend dev server
cd apps/web && npx vite --port 5174

# Run focused tests
env PYTHONPATH='.;src;apps/api;apps/worker' \
  D:/temp/rorven-validate/Scripts/python.exe \
  -m unittest tests.test_root_dashboard tests.test_api_settings \
  tests.test_local_runtime_contract tests.test_langgraph_runtime_contract
```

The OpenRouter key must be set in the shell environment as
`RORVEN_OPENROUTER_API_KEY` before starting the API. Startup will raise
`RuntimeError` if absent or empty.
