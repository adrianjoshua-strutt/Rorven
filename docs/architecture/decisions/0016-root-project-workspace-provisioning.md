# ADR 0016-root-project-workspace-provisioning: Let the root project create local projects

Status: Proposed  
Date: 2026-06-17

## Context

The root project is meant to manage projects, not merely describe how a user can
click through the UI. Creating a project has a filesystem side effect because the
workspace folder may need to be created before registration.

## Decision

Add a `WorkspaceProvisioner` port owned by the application layer. The local
adapter creates directories under a configured workspace base root. The local
state store persists `settings.project_defaults.workspace_base_root`, seeded from
the directory where the Rorven server process starts.

Root chat handles simple project creation requests locally before asking the
model. If a request has a project name, Rorven creates the workspace directory
under the configured base root and registers the project through `ProjectService`.
If the project name is missing, root chat asks for it. Paths outside the configured
base are rejected until the operator changes the base in Settings.

## Consequences

Root project creation is now a real product action rather than a model-written
instruction. The first local adapter is intentionally conservative: no arbitrary
filesystem roots, no shell commands, and no external side effects beyond creating
the scoped directory and persisting the project record.

## Enforcement

Backend tests cover root-chat project creation, missing-name prompts, settings
updates for the workspace base, and the existing project persistence flow.
