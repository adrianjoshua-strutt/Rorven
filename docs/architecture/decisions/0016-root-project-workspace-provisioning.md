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

Root chat asks the model gateway for a provider-neutral root action JSON object.
The first supported root tool action is `project.create`. The model may request
that tool with a project name and optional workspace path, but the application
layer owns all execution: it validates the payload, resolves the configured
workspace base root, creates the workspace directory through `WorkspaceProvisioner`,
and registers the project through `ProjectService`.

If the project name is missing, the root project asks for it. Paths outside the
configured base are rejected until the operator changes the base in Settings.

## Consequences

Root project creation is now a real product action rather than a model-written
instruction or a brittle text-intent parser. The first local adapter is
intentionally conservative: no arbitrary filesystem roots, no shell commands, and
no external side effects beyond creating the scoped directory and persisting the
project record.

## Enforcement

Backend tests cover root-chat project creation through the model-requested tool
contract, missing-name prompts, path rejection outside the workspace base,
settings updates for the workspace base, and the existing project persistence
flow.
