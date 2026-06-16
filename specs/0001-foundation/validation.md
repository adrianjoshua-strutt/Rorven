# Validation evidence

Status: In progress

## Acceptance checklist

- [x] Project and workspace creation verified.
- [x] Parallel child runs verified.
- [ ] API restart recovery verified.
- [ ] Worker loss recovery verified.
- [ ] No duplicate child results verified.
- [x] UI reload reconstruction verified.
- [x] Architecture boundaries verified.
- [x] Model-profile-only agent definitions verified.
- [ ] No raw secret persistence verified.
- [ ] Clean bootstrap migration verified.
- [ ] Synthetic previous-schema migration verified.

## Evidence

- `02a2109` - `python -m unittest discover -s tests` with `PYTHONPATH=src`: 7 tests passed.
- Verified domain/application forbidden-import architecture checks.
- Verified domain/application historical-schema branch scan.
- Verified workspace binding rejects paths outside the allowed root and sibling-prefix escapes.
- Verified local deterministic `AgentRuntime` contract creates one parent and two child agent runs with model-profile names only.
- `658f235` - `python -m unittest discover -s tests` with `PYTHONPATH=src;apps/api;apps/worker`: 9 tests passed.
- Verified FastAPI project creation, run submission, worker pass, parent completion, task completion, and persisted state reload through the local file adapter.
- `e2ec8a1` - `npm.cmd audit --json` in `apps/web`: 0 vulnerabilities reported.
- `e2ec8a1` - `npm.cmd run build` in `apps/web`: TypeScript and Vite production build passed.
- Verified React/Vite console can reconstruct project runs, run tree, tasks, and events from API state.
- `67bfbd7` - `npm.cmd run build` in `apps/web`: TypeScript and Vite production build passed after redesigning the console around project chat and spawned-agent inspection.
- `67bfbd7` - `npm.cmd audit --json` in `apps/web`: 0 vulnerabilities reported.
- `67bfbd7` - `python -m unittest discover -s tests` with `PYTHONPATH=src;apps/api;apps/worker`: 9 tests passed.
- `2459e46` - `npm.cmd run build` in `apps/web`: TypeScript and Vite production build passed after removing dev controls and replacing the clickable agent inspector with a passive subagent activity rail.
- `2459e46` - `npm.cmd audit --json` in `apps/web`: 0 vulnerabilities reported.
- `2459e46` - `python -m unittest discover -s tests` with `PYTHONPATH=src;apps/api;apps/worker`: 9 tests passed.
- `2a11b24` - `npm.cmd run build` in `apps/web`: TypeScript and Vite production build passed after moving project creation into a modal, adding settings, shrinking the composer, fixing project selection, and restoring subagent inspection through the main panel.
- `2a11b24` - `npm.cmd audit --json` in `apps/web`: 0 vulnerabilities reported.
- `2a11b24` - `python -m unittest discover -s tests` with `PYTHONPATH=src;apps/api;apps/worker`: 9 tests passed.
- `89d4ebf` - `npm.cmd run build` in `apps/web`: TypeScript and Vite production build passed after making root project selectable, stabilizing project selection, and presenting subagent work as a chat-like transcript view.
- `89d4ebf` - `npm.cmd audit --json` in `apps/web`: 0 vulnerabilities reported.
- `89d4ebf` - `python -m unittest discover -s tests` with `PYTHONPATH=src;apps/api;apps/worker`: 9 tests passed.

## Known deferred evidence

- Real external model calls are deferred until the model-provider adapter slice.
- LangGraph runtime behavior is deferred until the runtime-adapter slice.
- Brokered secret use is deferred until the secret-store and tool-broker slice.
- PostgreSQL migrations, full task lease recovery, and API/worker process restart recovery are not yet implemented.
