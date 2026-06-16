# Validation evidence

Status: In progress

## Acceptance checklist

- [x] Project and workspace creation verified.
- [x] Parallel child runs verified.
- [ ] API restart recovery verified.
- [ ] Worker loss recovery verified.
- [ ] No duplicate child results verified.
- [ ] UI reload reconstruction verified.
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

## Known deferred evidence

- Real external model calls are deferred until the model-provider adapter slice.
- LangGraph runtime behavior is deferred until the runtime-adapter slice.
- Brokered secret use is deferred until the secret-store and tool-broker slice.
- PostgreSQL migrations, durable task leases, API/worker restart recovery, and UI reload evidence are not yet implemented.
