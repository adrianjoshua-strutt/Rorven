# Plan

## Implemented Slice

1. Extend tool policy support for direct workspace text writes.
2. Extend the local workspace broker with `workspace.write_text_file`.
3. Teach prompts that subagents are autonomous coding workers that should inspect,
   edit, run bounded CLI commands, verify, and report.
4. Add adapter, worker, and API tests proving direct mutation occurs only inside
   the workspace.
5. Keep durable agent transcript entries for user messages, assignments, tool
   results, approvals, and final answers.
6. Add an API-managed local worker supervisor so local project chat progresses
   without manually starting a separate worker process.
7. Allow child agents to use bounded multi-round workspace tools, so they can
   inspect files, edit files, run CLI commands, and verify work.
8. Render project chat as root user/orchestrator turns and compact subagent
   status messages; keep full subagent harness and transcript in the inspectable
   subagent work view.

## Next Slices

1. Add idempotency keys and recovery tests for interrupted writes.
2. Add sandbox isolation around mutable tools and shell commands.
3. Add broader command approval policy for risky CLI operations.
4. Add atomic multi-file patch support after recovery semantics are proven.
