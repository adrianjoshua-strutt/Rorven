# ADR 0015-approval-records-approved-workspace-apply: Add approval records for mutable workspace actions

Status: Proposed; text-file write execution superseded by ADR 0019  
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

The web console ingests run approvals from the run-state API and renders them in
the subagent work view beside the transcript and proposal artifact. Human approve
or reject actions call the explicit approval endpoints and then reload the run.
Approval decisions also append inspectable transcript entries for the producing
agent run.

## Consequences

Mutable workspace writes now require a durable approval record and can be observed
through run state, approval state, artifacts, lifecycle events, the subagent work
view, and agent transcript entries. The local apply adapter is still not sandboxed
and does not yet provide full idempotency or interrupted-apply recovery.

## Enforcement

Backend tests cover pending approval creation from a proposal, API approval
application, transcript entries for approval decisions, local persistence
migration for the approvals bucket, and direct broker apply behavior. Existing
policy tests continue to prove agents cannot directly request unsupported mutable
tools. Frontend build and Playwright smoke tests cover console ingestion.
