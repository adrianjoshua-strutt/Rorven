# ADR 0004-postgres-system-of-record: Use PostgreSQL as system of record

Status: Proposed  
Date: 2026-06-16

## Context

Projects, runs, events, queue state, memory, versions, and configuration require durable transactional storage.

## Decision

Use PostgreSQL for platform domain data and the initial durable task queue. Isolate adapter-owned schemas.

## Consequences

Operations remain simple and transactional guarantees support recovery. Queue scaling limits are accepted initially.

## Enforcement

Architecture tests, adapter contract tests, and review gates must verify this decision where applicable.
