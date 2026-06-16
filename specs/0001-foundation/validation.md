# Validation evidence

Status: Not started

## Acceptance checklist

- [ ] Project and workspace creation verified.
- [ ] Parallel child runs verified.
- [ ] API restart recovery verified.
- [ ] Worker loss recovery verified.
- [ ] No duplicate child results verified.
- [ ] UI reload reconstruction verified.
- [ ] Architecture boundaries verified.
- [ ] Model-profile-only agent definitions verified.
- [ ] No raw secret persistence verified.
- [ ] Clean bootstrap migration verified.
- [ ] Synthetic previous-schema migration verified.

## Evidence

Add links or references to CI runs, test reports, screenshots, migration checks, and manual verification notes here.

## Known deferred evidence

- Real external model calls are deferred until the model-provider adapter slice.
- LangGraph runtime behavior is deferred until the runtime-adapter slice.
- Brokered secret use is deferred until the secret-store and tool-broker slice.
