# Read-Only Workspace Tools

Status: active

## Goal

Child agents can inspect ordinary project files through a brokered, policy-checked
tool path. Tool use must be persisted as events and artifacts, and agents must not
receive raw machine access.

## Requirements

- Add application-owned `ToolPolicy` and `ToolBroker` ports.
- Compose product workers with a deny-by-default read-only workspace policy.
- Compose product workers with a local read-only workspace tool adapter.
- Allow only child agents to request workspace tools.
- Support `workspace.list_files` and `workspace.read_text_file`.
- Confine broker paths to the project workspace root.
- Deny obvious secret paths such as `.env`, `.git`, keys, tokens, secrets, and
  credential files.
- Persist tool requests, denials, completions, failures, and output artifacts.
- Allow one tool round per child-agent execution before final output.

## Non-Goals

- File writes or edits.
- Shell, git, browser, network, or external service tools.
- Sandbox isolation.
- Human approval flows.
- Secret broker integration.
- Long-lived memory.

## Acceptance

- Backend tests cover policy denial, path escape prevention, local file reads,
  worker tool use, persisted tool events, and existing run flows.
- Frontend build succeeds against the unchanged API contract.
- ADR 0014 records the new ports and first adapter.
