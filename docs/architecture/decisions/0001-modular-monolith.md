# ADR 0001-modular-monolith: Use a modular monolith

Status: Proposed  
Date: 2026-06-16

## Context

The platform needs strong boundaries but should remain simple to self-host and operate.

## Decision

Use one repository and one logical application with separate web, API, worker, and scheduler processes. Use one PostgreSQL system of record.

## Consequences

Internal boundaries must be explicit. Distributed infrastructure is deferred until justified by measured need.

## Enforcement

Architecture tests, adapter contract tests, and review gates must verify this decision where applicable.
