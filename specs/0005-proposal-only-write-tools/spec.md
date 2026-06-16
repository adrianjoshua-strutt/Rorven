# Proposal-Only Write Tools

Status: active

## Goal

Child agents can propose text-file changes through the tool broker without applying
them. The proposal is persisted as a unified diff artifact for inspection and later
approval/apply flows.

## Requirements

- Extend the existing `ToolBroker` and `ToolPolicy` ports; do not add direct
  filesystem access to agents.
- Add `workspace.propose_text_file_write`.
- Restrict proposal tools to child agents.
- Confine proposal paths to the project workspace root.
- Deny obvious secret paths.
- Limit proposed text size.
- Return a unified diff artifact and metadata with `applied: false`.
- Prove the workspace file is not mutated.

## Non-Goals

- Applying changes.
- Human approval UI.
- Shell, git, browser, network, or external service tools.
- Sandbox isolation.
- Multi-file patch application.

## Acceptance

- Backend tests prove proposal diffs are generated and files remain unchanged.
- Worker tests prove proposal artifacts are persisted in a run.
- Worker tests prove successful proposals create pending approvals.
- API tests prove approved proposal application mutates the target file only
  after approval.
- Frontend build succeeds against the unchanged API contract.
