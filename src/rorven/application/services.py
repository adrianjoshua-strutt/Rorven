"""Application services for the first durable execution slice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from rorven.application.ports import (
    AgentRuntime,
    ArtifactStore,
    EventRepository,
    RunRepository,
    TaskQueue,
)
from rorven.application.worker_service import WorkerService
from rorven.domain import (
    AgentRun,
    ArtifactMetadata,
    Event,
    EventType,
    Project,
    Run,
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
