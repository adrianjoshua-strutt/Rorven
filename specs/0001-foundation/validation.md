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
- [x] No raw secret persistence verified.
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
- `242944a` - `python -m unittest discover -s tests` with `PYTHONPATH=src;apps/api;apps/worker`: 10 tests passed after adding the settings metadata endpoint and a credential non-disclosure check.
- `242944a` - `npm.cmd run build` in `apps/web`: TypeScript and Vite production build passed after replacing the settings modal with a first-class settings surface.
- `242944a` - `npm.cmd audit --json` in `apps/web`: 0 vulnerabilities reported.
- Verified `/settings` reports OpenRouter credential presence without returning the raw `RORVEN_OPENROUTER_API_KEY` value.
- `0f1032f` - `npm.cmd run build` in `apps/web`: TypeScript and Vite production build passed after moving controls, modals, badges, tables, cards, and text inputs to Mantine.
- `0f1032f` - `python -m unittest discover -s tests` with `PYTHONPATH=src;apps/api;apps/worker`: 10 tests passed.
- `0f1032f` - `npm.cmd audit --json` in `apps/web`: 0 vulnerabilities reported.
- Verified root project is represented as a normal chat surface with root-scoped subagent activity rather than a dashboard.
- Verified chat composers use fixed-height Mantine textareas so empty chat state does not resize the input.
- `d7f2673` - `python -m unittest discover -s tests` with `PYTHONPATH=src;apps/api;apps/worker`: 13 tests passed after stabilizing project list order, duplicate workspace rejection, and repo-local data directory resolution.
- `d7f2673` - `npm.cmd run build` in `apps/web`: TypeScript and Vite production build passed after preserving project list order on selection.
- `d7f2673` - `npm.cmd audit --json` in `apps/web`: 0 vulnerabilities reported.
- Verified clicking a project no longer reorders the project list under the cursor; selected project rows are highlighted in place.
- `acc03d3` - `npm.cmd run build` in `apps/web`: TypeScript and Vite production build passed after splitting the console into components, hooks, typed utilities, and a small React bootstrap entrypoint.
- `acc03d3` - `python -m unittest discover -s tests` with `PYTHONPATH=src;apps/api;apps/worker`: 13 tests passed after splitting the FastAPI app into entrypoint, routes, schemas, and serializers.
- `acc03d3` - `npm.cmd audit --json` in `apps/web`: 0 vulnerabilities reported.
- Verified `apps/web/src/main.tsx` is only the React bootstrap, console screens live under `apps/web/src/components`, controller state lives under `apps/web/src/hooks`, and shared helpers live under `apps/web/src/utils`.
- Verified `apps/api/rorven_api/main.py` only builds the FastAPI app while routes, serializers, and request schemas live in separate modules.
- Verified chat bubbles and agent work entries wrap long content and stay inside fixed-height scroll regions.
- `5fbbb63` - `python -m unittest discover -s tests` with `PYTHONPATH=src;apps/api;apps/worker`: 15 tests passed after adding the provider-neutral model gateway, OpenRouter adapter, model-backed worker artifacts, artifact text in API run state, and local state migration for the artifacts bucket.
- `5fbbb63` - `npm.cmd run build` in `apps/web`: TypeScript and Vite production build passed after rendering persisted agent artifact text in subagent and orchestrator chat surfaces.
- `5fbbb63` - `npm.cmd audit --json` in `apps/web`: 0 vulnerabilities reported.
- Verified the OpenRouter adapter sends chat-completions requests through a model-profile mapping and does not expose the configured API key in adapter responses.
- Verified `/settings` reports OpenRouter credential presence and active model gateway without returning the raw `RORVEN_OPENROUTER_API_KEY` value.
- Verified workers persist model gateway output as text artifacts and the console displays those artifact contents when a subagent is selected.

## Known deferred evidence

- LangGraph runtime behavior is deferred until the runtime-adapter slice.
- Brokered secret use is deferred until the secret-store and tool-broker slice.
- Filesystem/shell tools, Docker sandboxing, PostgreSQL migrations, full task lease recovery, and API/worker process restart recovery are not yet implemented.
