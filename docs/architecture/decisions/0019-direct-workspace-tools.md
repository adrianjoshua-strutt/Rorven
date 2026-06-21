# ADR 0019: Direct Brokered Workspace Tools

Status: accepted

## Context

The proposal-only write path made child agents behave like cautious tool
selectors. A coding subagent that only proposes a file and then stops has not
completed the orchestrator assignment.

The platform still requires brokered capabilities, policy evaluation, scoped
workspace roots, persisted tool evidence, and secret non-disclosure.

## Decision

Child agents use `workspace.write_text_file` as the canonical text-file mutation
tool. It writes one complete UTF-8 text file inside the project workspace after
policy evaluation, creates parent directories when needed, and persists tool
request, policy decision, result metadata, and output artifacts.

The active child-agent toolbox is:

- `workspace.list_files`
- `workspace.read_text_file`
- `workspace.write_text_file`
- `workspace.run_shell_command`

`workspace.run_shell_command` remains bounded: workspace-scoped cwd, sanitized
environment, timeout cap, captured output, and policy denies for obvious
destructive, package-install, network-fetch, and secret-sensitive commands.

The proposal/apply write flow from ADR 0015 is no longer the active worker
execution path for text-file writes. Older approval records may still be visible
in persisted local state, but new child runs do not create text-file write
proposals.

## Consequences

- Implementer prompts can instruct subagents to complete work rather than stop
  at a proposal.
- Project chat can summarize subagent starts while the subagent work view keeps
  the full harness prompt and durable transcript.
- Direct writes are useful but still not sandboxed; interrupted-write recovery,
  idempotency keys, and sandbox isolation remain required before expanding to
  broader mutable operations.
