"""Ports owned by the application layer."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol, Sequence

from rorven.application.modeling import ModelRequest, ModelResponse
from rorven.application.tools import ToolExecutionResult, ToolPolicyDecision, ToolRequest
from rorven.domain import AgentRun, ArtifactMetadata, Event, Project, Run, Task


class Clock(Protocol):
    def now(self) -> datetime:
        """Return the authoritative current time for application decisions."""


class RunRepository(Protocol):
    def list_projects(self) -> Sequence[Project]:
        """Return persisted projects in creation order."""

    def get_project(self, project_id: str) -> Project:
        """Return one project by ID."""

    def add_project(self, project: Project, event: Event) -> None:
        """Persist a project and its creation event atomically."""

    def list_runs(self, project_id: str) -> Sequence[Run]:
        """Return runs for one project in creation order."""

    def get_run(self, project_id: str, run_id: str) -> Run:
        """Return one run by ID within a project."""

    def add_run(self, run: Run, agent_run: AgentRun, events: Sequence[Event]) -> None:
        """Persist a parent run, initial agent run, and lifecycle events atomically."""

    def add_child_runs(
        self,
        run: Run,
        parent_agent_run: AgentRun,
        child_agent_runs: Sequence[AgentRun],
        tasks: Sequence[Task],
        events: Sequence[Event],
    ) -> None:
        """Persist child agent runs and their queued tasks before work can execute."""

    def get_run_tree(self, project_id: str, run_id: str) -> Sequence[AgentRun]:
        """Return the current persisted agent-run tree."""

    def get_agent_run(self, agent_run_id: str) -> AgentRun:
        """Return one agent run by ID."""

    def update_agent_run(self, agent_run: AgentRun, events: Sequence[Event]) -> None:
        """Persist an agent-run state transition and lifecycle events atomically."""

    def update_run(self, run: Run, events: Sequence[Event]) -> None:
        """Persist a run state transition and lifecycle events atomically."""


class EventRepository(Protocol):
    def list_project_events(self, project_id: str) -> Sequence[Event]:
        """Return events in occurrence order for UI reconstruction."""


class TaskQueue(Protocol):
    def enqueue(self, tasks: Sequence[Task], events: Sequence[Event]) -> None:
        """Persist tasks and queue events atomically."""

    def lease_ready(self, worker_id: str, lease_duration: timedelta, limit: int) -> Sequence[Task]:
        """Lease ready or expired work using the durable queue."""

    def complete(self, task_id: str, events: Sequence[Event]) -> None:
        """Mark a task complete and persist completion events atomically."""

    def fail(self, task_id: str, events: Sequence[Event]) -> None:
        """Mark a task failed and persist failure events atomically."""

    def list_for_run(self, run_id: str) -> Sequence[Task]:
        """Return tasks attached to a run tree."""


class ArtifactStore(Protocol):
    def put_text(
        self,
        project_id: str,
        run_id: str,
        kind: str,
        name: str,
        content: str,
    ) -> ArtifactMetadata:
        """Persist artifact content and return provider-neutral metadata."""

    def list_artifacts_for_run(self, run_id: str) -> Sequence[ArtifactMetadata]:
        """Return artifact metadata for a run."""

    def get_text(self, artifact_id: str) -> str:
        """Return artifact text content by ID."""


class AgentRuntime(Protocol):
    def start_parent_run(self, project: Project, command: str) -> Run:
        """Create and persist the parent run before child work exists."""


class ModelGateway(Protocol):
    def complete(self, request: ModelRequest) -> ModelResponse:
        """Return one provider-neutral model completion."""


class ToolPolicy(Protocol):
    def evaluate(
        self,
        project: Project,
        agent_run: AgentRun,
        request: ToolRequest,
    ) -> ToolPolicyDecision:
        """Evaluate whether an agent may invoke a brokered tool."""


class ToolBroker(Protocol):
    def execute(
        self,
        project: Project,
        agent_run: AgentRun,
        request: ToolRequest,
    ) -> ToolExecutionResult:
        """Execute a policy-approved brokered tool call."""


class RootDashboardRepository(Protocol):
    def list_root_messages(self) -> Sequence[dict[str, str]]:
        """Return persisted root-dashboard chat messages in chronological order."""

    def append_root_message(self, message: dict[str, str]) -> None:
        """Persist one root-dashboard message."""
