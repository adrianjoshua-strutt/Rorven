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
