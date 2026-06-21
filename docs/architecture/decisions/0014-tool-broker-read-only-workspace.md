# ADR 0014-tool-broker-read-only-workspace: Add brokered workspace tools

Status: Proposed; text-file write decision superseded by ADR 0019  
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

The first adapter is `LocalWorkspaceToolBroker`, which supports local workspace
inspection and proposal-only text writes through:

- `workspace.list_files`
- `workspace.read_text_file`
- `workspace.propose_text_file_write`

Product composition wires `WorkspaceReadPolicy` and `LocalWorkspaceToolBroker`.
The policy denies by default, allows only child agents, blocks unsupported tools,
caps output sizes, and denies obvious secret paths. Write proposals are represented
as unified diffs and are not applied to the workspace.

## Consequences

Agents can inspect ordinary project files and propose text-file changes through
auditable artifacts and events without receiving ambient machine access. This is
still not sandbox isolation and does not permit applied edits, shell commands, git
actions, network access, or secret retrieval.

## Enforcement

Backend tests cover policy denial, path escape prevention, brokered file reads,
proposal-only text diffs that leave files unchanged, and worker runs where child
agents request tools before producing final work. Architecture boundary tests
continue to prevent provider/framework imports in domain and application layers.
