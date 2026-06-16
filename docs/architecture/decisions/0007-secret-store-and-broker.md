# ADR 0007-secret-store-and-broker: Use an external secret store and credential broker

Status: Proposed  
Date: 2026-06-16

## Context

Autonomous agents must not inherit workstation credentials or receive raw secret values.

## Decision

Store secret values only in a dedicated secret store. Store references and bindings in platform PostgreSQL. Route external actions through brokered tools.

## Consequences

Some CLIs may require short-lived process injection, which must be isolated, audited, redacted, and revoked.

## Enforcement

Architecture tests, adapter contract tests, and review gates must verify this decision where applicable.
