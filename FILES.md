# Pack contents

This pack intentionally contains no production implementation code. It establishes the product, architecture, engineering rules, initial ADR set, and first vertical-slice specification so Codex can begin from explicit constraints rather than conversational context.

The project uses **Rorven** as a provisional development and public repository name. Identity is centralized in `.project/identity.yaml`; ADR 0012 records the decision.

The pack permanently adopts migration-first evolution. ADR 0013 and `docs/architecture/evolution-and-migrations.md` require automatic upgrades to one canonical model and treat backward-compatibility code as a rare, isolated, time-bounded exception.
