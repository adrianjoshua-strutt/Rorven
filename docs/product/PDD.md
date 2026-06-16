# Product Design Document

## 1. Product name

Product name: Rorven

Naming status: Provisional public development name; legal clearance and identifier reservation remain pending.

## 2. Product vision

Rorven is a self-hosted platform for durable, long-running, multi-agent project work. A user interacts primarily with one project orchestrator. The orchestrator delegates to specialized agents, which may run in parallel, request input, produce artifacts, and spawn additional work under controlled policies.

The product is intended for serious private software and knowledge-work projects, not one-off chat sessions.

## 3. Primary user experience

The user opens a web UI and sees a list of projects. Each project maps to a local or managed workspace root.

Within a project, the user communicates with a main orchestrator. The orchestrator delegates work to specialized agents such as coder, reviewer, researcher, test engineer, Git agent, or infrastructure agent.

The user can:

- close the browser while work continues,
- inspect a tree of active and completed agent runs,
- provide input when a run is interrupted,
- pause, resume, cancel, or retry work,
- inspect tool executions, artifacts, diffs, costs, and structured decisions,
- review and edit project memory,
- configure project-specific model-profile and secret overrides,
- resume work after server or worker failure.

## 4. Product goals

- Durable multi-agent execution.
- Strong project isolation.
- Modular and replaceable technical subsystems.
- Explicit permissions and secret isolation.
- Reproducible, versioned agent behavior.
- Clear observability and auditability.
- Simple self-hosting for one user or a small trusted group.
- A foundation that can evolve without rewriting UI, APIs, agents, prompts, or permissions. Persisted project data is evolved through automatic versioned migrations.

## 5. Non-goals for the first release

- General-purpose visual workflow builder.
- Public multi-tenant SaaS.
- Marketplace for agents or plugins.
- Fully autonomous creation of arbitrary new agent types.
- Kubernetes requirement.
- Distributed execution across multiple physical hosts.
- Desktop virtualization.
- Support for every model provider or memory backend.

## 6. Core concepts

### Project

A durable container for workspace binding, conversations, runs, memory, agent configuration, model-profile overrides, permission policies, secret bindings, artifacts, and statistics.

### Orchestrator

The primary agent that communicates with the user and delegates work. It is not expected to perform all work directly.

### Agent definition

A versioned configuration containing role, prompt reference, tools, permission profile, memory policy, model profile, and completion contract.

### Agent run

One execution of an agent definition within a project and parent run. Agent runs form a tree.

### Workflow

A versioned orchestration definition that determines how agents are spawned, joined, retried, escalated, paused, and completed.

### Memory

Typed, scoped, provenance-aware project knowledge. Memory is contextual, editable, invalidatable, and subordinate to normative repository documentation.

### Model profile

One of four stable names selected by agents and workflows: `utility`, `balanced`, `reasoning`, or `frontier`. Concrete models are resolved centrally.

### Capability

An action the platform may perform on behalf of an agent, such as reading a file, running tests, creating a branch, or opening a pull request.

## 7. Functional requirements

### Projects

- Create, archive, search, and open projects.
- Bind each project to a workspace root.
- Store project configuration and overrides.

### Conversations

- Maintain a durable conversation with the project orchestrator.
- Preserve run links and artifacts across restarts.

### Agent execution

- Spawn one or more subagents.
- Run independent subagents concurrently.
- Wait for all, any, or policy-defined subsets.
- Support nested child runs.
- Persist parent-child relationships and status.

### Durability

- Continue work after browser closure.
- Recover after API restart.
- Recover or retry after worker loss.
- Persist interrupts and pending approvals.

### Permissions and secrets

- Deny by default.
- Evaluate every tool execution against agent, project, run, resource, and policy.
- Support global and project secret bindings with explicit override behavior.
- Never expose raw secret values to agents.

### Memory

- Search, write, revise, invalidate, and inspect project memory.
- Record provenance and confidence.
- Support replacement of the memory backend.

### Models

- Agents choose one of four profiles only.
- Resolve profiles globally with optional project overrides.
- Use OpenRouter as the first provider adapter.
- Record actual model, provider, usage, cost, latency, and fallback path.


### Upgrades and evolution

- Detect platform and adapter schema versions during startup.
- Apply ordered, versioned migrations before API, worker, and scheduler readiness.
- Migrate first-party data, configuration, and stored definitions to the current canonical model.
- Block startup on failed migration rather than running mixed historical models.
- Prefer rebuilding derived data when safer than migration.
- Require an ADR, isolation boundary, owner, metrics where practical, and removal date for every backward-compatibility exception.
- Do not guarantee downgrade-in-place; restore a compatible backup when necessary.

### UI

- Project list.
- Project chat.
- Run and agent tree.
- Live event stream.
- Approval and input requests.
- Artifact and diff viewer.
- Memory editor.
- Secret metadata and binding editor without value disclosure.
- Cost and usage views.

## 8. Non-functional requirements

- Modular monolith with strict import boundaries.
- PostgreSQL as the system of record.
- API, worker, and scheduler as separate processes.
- Recoverable and idempotent background execution.
- Structured logs and append-only lifecycle events.
- Contract tests for all adapters.
- Architecture tests in CI.
- Self-hostable with Docker Compose.
- Backup and restore documentation before stable release.
- One canonical internal model, reached through automatic ordered migrations before readiness.
- Backward-compatibility layers only as isolated, time-bounded exceptions approved by ADR.

## 9. Success criteria for version 1

A user can create a project, bind a workspace, ask an orchestrator to complete a task, observe two parallel subagents, close the browser, restart the API and one worker, reopen the project, provide an interrupt response, and receive a final result without duplicate destructive actions or secret exposure.

## 10. Product principles

- Durable before clever.
- Explicit before magical.
- Replaceable before provider-specific.
- Observable before autonomous.
- Controlled authority instead of credential access.
- Specifications and tests before implementation.
- Migration before compatibility branches.
- Current model in runtime; history belongs in migrations and ADRs.
