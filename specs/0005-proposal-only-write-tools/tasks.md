# Tasks

- [x] Add `workspace.write_text_file`.
- [x] Enforce child-agent-only policy for workspace tools.
- [x] Deny sensitive paths.
- [x] Confine paths to the workspace root.
- [x] Write UTF-8 text files directly after policy evaluation.
- [x] Persist direct write tool artifacts through worker execution.
- [x] Add durable agent transcript entries.
- [x] Add API-managed local worker execution loop for single-process local use.
- [x] Add bounded multi-round subagent tool calls.
- [x] Keep subagent assignments/results out of the main user/orchestrator chat.
- [x] Keep full subagent harness prompts inspectable in the subagent work view.
- [x] Add bounded CLI command execution for child agents.
- [ ] Add sandbox isolation for mutable tools.
- [ ] Add recovery tests for interrupted writes.
- [ ] Add command approval policy for risky CLI operations.
