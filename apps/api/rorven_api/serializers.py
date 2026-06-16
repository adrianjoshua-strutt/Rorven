from __future__ import annotations

from datetime import datetime
from typing import Any

from rorven.application.services import ProjectState, RootActivity, RootDashboardState, RunState
from rorven.domain import AgentRun, Approval, ArtifactMetadata, Event, Project, Run, Task


def project_state_to_api(state: ProjectState) -> dict[str, Any]:
    data = project_to_api(state.project)
    data["runs"] = [run_to_api(run) for run in state.runs]
    return data


def run_state_to_api(state: RunState) -> dict[str, Any]:
    return {
        **run_to_api(state.run),
        "agent_runs": [agent_run_to_api(agent_run) for agent_run in state.agent_runs],
        "tasks": [task_to_api(task) for task in state.tasks],
        "events": [event_to_api(event) for event in state.events if event.run_id == state.run.id],
        "artifacts": [
            artifact_to_api(artifact, state.artifact_contents.get(artifact.id, ""))
            for artifact in state.artifacts
        ],
        "approvals": [approval_to_api(approval) for approval in state.approvals],
    }


def project_to_api(project: Project) -> dict[str, Any]:
    return {
        "id": project.id,
        "name": project.name,
        "workspace": {
            "allowed_root": project.workspace.allowed_root,
            "workspace_root": project.workspace.workspace_root,
        },
        "created_at": _dt(project.created_at),
    }


def run_to_api(run: Run) -> dict[str, Any]:
    return {
        "id": run.id,
        "project_id": run.project_id,
        "status": run.status.value,
        "command": run.command,
        "created_at": _dt(run.created_at),
        "completed_at": _dt(run.completed_at) if run.completed_at else None,
    }


def agent_run_to_api(agent_run: AgentRun) -> dict[str, Any]:
    return {
        "id": agent_run.id,
        "run_id": agent_run.run_id,
        "project_id": agent_run.project_id,
        "parent_agent_run_id": agent_run.parent_agent_run_id,
        "definition": {
            "name": agent_run.definition.name,
            "version": agent_run.definition.version,
            "model_profile": agent_run.definition.model_profile.value,
        },
        "status": agent_run.status.value,
        "input_artifact_id": agent_run.input_artifact_id,
        "result_artifact_id": agent_run.result_artifact_id,
        "created_at": _dt(agent_run.created_at),
    }


def task_to_api(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "agent_run_id": task.agent_run_id,
        "status": task.status.value,
        "lease_owner": task.lease_owner,
        "lease_expires_at": _dt(task.lease_expires_at) if task.lease_expires_at else None,
        "created_at": _dt(task.created_at),
    }


def event_to_api(event: Event) -> dict[str, Any]:
    return {
        "id": event.id,
        "project_id": event.project_id,
        "run_id": event.run_id,
        "type": event.type.value,
        "payload": event.payload,
        "occurred_at": _dt(event.occurred_at),
    }


def artifact_to_api(artifact: ArtifactMetadata, content: str) -> dict[str, Any]:
    return {
        "id": artifact.id,
        "project_id": artifact.project_id,
        "run_id": artifact.run_id,
        "kind": artifact.kind,
        "uri": artifact.uri,
        "content": content,
        "created_at": _dt(artifact.created_at),
    }


def approval_to_api(approval: Approval) -> dict[str, Any]:
    return {
        "id": approval.id,
        "project_id": approval.project_id,
        "run_id": approval.run_id,
        "agent_run_id": approval.agent_run_id,
        "artifact_id": approval.artifact_id,
        "action": approval.action,
        "status": approval.status.value,
        "created_at": _dt(approval.created_at),
        "decided_at": _dt(approval.decided_at) if approval.decided_at else None,
        "result_artifact_id": approval.result_artifact_id,
        "failure_reason": approval.failure_reason,
    }


def root_state_to_api(state: RootDashboardState) -> dict[str, Any]:
    return {
        "messages": list(state.messages),
        "activities": [root_activity_to_api(activity) for activity in state.activities],
    }


def root_activity_to_api(activity: RootActivity) -> dict[str, Any]:
    return {
        "id": activity.id,
        "name": activity.name,
        "modelProfile": activity.model_profile,
        "status": activity.status,
        "createdAt": activity.created_at,
        "summary": activity.summary,
    }


def _dt(value: datetime) -> str:
    return value.isoformat()
