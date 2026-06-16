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

- Policy denies root-agent workspace tool calls.
- Policy denies sensitive paths.
- Local broker reads files inside the workspace.
- Local broker rejects path traversal outside the workspace.
- Worker persists tool events and artifacts during child-agent execution.
- Existing project, dispatch, API, persistence, and architecture tests remain green.
