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

- API project creation, run submission, worker execution, and state reload.
- Local-file persistence for projects, runs, tasks, artifacts, settings, and migrations.
- OpenRouter adapter contract with patched HTTP transport.
- Runtime adapter contract for persisted root orchestrator runs.
- Frontend API-state assumptions and production build.
