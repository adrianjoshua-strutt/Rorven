# Permissions and secrets

## Core principle

Agents receive authority to invoke capabilities, not access to credentials.

## Permission evaluation

Every tool request is evaluated using:

- agent-run identity
- agent-definition version
- project
- workflow and run
- requested capability
- resource scope
- operation
- policy conditions
- approval requirements

Default is deny.

## Secret scopes

- global secret references
- project secret references
- optional run-scoped temporary credentials

Project overrides are explicit bindings, not implicit same-name replacement.

Example:

```yaml
secret_bindings:
  github.default:
    project: secret://project/current/github/agent
    fallback: secret://global/github/default
```

## Secret handling

Raw values exist only inside the secret-store adapter, credential broker, authorized tool adapter, or a short-lived isolated process when unavoidable.

The application database stores:

- reference ID
- external path or key
- display metadata
- scope
- status
- allowed capability bindings
- audit metadata

It never stores a raw secret value.

## Brokered tools

Preferred flow:

```text
Agent -> Tool Broker -> Permission Engine -> Credential Broker -> Tool Adapter -> External Service
```

The first implemented tool slice is local read-only workspace inspection:

- `ToolBroker` is the application-owned port for tool execution.
- `ToolPolicy` is the application-owned port for authorization decisions.
- Product composition wires `WorkspaceReadPolicy` and `LocalWorkspaceToolBroker`.
- Child agents may request one round of `workspace.list_files`,
  `workspace.read_text_file`, or `workspace.propose_text_file_write`.
- Root orchestrators may not invoke workspace tools directly.
- Sensitive-looking paths such as `.env`, `.git`, key, token, secret, or
  credential files are denied before execution.
- Text-file write proposals return persisted unified diffs and do not modify the
  workspace.
- Tool requests, denials, completions, failures, and output artifacts are persisted
  for run inspection.
- No apply-write, shell, git, browser, network, or secret-bearing tools exist yet.

## Redaction

Central redaction is mandatory for tool outputs, exceptions, logs, events, and traces. Redaction is a defense-in-depth control and not a substitute for avoiding disclosure.

## Settings visibility

The settings surface may report whether a required credential binding or environment-backed secret is configured. It must not return raw secret material, masked fragments, prompt-ready credential text, or values that could be copied into an agent message.
