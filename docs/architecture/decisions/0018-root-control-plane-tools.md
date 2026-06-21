# ADR 0018-root-control-plane-tools: Expand root project management actions

Status: Proposed  
Date: 2026-06-21

## Context

The root project is the operator-facing control plane for a local Rorven
installation. It should help the operator find, inspect, summarize, and route
project work without pretending to solve project-scoped implementation tasks.

The first root tool action, `project.create`, proved the provider-neutral JSON
action pattern. The next root slice needs more management actions while keeping
execution inside the application layer and avoiding direct workspace or provider
access from the model.

## Decision

Extend the existing root action JSON contract with these application-executed
tool names:

- `project.search`
- `project.explain`
- `project.summarize_all`
- `system.health`
- `project.route`

These actions inspect persisted project, run, task, approval, artifact, and
conversation state. `system.health` also receives safe API-provided status data:
API readiness, worker status, data directory, and settings presence metadata.

The root model chooses the action, but the application layer performs all
lookup, aggregation, validation, formatting, and routing. `project.route`
returns an in-console hash route such as `#/projects/<id>`; it does not execute
the project task itself.

## Consequences

The root project can now create/register projects, search project records and
indexed persisted content, explain current project activity, summarize all
projects, report basic system health, and point the operator to the correct
project chat.

This is not a general root-agent tool broker. Root actions still cannot inspect
arbitrary workspace files, run shell commands, mutate settings except through
existing approved settings APIs, access raw secrets, or perform project-scoped
implementation work.

## Enforcement

Backend tests cover root project search, explanation, summary, health, routing,
and the existing scoped project creation behavior. The console linkifies
project hash routes returned in chat so routing stays inside the SPA.
