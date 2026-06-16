# Project Constitution

Version: 1.1.0  
Status: Draft for approval

## Article I — Adapter-first extensibility

All replaceable technologies and external systems must be accessed through explicit, platform-owned ports.

A new capability must be implemented by one of the following:

1. extending an existing adapter behind an unchanged port,
2. adding a new adapter implementing an existing port,
3. defining a new port through an approved ADR.

Direct provider-, framework-, runtime-, memory-, secret-store-, model-provider-, sandbox-, database-, transport-, or object-store-specific logic in domain, application, API contracts, UI contracts, workflows, prompts, or agent definitions is prohibited.

## Article II — Domain independence

The domain and application layers must not depend on FastAPI, LangGraph, OpenRouter, PostgreSQL drivers, secret-store SDKs, Docker SDKs, model SDKs, or frontend frameworks.

Dependency direction always points inward.

## Article III — Modular monolith first

The initial product is one repository and one logical application with separate API, worker, and scheduler processes.

Microservices, Kafka, Kubernetes, and distributed transactions require a separate ADR and demonstrated operational need.

## Article IV — Durable execution

Long-running work must survive browser closure, API restart, worker loss, and recoverable infrastructure failure.

Every externally meaningful state transition must be persisted before dependent work begins. Tool actions that can cause side effects must be idempotent or protected by deduplication keys.

## Article V — Explicit permissions and least privilege

Agents receive capabilities, not ambient machine access. Every tool call is evaluated against agent identity, project scope, run scope, resource scope, and policy conditions.

Default policy is deny.

## Article VI — Secret non-disclosure

Raw secret material must never be exposed to an agent or persisted in prompts, model messages, graph state, checkpoints, memory, events, traces, logs, artifacts, command history, exception text, or UI state.

Agents receive authority to perform actions through brokered tools. They do not receive credentials.

## Article VII — Model-profile abstraction

Agents and workflows select only one approved model profile. Concrete model IDs, provider routing, retry behavior, and provider configuration belong exclusively to the model layer.

Initial profiles are:

- `utility`
- `balanced`
- `reasoning`
- `frontier`

## Article VIII — Versioned definitions

Agent definitions, prompts, workflows, model profiles, permission profiles, memory policies, tool schemas, and runtime configuration are immutable after use and versioned explicitly.

Every run records the exact versions it resolved.

## Article IX — Documentation is part of the change

A feature is incomplete until its specification, architecture impact, tests, validation evidence, operational implications, and project state are updated.

## Article X — Architecture enforcement

Architectural rules must be enforced through automated tests where practical. Intent expressed only in prose is insufficient for critical boundaries.

## Article XI — Observable execution

Runs expose structured state, parent-child relationships, tool executions, approvals, artifacts, usage, errors, and lifecycle events.

Private chain-of-thought is neither required nor stored. Store structured plans, decisions, tool calls, outputs, and concise rationale instead.

## Article XII — Normative truth hierarchy

Repository-controlled normative documents override runtime memory and conversational context. Memory is contextual and correctable, never authoritative.

## Article XIII — Migration-first evolution

Rorven maintains one canonical internal model. Persisted data, configuration, stored definitions, and adapter-owned metadata are migrated to that model before normal use.

Backward-compatibility code is an exception, not a default strategy. Runtime branches for historical schemas, dual-read or dual-write paths, legacy DTOs, and permanent old-model adapters are prohibited unless an accepted ADR proves that migration cannot reasonably solve the compatibility requirement.

Every approved compatibility exception must be isolated, owned, observable, time-bounded, and removable. It must define a removal condition and latest removal date.

Automatic startup migrations must be ordered, tested, auditable, restart-safe, and blocking on failure. A failed migration must not silently enable legacy behavior.
