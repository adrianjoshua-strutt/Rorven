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

- Local broker returns a unified diff for proposed text writes.
- Local broker does not mutate the target file.
- Worker persists proposal tool artifacts.
- Worker persists inspectable agent transcript entries.
- Approval decisions append transcript entries.
- Project chat renders multiple submitted commands without replacing earlier
  messages.
- Existing dispatch, read-only tool, API, persistence, and architecture tests stay green.
