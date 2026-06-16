# ADR 0006-versioned-definitions: Version agents, prompts, workflows, and policies

Status: Proposed  
Date: 2026-06-16

## Context

Long-running work must be reproducible even after definitions change.

## Decision

Treat definitions as immutable after use. New changes create new versions. Runs record all resolved versions.

## Consequences

Storage and UX become slightly more complex, but historical runs remain explainable and reproducible.

## Enforcement

Architecture tests, adapter contract tests, and review gates must verify this decision where applicable.
