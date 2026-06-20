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
- No shell, git, browser, network, or external service tools.
