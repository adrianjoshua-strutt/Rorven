# Model layer

## Principle

Agents and workflows select one model profile only:

- `utility`
- `balanced`
- `reasoning`
- `frontier`

They do not select provider names, model IDs, provider parameters, context requirements, or routing rules.

## Resolution

```text
Agent profile request
-> project override
-> global profile definition
-> provider adapter
-> normalized response
```

## Initial provider

OpenRouter is the first `ModelProvider` adapter. No OpenRouter-specific type, field, status, or model identifier may appear in domain entities, agent definitions, workflow contracts, or UI contracts.

The current implementation adds a provider-neutral `ModelGateway` port and an
OpenRouter chat-completions adapter. Local API and worker processes load
`RORVEN_OPENROUTER_API_KEY` from the process environment or the root `.env` file.
The key is used only by the adapter and is not returned through settings, events,
artifacts, prompts, or UI state.

Concrete model IDs are resolved from persisted model-profile settings. The local
file store seeds usable defaults into `settings.model_profiles` on startup, and
operators change them through the settings API/UI. Model profile IDs are not read
from environment variables.

When the key is absent, the composition root refuses to create the model gateway.
Tests that need deterministic responses patch the OpenRouter adapter or inject a
test gateway directly into application services; no local product gateway is
registered in composition.

When the key is present, model profiles are configured, and
`RORVEN_MODEL_GATEWAY` is `auto` or `openrouter`, root orchestrator messages and
project worker tasks use OpenRouter for model responses.

Project orchestrator worker calls use a strict provider-neutral JSON contract:
answer directly or dispatch approved child agents with text assignments. The
application layer parses and validates that contract before any child task is
persisted.

## Profile versioning

Profiles are immutable once used. Each run records:

- requested profile
- resolved profile version
- concrete provider adapter
- requested model ID
- actual model ID
- actual upstream provider when available
- retries and fallbacks
- token usage
- cost
- latency
- finish reason

## Fallback distinction

- Technical provider/model fallback belongs to the model layer.
- Quality escalation from one profile to another belongs to workflow logic.

## Overrides

Global defaults may be overridden per project. The agent still requests the same profile name.

## Settings visibility

The console may expose model-profile configuration status in the settings surface so an operator can see whether each approved profile is mapped. This is control-plane configuration metadata, not an agent, workflow, run, or memory contract.

The settings API must not place raw provider credentials in responses. Agent definitions and run records continue to store profile names only.

## Current limitation

The model-backed worker has brokered workspace inspection, direct text-file
writes, and bounded workspace shell commands for child agents only. It has no git
writes, browser, memory, external network-fetch, package-install, or sandbox
tools. Root orchestrators and child subagents produce persisted text artifacts,
write results, and shell observations; they must not claim they edited files or
ran commands unless brokered tool results prove it.
