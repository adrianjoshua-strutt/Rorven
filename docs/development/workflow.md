# Development workflow

## Feature lifecycle

```text
PROPOSED
-> CLARIFIED
-> SPECIFIED
-> ARCHITECTURE_REVIEWED
-> PLANNED
-> IMPLEMENTING
-> CODE_REVIEW
-> VALIDATING
-> COMPLETED
```

## Required feature dossier

Each non-trivial feature should include:

- `spec.md`
- `assumptions.md`
- `plan.md`
- `contracts.md` or contract files
- `tasks.md`
- `test-plan.md`
- `validation.md`
- `rollout.md` when operationally relevant
- `retrospective.md` for major features

## Adapter-first change rule

Every feature plan must answer:

1. Which existing port is used?
2. Which adapter is extended or added?
3. Does the change require a new port?
4. How is the boundary enforced in tests?
5. How can the implementation be replaced later?

## Documentation rule

Documentation changes are part of the same change set as implementation.


## Migration-first change rule

Every change to persisted data, configuration, stored definitions, or adapter metadata must answer:

1. What is the new canonical representation?
2. Which source versions are supported?
3. How are existing records transformed before normal use?
4. Is the migration transactional, resumable, or safely restartable?
5. What preflight, backup, and post-migration invariants are required?
6. Which old runtime branches and representations are removed by the same change?
7. If compatibility code is proposed, why is migration impossible or insufficient?
8. Where is the exception ADR, owner, removal condition, and removal date?

Compatibility is not a release phase or a permanent mode. It is a narrow exception at an external or operational boundary.
