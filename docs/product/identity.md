# Rorven product identity

## Decision

The project uses **Rorven** as its provisional public development name. The canonical machine-readable slug is `rorven`.

Rorven is a coined name. The `Ro` prefix may subtly evoke robotics, while the full name is intentionally broad enough for durable orchestration, automation, and autonomous project work.

## Naming status

Rorven may be used for development and for a public source repository. It is not represented as a legally cleared or registered brand. Live registry checks, identifier reservation, domain selection, and qualified trademark review remain separate release activities.

A future rename must remain mechanical. Product branding therefore must not appear in domain entity names, database tables, event types, API routes, ports, or adapter contracts.

## Canonical identifiers

| Surface | Identifier |
|---|---|
| Product | `Rorven` |
| Repository | `rorven` |
| CLI | `rorven` |
| Configuration | `rorven.yaml` |
| Environment variables | `RORVEN_*` |
| Python namespace | `rorven` |
| TypeScript package scope | `@rorven/*` |
| Container prefix | `rorven/*` |

Examples:

```bash
rorven server start
rorven project create
rorven run inspect <run-id>
rorven memory list <project-id>
```

## Component naming

Use clear functional component names:

- Rorven Console
- Rorven API
- Rorven Worker
- Rorven Scheduler
- Rorven Runtime
- Rorven Model Gateway
- Rorven Memory
- Rorven Policy Engine
- Rorven Secret Broker
- Rorven Workspace Manager

Ports retain precise functional names such as `AgentRuntime`, `MemoryBackend`, `ModelGateway`, and `SecretStore`.

## Working description

> Rorven is durable infrastructure for autonomous work.

## Naming rules

- Use `Rorven` in prose and UI labels.
- Use `rorven` for repositories, executables, package roots, URLs, and file names.
- Use `RORVEN_` for environment variables.
- Do not create themed subsystem names.
- Do not rename architecture concepts solely to match the brand.
- Do not claim exclusivity or trademark status.
- A future rename requires a superseding ADR and an update to `.project/identity.yaml`.
