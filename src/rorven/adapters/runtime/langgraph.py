"""LangGraph-backed agent runtime adapter."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from rorven.application.ports import RunRepository
from rorven.domain import (
    AgentDefinitionRef,
    AgentRun,
    Event,
    EventType,
    ModelProfile,
    Project,
    Run,
)


class _StartParentState(TypedDict, total=False):
    project: Project
    command: str
    run: Run
    parent_agent_run: AgentRun


class _PlanChildrenState(TypedDict, total=False):
    run: Run
    parent_agent_run: AgentRun
    child_runs: list[AgentRun]


class LangGraphAgentRuntime:
    """A real runtime adapter that uses LangGraph for orchestration flow."""

    def __init__(self, runs: RunRepository) -> None:
        self._runs = runs
        self._start_parent_graph = self._build_start_parent_graph()
        self._plan_children_graph = self._build_plan_children_graph()

    def start_parent_run(self, project: Project, command: str) -> Run:
        state = self._start_parent_graph.invoke({"project": project, "command": command})
        run = state["run"]
        return run

    def plan_child_runs(self, run: Run, parent_agent_run: AgentRun) -> list[AgentRun]:
        # Real child runs are created when actual agent work is dispatched.
        # No synthetic subagents are created upfront.
        return []

    def _build_start_parent_graph(self):
        graph = StateGraph(_StartParentState)
        graph.add_node("persist_parent", self._persist_parent_run)
        graph.add_edge(START, "persist_parent")
        graph.add_edge("persist_parent", END)
        return graph.compile()

    def _build_plan_children_graph(self):
        graph = StateGraph(_PlanChildrenState)
        graph.add_node("persist_children", self._persist_child_runs)
        graph.add_edge(START, "persist_children")
        graph.add_edge("persist_children", END)
        return graph.compile()

    def _persist_parent_run(self, state: _StartParentState) -> _StartParentState:
        project = state["project"]
        command = state["command"]
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
        return {"project": project, "command": command, "run": run, "parent_agent_run": parent}

    def _persist_child_runs(self, state: _PlanChildrenState) -> _PlanChildrenState:
        run = state["run"]
        parent_agent_run = state["parent_agent_run"]
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
        return {"run": run, "parent_agent_run": waiting_parent, "child_runs": [reviewer, implementer]}