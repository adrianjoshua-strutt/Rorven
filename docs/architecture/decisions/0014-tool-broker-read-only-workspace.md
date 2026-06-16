# ADR 0014-tool-broker-read-only-workspace: Add brokered read-only workspace tools

Status: Proposed  
Date: 2026-06-16

## Context

Agents need project context from files, but direct filesystem access would violate
the permission and secret model. The platform needs a boundary that can later be
replaced by a sandboxed implementation without changing agent, API, or domain
contracts.

## Decision

Add two application-owned ports:

- `ToolPolicy` evaluates whether an agent may invoke a requested capability.
- `ToolBroker` executes policy-approved tool calls.

The first adapter is `LocalWorkspaceToolBroker`, which supports read-only local
workspace inspection through:

- `workspace.list_files`
- `workspace.read_text_file`

Product composition wires `WorkspaceReadPolicy` and `LocalWorkspaceToolBroker`.
The policy denies by default, allows only child agents, blocks unsupported tools,
caps output sizes, and denies obvious secret paths.

## Consequences

Agents can inspect ordinary project files through auditable artifacts and events
without receiving ambient machine access. This is still not sandbox isolation and
does not permit edits, shell commands, git actions, network access, or secret
retrieval.

## Enforcement

Backend tests cover policy denial, path escape prevention, brokered file reads,
and a worker run where a child agent requests a tool before producing final work.
Architecture boundary tests continue to prevent provider/framework imports in
domain and application layers.
