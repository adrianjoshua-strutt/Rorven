# ADR 0015-approval-records-approved-workspace-apply: Add approval records for mutable workspace actions

Status: Proposed  
Date: 2026-06-16

## Context

Proposal-only workspace writes create auditable diffs but leave no durable decision
record for the human approval step. Mutable workspace actions need persisted
approval state before Rorven can safely expose apply behavior.

## Decision

Add an application-owned `ApprovalRepository` port and a domain `Approval` record.
The local file adapter implements the port while PostgreSQL remains the target
production repository.

Child agents still only request `workspace.propose_text_file_write`. When a
proposal tool succeeds, the worker creates a pending approval linked to the tool
artifact. The API exposes run-scoped approval listing plus explicit approve and
reject endpoints. Approval applies a proposal by calling the existing workspace
tool broker with `workspace.apply_text_file_write`; this tool is not exposed
through agent policy.

## Consequences

Mutable workspace writes now require a durable approval record and can be observed
through run state, approval state, artifacts, and lifecycle events. The local
apply adapter is still not sandboxed and does not yet provide full idempotency or
interrupted-apply recovery.

## Enforcement

Backend tests cover pending approval creation from a proposal, API approval
application, local persistence migration for the approvals bucket, and direct
broker apply behavior. Existing policy tests continue to prove agents cannot
directly request unsupported mutable tools.
