# ADR 0012: Use Rorven as the provisional product name

Status: Accepted  
Date: 2026-06-16

## Context

ADR 0011 rejected Rovan as a cleared public product name after a direct software-brand conflict was identified. Development should continue without making naming a blocker.

## Decision

Use **Rorven** as the provisional project, repository, CLI, and package-root name.

Rorven may be used for a public source repository, but the project does not claim legal clearance or exclusivity. Formal checks and identifier reservation are required before stable package publication or commercial branding.

Branding must remain outside domain entities, database table names, event types, API routes, ports, and adapter contracts.

## Consequences

Positive:

- Development can proceed under a coherent name.
- A later rename remains largely mechanical.
- Product identity does not contaminate stable architecture contracts.

Negative:

- Package and domain identifiers may need alternatives later.
- Public-facing materials must describe the name as provisional until clearance is complete.

## Enforcement

- Canonical identity lives in `.project/identity.yaml`.
- Architecture tests forbid branded domain and persistence identifiers where practical.
- Stable-release readiness includes live registry and trademark checks.
