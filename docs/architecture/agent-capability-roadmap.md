# Agent capability roadmap

Rorven's current project agents are real model-backed workers, but the active
runtime slice intentionally exposes only brokered workspace tools:

- `workspace.list_files`
- `workspace.read_text_file`
- `workspace.propose_text_file_write`
- `workspace.apply_text_file_write` after approval
- `workspace.run_shell_command` for bounded, workspace-scoped read/test/build
  commands

This keeps the first write path auditable while approvals, persistence, and
project chat history stabilize.

## Required E2E agent tools

To become a broad overnight-capable coding agent, Rorven needs additional
brokered tools behind domain-owned ports:

- Command approval broker: allow scoped approval for currently denied risky
  commands, command prefixes, directories, or sessions.
- Test runner broker: execute configured unit, integration, frontend, and e2e
  commands with summarized failures instead of asking agents to know the exact
  command every time.
- Git broker: inspect status/diff/log, create commits, push branches, and guard
  destructive operations behind policy.
- Multi-file patch broker: propose and apply atomic patch sets with per-file
  approval and rollback metadata.
- Package manager broker: install or update dependencies through explicit
  policy evaluation.
- Browser/dev-server broker: start local servers, inspect pages, run Playwright,
  and surface screenshots or trace artifacts.
- Search/index broker: build workspace search context without leaking secrets.
- Scheduler broker: let orchestrators schedule periodic checks or long-running
  follow-up work.

Every broker needs contract tests, persistence tests, approval policy coverage,
and explicit secret redaction before it becomes available to agents.

## Approval modes

The current text-file write path supports these persisted modes:

- `ask_each_time`: create a pending approval and pause only the subagent.
- `auto_apply_text_file_writes`: create an approval record and immediately apply
  the proposal under a standing policy.
- `reject_text_file_writes`: create and reject the proposal by policy.

Future command and patch brokers should use the same shape but add scoped rules,
for example approving one command, one command prefix, one directory, one
subagent type, or one session.

The first shell command tool is intentionally bounded: it runs only inside the
project workspace, strips raw secret-bearing environment variables, captures
stdout/stderr/exit code, caps timeout, and denies obvious destructive, network,
package-install, and secret-path commands.

## Current prompt source

The files under `config/agents` are example configuration documents only. The
active local runtime currently reads agent definitions from
`src/rorven/application/dispatching.py` and prompt text from
`src/rorven/application/agent_prompts.py`.

Moving agent definitions, immutable prompt versions, permission profiles, and
model profiles into a loaded registry is a separate architecture slice. That
slice should include migration tests and contract tests proving the registry
replaces the hardcoded definitions instead of becoming a parallel source of
truth.
