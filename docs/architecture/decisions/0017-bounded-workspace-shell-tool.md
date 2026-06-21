# ADR 0017-bounded-workspace-shell-tool: Add a policy-checked workspace shell command tool

Status: Proposed  
Date: 2026-06-21

## Context

Rorven needs agents that can verify work, inspect runtime behavior, and run local
project commands. A raw subprocess escape hatch would violate the ports-and-
adapters boundary, leak secrets through inherited environment variables, and
make destructive behavior hard to govern.

## Decision

Expose shell execution only through the existing `ToolBroker` and `ToolPolicy`
ports as `workspace.run_shell_command`.

The first local adapter implementation:

- runs commands with the project workspace as the root and optional cwd scoped
  inside that workspace;
- captures stdout, stderr, return code, timeout status, cwd, and output sizes;
- caps command length and timeout;
- strips raw secret-bearing environment variables before execution;
- denies root-orchestrator access;
- denies obvious destructive, package-install, network-fetch, and secret-path
  commands through policy while allowing safe diagnostics such as version checks
  or `ping` when policy accepts them.

Agents may use this tool for bounded read, test, build, and inspection commands.
Risky command approvals are not part of this decision and require a later policy
extension.

## Consequences

Implementer and reviewer subagents can now gather runtime evidence without
claiming unsupported machine access. The tool is still not a complete sandbox.
It must not be treated as permission to run arbitrary commands, mutate the
workspace without approval, install dependencies, push to remotes, or fetch from
network services. Connectivity diagnostics may be run only through the same
policy-checked brokered command path.

## Enforcement

Backend tests cover safe command allowance, destructive command denial, scoped
workspace command execution, and existing root-agent denial. Architecture tests
continue to prevent provider/framework imports in domain and application code.
