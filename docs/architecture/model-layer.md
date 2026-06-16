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

When the key is absent, the composition root selects a local gateway so durability
and UI reconstruction remain testable. When the key is present and
`RORVEN_MODEL_GATEWAY` is `auto` or `openrouter`, workers use OpenRouter for
subagent result generation and orchestrator summaries.

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

The first model-backed worker slice has no brokered filesystem, shell, memory, or
sandbox tools. Model-backed subagents produce persisted text artifacts and
orchestrator summaries; they must not claim they edited files or ran commands until
the tool-broker and sandbox slices exist.
