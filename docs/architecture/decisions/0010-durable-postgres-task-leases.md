# ADR 0010-durable-postgres-task-leases: Use durable database-backed task leases first

Status: Proposed  
Date: 2026-06-16

## Context

Parallel child agents must survive process loss and must not rely on in-memory asyncio tasks.

## Decision

Persist tasks before execution. Workers claim tasks using transactional leases and heartbeats. Parent joins depend on durable child states.

## Consequences

This avoids an early dependency on a large workflow platform. A future task backend can replace the adapter.

## Enforcement

Architecture tests, adapter contract tests, and review gates must verify this decision where applicable.
