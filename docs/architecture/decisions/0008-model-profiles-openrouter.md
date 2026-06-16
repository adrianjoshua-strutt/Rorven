# ADR 0008-model-profiles-openrouter: Use four model profiles and OpenRouter first

Status: Proposed  
Date: 2026-06-16

## Context

Agents should not manage model IDs or provider complexity. Initial provider breadth is desirable.

## Decision

Agents choose only utility, balanced, reasoning, or frontier. Use OpenRouter as the first provider adapter with global defaults and project overrides.

## Consequences

Provider details remain centralized. A later direct provider adapter can be added without changing agents or workflows.

## Enforcement

Architecture tests, adapter contract tests, and review gates must verify this decision where applicable.
