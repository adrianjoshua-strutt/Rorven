# ADR 0005-react-vite-fastapi: Use React/Vite and FastAPI

Status: Proposed  
Date: 2026-06-16

## Context

The UI is a desktop-like authenticated control plane and the agent ecosystem is strongest in Python.

## Decision

Use React with Vite and TypeScript for the web UI. Use FastAPI for the API. Serve the web app statically behind a reverse proxy.

## Consequences

Frontend and backend remain independently replaceable. Server-side rendering is intentionally omitted.

## Enforcement

Architecture tests, adapter contract tests, and review gates must verify this decision where applicable.
