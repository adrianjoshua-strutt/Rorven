# ADR 0002-ports-and-adapters: Use ports and adapters

Status: Proposed  
Date: 2026-06-16

## Context

Runtime, model, memory, secret, sandbox, and storage technologies must remain replaceable.

## Decision

Domain and application layers own small interfaces. External technologies are implemented only in adapters.

## Consequences

Initial implementation requires more interface discipline but avoids platform lock-in and cross-layer rewrites.

## Enforcement

Architecture tests, adapter contract tests, and review gates must verify this decision where applicable.
