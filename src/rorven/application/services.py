"""Application services for the first durable execution slice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from rorven.application.modeling import ModelMessage, ModelRequest
from rorven.application.ports import (
    AgentRuntime,
    ArtifactStore,
    EventRepository,
    RunRepository,
    RootDashboardRepository,
    TaskQueue,
    ModelGateway,
)
from rorven.application.worker_service import WorkerService
from rorven.domain import (
    AgentRun,
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
    ) -> None:
        self._runs = runs
        self._events = events
        self._tasks = tasks
        self._runtime = runtime
        self._artifacts = artifacts

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
        self._runtime.plan_child_runs(run, parent)
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
        self._ensure_welcome_message()
        projects = self._project_stats()
        messages = self._root_messages.list_root_messages()
        return RootDashboardState(messages=messages, activities=self._build_activities(projects, "", False))

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
        activities = self._build_activities(projects, message, True)
        response = self._model_gateway.complete(
            ModelRequest(
                profile=ModelProfile.REASONING,
                session_id=f"root:{len(self._root_messages.list_root_messages())}",
                messages=(
                    ModelMessage(
                        "system",
                        "You are the root orchestrator for the Rorven control plane. Summarize live workspace inventory and answer operationally.",
                    ),
                    ModelMessage("user", _build_root_prompt(projects, message)),
                ),
                max_output_tokens=500,
            )
        )
        assistant_message = {
            "id": f"root-orchestrator-{len(self._root_messages.list_root_messages()) + 1}",
            "side": "orchestrator",
            "title": "Root orchestrator",
            "body": response.content.strip(),
            "time": _current_iso(),
            "status": response.provider,
        }
        self._root_messages.append_root_message(assistant_message)
        return RootDashboardState(messages=self._root_messages.list_root_messages(), activities=activities)

    def _ensure_welcome_message(self) -> None:
        if self._root_messages.list_root_messages():
            return
        self._root_messages.append_root_message(
            {
                "id": "root-orchestrator-ready",
                "side": "orchestrator",
                "title": "Root orchestrator",
                "body": "I manage the local Rorven installation. Ask me to create projects, find projects, inspect runs, or summarize workspace activity.",
                "time": _current_iso(),
                "status": "ready",
            }
        )

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

    def _build_activities(
        self,
        projects: Sequence[dict[str, object]],
        command: str,
        include_command: bool,
    ) -> list[RootActivity]:
        now = _current_iso()
        lower = command.lower()
        activities: list[RootActivity] = []
        matching_projects = [
            project
            for project in projects
            if any(
                token and len(token) >= 3 and str(project["name"]).lower().find(token) >= 0
                or token and len(token) >= 3 and str(project["workspace_root"]).lower().find(token) >= 0
                for token in lower.split()
            )
        ]

        if include_command and ("create" in lower or "new project" in lower or "workspace" in lower):
            activities.append(
                RootActivity(
                    id=f"root-project-creator-{now}",
                    name="project-creator",
                    model_profile="balanced",
                    status="completed",
                    created_at=now,
                    summary="Use the Create Project flow to register a workspace-scoped project in the API.",
                )
            )

        if include_command and ("search" in lower or "find" in lower or "list" in lower):
            targets = matching_projects if matching_projects else projects
            for project in targets[:3]:
                activities.append(
                    RootActivity(
                        id=f"root-project-search-{project['id']}",
                        name=str(project["name"]),
                        model_profile="utility",
                        status="completed",
                        created_at=now,
                        summary=f"{project['runs']} runs, {project['completed_runs']} completed, {project['active_runs']} active.",
                    )
                )

        if include_command and ("stat" in lower or "summary" in lower or "report" in lower):
            activities.append(
                RootActivity(
                    id=f"root-project-analyst-{now}",
                    name="project-analyst",
                    model_profile="utility",
                    status="completed",
                    created_at=now,
                    summary=_summarize_projects(projects),
                )
            )

        if not activities:
            for project in projects[:3]:
                activities.append(
                    RootActivity(
                        id=f"root-project-{project['id']}",
                        name=str(project["name"]),
                        model_profile="reasoning" if project["active_runs"] else "utility",
                        status="started" if project["active_runs"] else "ready",
                        created_at=now,
                        summary=f"{project['runs']} runs recorded for {project['workspace_root']}.",
                    )
                )

        return activities


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
        "Respond as the root orchestrator for the Rorven control plane. Keep it operational and concise."
    )
    return "\n".join(lines)


def _summarize_projects(projects: Sequence[dict[str, object]]) -> str:
    project_count = len(projects)
    run_count = sum(int(project["runs"]) for project in projects)
    active_run_count = sum(int(project["active_runs"]) for project in projects)
    if project_count == 0:
        return "No projects are registered yet. Create one to start durable work."
    return (
        f"Tracking {project_count} project{'s' if project_count != 1 else ''}. "
        f"{run_count} run{'s' if run_count != 1 else ''} recorded across the workspace. "
        + (
            f"{active_run_count} run{'s' if active_run_count != 1 else ''} are still active."
            if active_run_count > 0
            else "No active runs are currently in flight."
        )
    )


def _current_iso() -> str:
    return __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat()
