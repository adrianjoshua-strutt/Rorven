# Direct Workspace Tools

Status: active

## Goal

Child agents can complete scoped workspace work through brokered tools. The
current toolbox supports workspace inspection, text-file writes, and bounded CLI
commands without giving agents ambient machine access.

## Requirements

- Extend the existing `ToolBroker` and `ToolPolicy` ports; agents must still use
  brokered capabilities rather than direct filesystem or process access.
- Add `workspace.write_text_file`.
- Keep `workspace.list_files`, `workspace.read_text_file`, and
  `workspace.run_shell_command` available to child agents.
- Restrict workspace tools to child agents.
- Confine paths and command working directories to the project workspace root.
- Deny obvious secret paths.
- Limit text-write size.
- Write UTF-8 text files directly after policy evaluation.
- Create parent directories for text writes when needed.
- Persist tool request, policy decision, result metadata, and captured output as
  artifacts.
- Run bounded CLI commands inside the workspace with sanitized environment,
  timeout caps, captured output, and command-pattern denies for obvious
  destructive, install, network-fetch, and secret-sensitive operations.

## Non-Goals

- Arbitrary shell, git writes, browser, package installation, network-fetch, or
  external service tools.
- Sandbox isolation.
- Binary-file editing.
- Destructive file operations.
- Multi-file patch application as a single atomic patch.

## 2026-06-21 Extension

By operator request, proposal-only text writes are no longer the active child
agent write path. `workspace.write_text_file` is the canonical text-file tool for
child agents. Proposal/apply approval records may still exist in older local
state, but new worker execution does not create text-file write proposals.

## Acceptance

- Backend tests prove direct text writes are confined to the workspace and mutate
  the requested file.
- Worker tests prove child agents can read, write, run multiple tool rounds, and
  complete without approval dead-ends.
- API tests prove the embedded worker can apply a child-agent text write
  end-to-end.
- Project and subagent conversations are rendered from durable transcript
  entries rather than reconstructed from only the selected run.
- Child agents can run bounded workspace commands, including accepted safe
  diagnostics, through policy-checked shell execution without inheriting raw
  secrets.
- The main project chat summarizes spawned subagents with compact messages while
  the subagent work view exposes the full harness prompt and transcript.
- Frontend build succeeds against the API contract.
