# Test Plan

## Required Commands

```powershell
$env:PYTHONPATH='.;src;apps/api;apps/worker'
.venv\Scripts\python.exe -m unittest discover -s tests
```

```powershell
cd apps/web
npm.cmd run build
```

## Coverage Intent

- Local broker writes UTF-8 text files inside the workspace and rejects path escapes.
- Worker persists direct write tool artifacts.
- Worker persists inspectable agent transcript entries.
- Project chat renders multiple submitted commands without replacing earlier
  messages.
- Project chat renders compact subagent status messages while the subagent work
  view keeps the full harness and transcript.
- The API lifespan embedded worker completes queued project runs without a
  manual `/worker/work-once` call.
- Subagents can read workspace files, write text files, and run bounded CLI
  commands across multiple tool rounds.
- Existing dispatch, read-only tool, API, persistence, and architecture tests stay green.
