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


class LangGraphAgentRuntime:
    """Runtime adapter that persists project orchestrator runs through LangGraph."""

    def __init__(self, runs: RunRepository) -> None:
        self._runs = runs
        self._start_parent_graph = self._build_start_parent_graph()

    def start_parent_run(self, project: Project, command: str) -> Run:
        state = self._start_parent_graph.invoke({"project": project, "command": command})
        run = state["run"]
        return run

    def _build_start_parent_graph(self):
        graph = StateGraph(_StartParentState)
        graph.add_node("persist_parent", self._persist_parent_run)
        graph.add_edge(START, "persist_parent")
        graph.add_edge("persist_parent", END)
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
