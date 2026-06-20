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

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest discover -s tests
```

Result: 46 tests passed.

Coverage includes:

- API lifespan embedded worker completes a queued project run.
- API lifespan embedded worker runs a dispatched implementer subagent through
  read-file and propose-write tools, then approval applies the change.
- Worker supplies recent project chat history to the project orchestrator as
  prior `ModelMessage` turns before the current user request.
- Child agents can use multiple bounded tool rounds.

```powershell
cd apps/web
npm.cmd run build
```

Result: build passed.

Playwright browser validation was attempted twice during live debugging and was
interrupted by the operator before completion; do not treat the current follow-up
slice as browser-validated until it is rerun.

## Remaining Limitations

- No sandbox isolation for mutable actions exists yet.
- Approved local text-file writes do not yet have full idempotency keys or
  interrupted-apply recovery tests.
- No shell, git, browser, network, or external service tools.
- Follow-up browser validation for the embedded worker/chat UI slice is still
  outstanding after interrupted Playwright runs.
