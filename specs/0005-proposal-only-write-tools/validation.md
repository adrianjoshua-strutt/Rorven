# Validation

Validated implementation commit: `fc7bab6`

## Evidence

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest discover -s tests
```

Result: 46 tests passed.

```powershell
cd apps/web
npm.cmd run build
```

Result: build passed.

```powershell
$env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:5177'
npm.cmd run test:e2e
```

Result: 2 Playwright tests passed across desktop and mobile Chromium.

Coverage includes project-chat multi-message rendering so a later message does
not replace the earlier visible command.

## 2026-06-20 follow-up evidence

Validated implementation commit: `191dc10cbd7ea91d8632d7b95f8903696d970c8f`

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest discover -s tests
```

Result: 48 tests passed.

Coverage includes:

- API lifespan embedded worker completes a queued project run.
- API lifespan embedded worker runs a dispatched implementer subagent through
  read-file and propose-write tools, then approval applies the change.
- Worker frames recent project chat history as explicit begin/end-bounded prior
  `ModelMessage` turns before the current user request.
- Root project chat frames prior root messages as explicit history before the
  current user request.
- Child agents can use multiple bounded tool rounds.

```powershell
cd apps/web
npm.cmd run build
```

Result: build passed.

## 2026-06-20 timeline/context follow-up evidence

Validated implementation commit: `286308ea9294b46ca4dd32fd2d22858d75121f7b`

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest discover -s tests
```

Result: 49 tests passed.

Coverage includes:

- Child-agent prompts receive project conversation history and the actual
  workspace root.
- Orchestrator summary prompts receive project conversation history and returned
  subagent messages.
- Project snapshots expose child agent runs so the console can show project-wide
  subagent work instead of only the selected run.

```powershell
cd apps/web
npx.cmd tsc -b
```

Result: TypeScript compile passed.

```powershell
cd apps/web
npm.cmd run build
```

Result: build passed. The sandboxed attempt failed with `spawn EPERM` from
esbuild; the same build passed outside the sandbox.

```powershell
$env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:5182'
npm.cmd run test:e2e
```

Result: 2 Playwright tests passed across desktop and mobile Chromium against a
built static app and local API with the embedded worker disabled.

## Remaining Limitations

- No sandbox isolation for mutable actions exists yet.
- Approved local text-file writes do not yet have full idempotency keys or
  interrupted-apply recovery tests.
- Bounded workspace shell commands exist for child agents, but risky command
  approval, arbitrary shell, git writes, browser, network-fetch, package
  installation, and external service tools remain unavailable. Safe diagnostics
  such as `ping` may run only through the policy-checked shell broker.

## 2026-06-21 approval and command follow-up evidence

Validated implementation commit: `80995094a365eafbc2091a45ea981726205b0a0b`

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest tests.test_workspace_tools tests.test_api_settings tests.test_local_file_store.LocalFileStoreTests.test_child_agent_can_propose_file_write_without_applying_it tests.test_local_file_store.LocalFileStoreTests.test_child_agent_can_read_then_propose_across_tool_rounds
```

Result: 13 tests passed.

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest tests.test_api_integration.ApiIntegrationTests.test_approval_endpoint_applies_proposed_workspace_write tests.test_api_integration.ApiIntegrationTests.test_embedded_worker_runs_subagent_tools_and_approval_flow
```

Result: 2 tests passed.

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest discover
```

Result: 52 tests passed.

```powershell
cd apps/web
npm.cmd run build
```

Result: build passed.

Coverage includes:

- Pending approvals pause only the producing subagent and keep the project run
  waiting instead of falsely completed.
- Approval application resumes the waiting subagent and allows the project
  orchestrator to summarize the applied result.
- Project snapshots expose approvals and proposal artifacts for main-chat
  rendering.
- Settings persist text-file write approval policy.
- Bounded workspace shell commands are policy checked and captured through the
  tool broker.

## 2026-06-21 console routing/settings follow-up evidence

Validated implementation commit: `e6dee8a7190abc51c4a1adc6e70d91c2875191fe`

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest discover
```

Result: 52 tests passed.

Coverage includes:

- Project list API payloads expose latest activity, last user message,
  pending approval counts, and active run counts for console sorting and
  unread indicators.
- Orchestrator model requests receive a project work-log facts section so
  approval outcomes and subagent results are available to follow-up turns.
- Shell policy allows safe diagnostic commands such as `ping www.google.de`
  while continuing to deny network-fetch commands such as `curl`.

```powershell
cd apps/web
npm.cmd run build
```

Result: TypeScript and Vite build passed.

```powershell
$env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:5185'
npm.cmd run test:e2e
```

Result: 2 Playwright tests passed across desktop and mobile Chromium.

Coverage includes:

- Hash-routed root, settings, and project pages so browser Back returns inside
  the console instead of leaving the app.
- Settings contains real model-tier and project-default controls and no longer
  exposes removed status-only tiles such as secret visibility or memory backend.
- Project selection survives reload, and Shift+Enter submits through the chat
  composer.

## 2026-06-21 agent protocol and project sorting follow-up evidence

Validated implementation commit: `7d61f3db673ead2236d0df5b877e6355a78fe2cb`

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest discover
```

Result: 56 tests passed.

Coverage includes:

- `workspace.run_shell_command` tolerates missing stdout/stderr streams instead
  of failing with `object of type 'NoneType' has no len()`.
- Subagent final protocol JSON with common model wrappers is normalized to the
  final content before storing/rendering.
- Root chat responses no longer expose provider labels such as `openrouter`.
- Project detail responses preserve the same `last_activity_at` and
  `last_user_message_at` metadata as the project list, so selecting/polling a
  project no longer breaks sorting.
- The orchestrator dispatch contract explicitly requires fresh subagent work
  for retry requests such as "try again".

```powershell
cd apps/web
npm.cmd run build
```

Result: TypeScript and Vite build passed.

```powershell
$env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:5186'
npm.cmd run test:e2e
```

Result: blocked in this environment. The elevated Playwright run was rejected,
and the sandboxed run failed while cleaning Playwright state with
`EPERM: operation not permitted, unlink 'apps/web/test-results/.last-run.json'`.

## 2026-06-21 root control plane and protocol follow-up evidence

Validated implementation commit: `d457204`

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest tests.test_local_file_store.LocalFileStoreTests.test_child_and_summary_requests_receive_project_conversation_history tests.test_local_file_store.LocalFileStoreTests.test_auto_approved_write_completes_with_applied_summary_not_raw_tool_json tests.test_root_dashboard
```

Result: 12 tests passed.

Coverage includes:

- Root project actions for project search, project explanation, project routing,
  all-project summary, and system health.
- Child assignment artifacts include workspace root, current request, assigned
  task, and recent project chat context.
- Auto-approved text-file write proposals actually apply the workspace file and
  complete with a normal assistant answer instead of raw `tool_calls` protocol
  JSON.

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest discover
```

Result: 60 tests passed.

```powershell
cd apps/web
npm.cmd run build
```

Result: TypeScript and Vite build passed.

```powershell
cd apps/web
$env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:5187'
npm.cmd run test:e2e
```

Result: blocked in this environment while cleaning Playwright state with
`EPERM: operation not permitted, unlink 'apps/web/test-results/.last-run.json'`.

## 2026-06-21 direct workspace tool follow-up evidence

Validated implementation commit: pending commit.

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest tests.test_workspace_tools tests.test_local_file_store.LocalFileStoreTests.test_child_agent_can_write_file_directly tests.test_local_file_store.LocalFileStoreTests.test_child_agent_can_read_then_write_across_tool_rounds tests.test_local_file_store.LocalFileStoreTests.test_direct_write_completes_with_applied_summary_not_raw_tool_json tests.test_api_integration.ApiIntegrationTests.test_embedded_worker_runs_subagent_tools_and_approval_flow tests.test_api_integration.ApiIntegrationTests.test_worker_work_once_directly_applies_workspace_write
```

Result: 13 tests passed.

Coverage includes:

- `workspace.write_text_file` writes scoped UTF-8 files through the broker.
- Child agents can read, write, continue across tool rounds, and complete
  without approval dead-ends.
- Embedded API worker applies direct child-agent writes end-to-end.
- The project chat shows compact subagent status while the subagent work view
  keeps the full harness transcript.

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest discover
```

Result: 59 tests passed.

```powershell
cd apps/web
npm.cmd run build
```

Result: TypeScript and Vite build passed.
