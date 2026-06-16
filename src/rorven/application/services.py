"""Application services for the first durable execution slice."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Sequence

from rorven.application.ports import AgentRuntime, ArtifactStore, EventRepository, RunRepository, TaskQueue
from rorven.domain import (
    AgentRun,
    Event,
    EventType,
    Project,
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


class ProjectService:
    def __init__(
        self,
        runs: RunRepository,
        events: EventRepository,
        tasks: TaskQueue,
        runtime: AgentRuntime,
    ) -> None:
        self._runs = runs
        self._events = events
        self._tasks = tasks
        self._runtime = runtime

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
        return RunState(
            run=self._runs.get_run(project_id, run_id),
            agent_runs=self._runs.get_run_tree(project_id, run_id),
            tasks=self._tasks.list_for_run(run_id),
            events=self._events.list_project_events(project_id),
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


class WorkerService:
    def __init__(
        self,
        runs: RunRepository,
        tasks: TaskQueue,
        artifacts: ArtifactStore,
        events: EventRepository,
    ) -> None:
        self._runs = runs
        self._tasks = tasks
        self._artifacts = artifacts
        self._events = events

    def work_once(self, worker_id: str, limit: int = 2) -> Sequence[Task]:
        leased = self._tasks.lease_ready(worker_id, timedelta(seconds=30), limit)
        completed: list[Task] = []
        for task in leased:
            agent_run = self._runs.get_agent_run(task.agent_run_id)
            artifact = self._artifacts.put_text(
                project_id=agent_run.project_id,
                run_id=agent_run.run_id,
                kind="text.result",
                name=f"{agent_run.definition.name}-{agent_run.id}.txt",
                content=f"{agent_run.definition.name} completed deterministic work.",
            )
            finished_agent = agent_run.transition(RunStatus.COMPLETED, artifact.id)
            self._runs.update_agent_run(
                finished_agent,
                [
                    Event.create(
                        agent_run.project_id,
                        EventType.RUN_COMPLETED,
                        {"agent_run_id": agent_run.id, "artifact_id": artifact.id},
                        agent_run.run_id,
                    )
                ],
            )
            self._tasks.complete(
                task.id,
                [
                    Event.create(
                        agent_run.project_id,
                        EventType.TASK_COMPLETED,
                        {"task_id": task.id, "agent_run_id": agent_run.id},
                        agent_run.run_id,
                    )
                ],
            )
            self._complete_parent_if_ready(agent_run.project_id, agent_run.run_id)
            completed.append(task)
        return completed

    def _complete_parent_if_ready(self, project_id: str, run_id: str) -> None:
        agent_runs = self._runs.get_run_tree(project_id, run_id)
        child_runs = [agent_run for agent_run in agent_runs if agent_run.parent_agent_run_id is not None]
        if not child_runs or any(agent_run.status != RunStatus.COMPLETED for agent_run in child_runs):
            return

        roots = [agent_run for agent_run in agent_runs if agent_run.parent_agent_run_id is None]
        if len(roots) != 1 or roots[0].status == RunStatus.COMPLETED:
            return

        artifact = self._artifacts.put_text(
            project_id=project_id,
            run_id=run_id,
            kind="text.final",
            name=f"run-{run_id}-final.txt",
            content="All child agent runs completed.",
        )
        parent = roots[0].transition(RunStatus.COMPLETED, artifact.id)
        self._runs.update_agent_run(
            parent,
            [
                Event.create(
                    project_id,
                    EventType.RUN_COMPLETED,
                    {"agent_run_id": parent.id, "artifact_id": artifact.id},
                    run_id,
                )
            ],
        )
        run = self._runs.get_run(project_id, run_id).transition(RunStatus.COMPLETED)
        self._runs.update_run(
            run,
            [Event.create(project_id, EventType.RUN_COMPLETED, {"run_id": run_id}, run_id)],
        )
