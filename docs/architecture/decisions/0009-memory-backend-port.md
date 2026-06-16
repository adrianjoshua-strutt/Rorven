# ADR 0009-memory-backend-port: Access project memory through MemoryBackend

Status: Proposed  
Date: 2026-06-16

## Context

Project memory must be replaceable and must not become hidden authoritative state.

## Decision

Use a typed MemoryBackend port. Implement PostgreSQL first. Preserve provenance, revision, invalidation, and UI visibility.

## Consequences

Advanced memory products can be integrated later through new adapters. Normative repository files remain authoritative.

## Enforcement

Architecture tests, adapter contract tests, and review gates must verify this decision where applicable.
