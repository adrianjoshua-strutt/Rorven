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

- Dispatch parser accepts direct answers and approved child dispatch.
- Dispatch parser rejects unsupported child agents.
- Worker persists child assignments, child runs, child tasks, and waiting parent state.
- Worker joins completed child results into a final root summary.
- Malformed root dispatch fails the run.
- API integration still supports direct-answer project execution.
- UI build accepts assignment artifact rendering.
