"""Deterministic runtime adapter used to exercise the platform spine."""

from __future__ import annotations

from rorven.application.ports import RunRepository
from rorven.domain import (
    AgentDefinitionRef,
    AgentRun,
    Event,
    EventType,
    ModelProfile,
    Project,
    Run,
    RunStatus,
    Task,
)


class LocalDeterministicRuntime:
    """A real adapter that creates platform-owned durable run records."""

    def __init__(self, runs: RunRepository) -> None:
        self._runs = runs

    def start_parent_run(self, project: Project, command: str) -> Run:
        run = Run.create(project_id=project.id, command=command)
        parent = AgentRun.create(
            run_id=run.id,
            project_id=project.id,
            definition=AgentDefinitionRef(
                name="orchestrator",
                version="0001",
                model_profile=ModelProfile.REASONING,
            ),
        )
        events = [
            Event.create(project.id, EventType.RUN_CREATED, {"run_id": run.id}, run.id),
            Event.create(project.id, EventType.RUN_QUEUED, {"agent_run_id": parent.id}, run.id),
        ]
        self._runs.add_run(run, parent, events)
        return run

    def plan_child_runs(self, run: Run, parent_agent_run: AgentRun) -> list[AgentRun]:
        reviewer = AgentRun.create(
            run_id=run.id,
            project_id=run.project_id,
            parent_agent_run_id=parent_agent_run.id,
            definition=AgentDefinitionRef(
                name="reviewer",
                version="0001",
                model_profile=ModelProfile.BALANCED,
            ),
        )
        implementer = AgentRun.create(
            run_id=run.id,
            project_id=run.project_id,
            parent_agent_run_id=parent_agent_run.id,
            definition=AgentDefinitionRef(
                name="implementer",
                version="0001",
                model_profile=ModelProfile.REASONING,
            ),
        )
        tasks = [Task.create(reviewer.id), Task.create(implementer.id)]
        waiting_parent = parent_agent_run.transition(RunStatus.WAITING)
        events = [
            Event.create(run.project_id, EventType.RUN_QUEUED, {"agent_run_id": reviewer.id}, run.id),
            Event.create(run.project_id, EventType.RUN_QUEUED, {"agent_run_id": implementer.id}, run.id),
        ]
        self._runs.add_child_runs(waiting_parent, [reviewer, implementer], tasks, events)
        return [reviewer, implementer]
