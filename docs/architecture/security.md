# Security architecture

## Security goals

- No ambient host credentials.
- No workspace escape.
- No unauthorized external side effects.
- No raw secret disclosure.
- Auditable decisions and tool executions.
- Controlled network access.
- Recoverable operations without duplicate side effects.

## Required controls

- sandbox per project run or compatible isolation boundary
- least-privilege filesystem mounts
- network policy or destination allowlists
- central tool broker
- deny-by-default permission engine
- explicit approvals for destructive or externally visible actions
- secret broker and workload identity
- token, cost, time, and concurrency limits
- global kill switch
- immutable audit events

## Current tool surface

The current product surface exposes brokered workspace inspection, direct
text-file writes, and bounded CLI commands for child agents:

- `workspace.list_files`
- `workspace.read_text_file`
- `workspace.write_text_file`
- `workspace.run_shell_command`

The local adapter confines paths to the project workspace root, skips common heavy
directories, blocks obvious secret paths, caps file/listing/command output, and
runs shell commands with sanitized environment and timeout limits. This is not a
sandbox boundary and does not authorize destructive commands, package installs,
git writes, browser use, or arbitrary network fetches.

## Threats to test

- prompt injection requesting secret access
- agent reading host home directory
- symlink escape from project root
- command output leaking credentials
- retry duplicating Git push or external write
- child agent inheriting parent permissions incorrectly
- project A reading project B memory or secrets
- provider-specific request metadata leaking into persisted state
