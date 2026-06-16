# ADR 0003-langgraph-runtime-adapter: Use LangGraph only behind AgentRuntime

Status: Proposed  
Date: 2026-06-16

## Context

Durable agent execution, checkpoints, interrupts, and subgraphs are needed, but platform concepts must not depend on one runtime.

## Decision

Implement LangGraph as the first AgentRuntime adapter. Platform run data remains in platform-owned tables.

## Consequences

LangGraph can be replaced without changing UI, API contracts, agent definitions, permissions, memory, or project data.

## Enforcement

Architecture tests, adapter contract tests, and review gates must verify this decision where applicable.
