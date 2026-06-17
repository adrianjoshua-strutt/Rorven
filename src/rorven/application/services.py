"""Application services for the first durable execution slice."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Sequence

from rorven.application.modeling import ModelMessage, ModelRequest
from rorven.application.ports import (
    AgentRuntime,
    ApprovalRepository,
    ArtifactStore,
    EventRepository,
    RunRepository,
    RootDashboardRepository,
    TaskQueue,
    ModelGateway,
    ToolBroker,
)
from rorven.application.tools import ToolExecutionResult, ToolRequest
from rorven.application.worker_service import WorkerService
from rorven.domain import (
    AgentRun,
    Approval,
    ApprovalStatus,
    ArtifactMetadata,
    Event,
    EventType,
    Project,
    ModelProfile,
    Run,
    RunStatus,
    Task,
    WorkspaceBinding,
)


@dataclass(frozen=True, slots=True)
class ProjectState:
    project: Project
    runs: Sequence[Run]


@dataclass(frozen=True, slots=True)
class RunState:
    run: Run
    agent_runs: Sequence[AgentRun]
    tasks: Sequence[Task]
    events: Sequence[Event]
    artifacts: Sequence[ArtifactMetadata]
    artifact_contents: dict[str, str]
    approvals: Sequence[Approval]


@dataclass(frozen=True, slots=True)
class RootActivity:
    id: str
    name: str
    model_profile: str
    status: str
    created_at: str
    summary: str


@dataclass(frozen=True, slots=True)
class RootDashboardState:
    messages: Sequence[dict[str, str]]
    activities: Sequence[RootActivity]


class ProjectService:
    def __init__(
        self,
        runs: RunRepository,
        events: EventRepository,
        tasks: TaskQueue,
        runtime: AgentRuntime,
        artifacts: ArtifactStore,
        approvals: ApprovalRepository,
    ) -> None:
        self._runs = runs
        self._events = events
        self._tasks = tasks
        self._runtime = runtime
        self._artifacts = artifacts
        self._approvals = approvals

    def list_projects(self) -> Sequence[Project]:
        return self._runs.list_projects()

    def create_project(self, name: str, allowed_root: str, workspace_root: str) -> Project:
        workspace_key = _workspace_key(workspace_root)
        for existing in self._runs.list_projects():
            if _workspace_key(existing.workspace.workspace_root) == workspace_key:
                raise ValueError(
                    f"project already exists for workspace root: {workspace_root}"
                )
        project = Project.create(
            name=name,
            workspace=WorkspaceBinding(allowed_root=allowed_root, workspace_root=workspace_root),
        )
        event = Event.create(project.id, EventType.PROJECT_CREATED, {"project_id": project.id})
        self._runs.add_project(project, event)
        return project

    def get_project_state(self, project_id: str) -> ProjectState:
        return ProjectState(
            project=self._runs.get_project(project_id),
            runs=self._runs.list_runs(project_id),
        )

    def submit_task(self, project_id: str, command: str) -> RunState:
        project = self._runs.get_project(project_id)
        run = self._runtime.start_parent_run(project, command)
        parent = self._root_agent_run(project.id, run.id)
        task = Task.create(parent.id)
        self._tasks.enqueue(
            [task],
            [
                Event.create(
                    project.id,
                    EventType.TASK_QUEUED,
                    {"task_id": task.id, "agent_run_id": parent.id},
                    run.id,
                )
            ],
        )
        return self.get_run_state(project_id, run.id)

    def get_run_state(self, project_id: str, run_id: str) -> RunState:
        artifacts = self._artifacts.list_artifacts_for_run(run_id)
        return RunState(
            run=self._runs.get_run(project_id, run_id),
            agent_runs=self._runs.get_run_tree(project_id, run_id),
            tasks=self._tasks.list_for_run(run_id),
            events=self._events.list_project_events(project_id),
            artifacts=artifacts,
            artifact_contents={artifact.id: self._artifacts.get_text(artifact.id) for artifact in artifacts},
            approvals=self._approvals.list_approvals_for_run(run_id),
        )

    def _root_agent_run(self, project_id: str, run_id: str) -> AgentRun:
        roots = [
            agent_run
            for agent_run in self._runs.get_run_tree(project_id, run_id)
            if agent_run.parent_agent_run_id is None
        ]
        if len(roots) != 1:
            raise RuntimeError(f"expected one root agent run for run {run_id}, found {len(roots)}")
        return roots[0]


def _workspace_key(value: str) -> str:
    return value.replace("\\", "/").rstrip("/").lower()


def _tool_request_without_content(request: ToolRequest) -> dict[str, object]:
    sanitized = dict(request.input)
    if "content" in sanitized:
        value = sanitized.pop("content")
        if isinstance(value, str):
            sanitized["content_bytes"] = len(value.encode("utf-8"))
        else:
            sanitized["content_present"] = True
    return {"name": request.name, "input": sanitized}


class ApprovalService:
    def __init__(
        self,
        runs: RunRepository,
        approvals: ApprovalRepository,
        artifacts: ArtifactStore,
        tool_broker: ToolBroker,
    ) -> None:
        self._runs = runs
        self._approvals = approvals
        self._artifacts = artifacts
        self._tool_broker = tool_broker

    def list_for_run(self, project_id: str, run_id: str) -> Sequence[Approval]:
        self._runs.get_run(project_id, run_id)
        return self._approvals.list_approvals_for_run(run_id)

    def approve(self, project_id: str, run_id: str, approval_id: str) -> Approval:
        approval = self._scoped_approval(project_id, run_id, approval_id)
        if approval.status == ApprovalStatus.APPLIED:
            return approval
        if approval.status == ApprovalStatus.REJECTED:
            raise ValueError("rejected approvals cannot be applied")
        if approval.status == ApprovalStatus.FAILED:
            raise ValueError("failed approvals require a new proposal")

        try:
            request = self._apply_request_from_proposal(approval)
            agent_run = self._runs.get_agent_run(approval.agent_run_id)
            project = self._runs.get_project(approval.project_id)
            result = self._tool_broker.execute(project, agent_run, request)
            result_artifact = self._put_apply_artifact(approval, request, result, error=None)
            applied = approval.apply(result_artifact.id)
            self._approvals.update_approval(
                applied,
                [
                    Event.create(
                        approval.project_id,
                        EventType.APPROVAL_APPLIED,
                        {
                            "approval_id": approval.id,
                            "artifact_id": approval.artifact_id,
                            "result_artifact_id": result_artifact.id,
                        },
                        approval.run_id,
                    )
                ],
            )
            return applied
        except Exception as exc:
            failed = approval.fail(str(exc))
            self._approvals.update_approval(
                failed,
                [
                    Event.create(
                        approval.project_id,
                        EventType.APPROVAL_FAILED,
                        {"approval_id": approval.id, "reason": str(exc)},
                        approval.run_id,
                    )
                ],
            )
            raise

    def reject(self, project_id: str, run_id: str, approval_id: str) -> Approval:
        approval = self._scoped_approval(project_id, run_id, approval_id)
        if approval.status == ApprovalStatus.APPLIED:
            raise ValueError("applied approvals cannot be rejected")
        if approval.status == ApprovalStatus.REJECTED:
            return approval
        rejected = approval.reject()
        self._approvals.update_approval(
            rejected,
            [
                Event.create(
                    approval.project_id,
                    EventType.APPROVAL_REJECTED,
                    {"approval_id": approval.id, "artifact_id": approval.artifact_id},
                    approval.run_id,
                )
            ],
        )
        return rejected

    def _scoped_approval(self, project_id: str, run_id: str, approval_id: str) -> Approval:
        approval = self._approvals.get_approval(approval_id)
        if approval.project_id != project_id or approval.run_id != run_id:
            raise KeyError(f"approval not found in run: {approval_id}")
        return approval

    def _apply_request_from_proposal(self, approval: Approval) -> ToolRequest:
        payload = json.loads(self._artifacts.get_text(approval.artifact_id))
        request = payload.get("request")
        result = payload.get("result")
        if not isinstance(request, dict) or request.get("name") != "workspace.propose_text_file_write":
            raise ValueError("approval does not reference a text-file write proposal")
        tool_input = request.get("input")
        if not isinstance(tool_input, dict):
            raise ValueError("proposal input is invalid")
        metadata = result.get("metadata") if isinstance(result, dict) else None
        if not isinstance(metadata, dict) or metadata.get("applied") is not False:
            raise ValueError("proposal result is invalid or already applied")
        path = tool_input.get("path")
        content = tool_input.get("content")
        if not isinstance(path, str) or not isinstance(content, str):
            raise ValueError("proposal path and content are required")
        return ToolRequest(
            "workspace.apply_text_file_write",
            {
                "path": path,
                "content": content,
                "proposal_artifact_id": approval.artifact_id,
                "approval_id": approval.id,
            },
        )

    def _put_apply_artifact(
        self,
        approval: Approval,
        request: ToolRequest,
        result: ToolExecutionResult,
        error: str | None,
    ) -> ArtifactMetadata:
        content = {
            "request": _tool_request_without_content(request),
            "approval_id": approval.id,
            "proposal_artifact_id": approval.artifact_id,
            "result": None if result is None else {"content": result.content, "metadata": result.metadata},
            "error": error,
        }
        return self._artifacts.put_text(
            project_id=approval.project_id,
            run_id=approval.run_id,
            kind="tool.execution",
            name=f"approved-apply-{approval.id}.json",
            content=json.dumps(content, indent=2, sort_keys=True),
        )


class RootService:
    def __init__(
        self,
        runs: RunRepository,
        root_messages: RootDashboardRepository,
        model_gateway: ModelGateway,
    ) -> None:
        self._runs = runs
        self._root_messages = root_messages
        self._model_gateway = model_gateway

    def get_root_state(self) -> RootDashboardState:
        messages = self._filtered_root_messages()
        return RootDashboardState(messages=messages, activities=[])

    def submit_message(self, message: str) -> RootDashboardState:
        user_message = {
            "id": f"root-user-{len(self._root_messages.list_root_messages()) + 1}",
            "side": "user",
            "title": "You",
            "body": message,
            "time": _current_iso(),
        }
        self._root_messages.append_root_message(user_message)
        projects = self._project_stats()
        response = self._model_gateway.complete(
            ModelRequest(
                profile=ModelProfile.REASONING,
                session_id=f"root:{len(self._root_messages.list_root_messages())}",
                messages=(
                    ModelMessage(
                        "system",
                        _root_system_prompt(),
                    ),
                    ModelMessage("user", _build_root_prompt(projects, message)),
                ),
                max_output_tokens=240,
            )
        )
        assistant_message = {
            "id": f"root-orchestrator-{len(self._root_messages.list_root_messages()) + 1}",
            "side": "orchestrator",
            "title": "Root orchestrator",
            "body": _normalize_root_response(response.content),
            "time": _current_iso(),
            "status": response.provider,
        }
        self._root_messages.append_root_message(assistant_message)
        return RootDashboardState(messages=self._filtered_root_messages(), activities=[])

    def _filtered_root_messages(self) -> list[dict[str, str]]:
        hidden_seed_bodies = {
            "I manage the local Rorven installation. Ask me to create projects, find projects, inspect runs, or summarize workspace activity.",
            "Create a new project for this repository.",
        }
        return [
            message
            for message in self._root_messages.list_root_messages()
            if str(message.get("body", "")).strip() not in hidden_seed_bodies
        ]

    def _project_stats(self) -> list[dict[str, object]]:
        projects: list[dict[str, object]] = []
        for project in self._runs.list_projects():
            runs = self._runs.list_runs(project.id)
            projects.append(
                {
                    "id": project.id,
                    "name": project.name,
                    "workspace_root": project.workspace.workspace_root,
                    "runs": len(runs),
                    "active_runs": len([run for run in runs if run.status != RunStatus.COMPLETED]),
                    "completed_runs": len([run for run in runs if run.status == RunStatus.COMPLETED]),
                }
            )
        return projects


def _root_system_prompt() -> str:
    return "\n".join(
        [
            "You are the root project orchestrator for Rorven.",
            "The root project helps the operator find, register, and inspect projects.",
            "Current limitation: this chat cannot yet create or register projects by itself.",
            "If the user asks to create/register a project, ask only for the missing project name and exact workspace folder path, and mention that the Project button can register it now.",
            "Write for an application chat bubble, not a document.",
            "Use plain text only: no Markdown, no bold markers, no headings, no bullet lists, no code fences.",
            "Answer in one to three short sentences.",
        ]
    )


def _build_root_prompt(projects: Sequence[dict[str, object]], command: str) -> str:
    lines = [
        f"User request: {command}",
        "Live project inventory:",
    ]
    for project in projects:
        lines.append(
            f"- {project['name']} at {project['workspace_root']}: {project['runs']} runs, {project['active_runs']} active, {project['completed_runs']} completed"
        )
    lines.append(
        "Respond plainly as the root project orchestrator. Do not format with Markdown."
    )
    return "\n".join(lines)


def _normalize_root_response(content: str) -> str:
    lines: list[str] = []
    for raw_line in content.strip().splitlines():
        line = raw_line.strip()
        if not line:
            if lines and lines[-1]:
                lines.append("")
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        line = line.replace("**", "").replace("__", "").replace("`", "")
        lines.append(line.rstrip())
    normalized = "\n".join(lines).strip()
    return normalized or "I could not produce a usable root project response."


def _current_iso() -> str:
    return __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat()
