# System context

## Actors

### User

Creates projects, communicates with orchestrators, approves sensitive actions, reviews artifacts, configures model profiles, memory, permissions, and secret bindings.

### Agent run

A constrained workload identity that requests model inference and platform capabilities.

### External model provider

Receives normalized model requests through the model-provider adapter.

### External secret store

Stores raw secret values. The platform database stores references and policy metadata only.

### External services

Git hosts, package registries, databases, web services, and other systems accessed through brokered tools.

## Trust boundaries

1. Browser to API.
2. API to worker.
3. Worker to sandbox.
4. Platform to model provider.
5. Platform to secret store.
6. Tool broker to external service.
7. Project workspace boundary.

## High-level flow

User input is stored as a project command. The runtime adapter advances the orchestrator. The orchestrator may request child agent runs. Each child run executes with its own identity, permissions, model profile, checkpoint namespace, budget, and workspace lease.

Tool requests pass through the capability registry, permission engine, optional approval layer, secret broker, and audited adapter. Model requests pass through the model gateway and profile resolver.
