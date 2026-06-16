"""Ports owned by the application layer."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol, Sequence

from rorven.domain import AgentRun, ArtifactMetadata, Event, Project, Run, Task


class Clock(Protocol):
    def now(self) -> datetime:
        """Return the authoritative current time for application decisions."""


class RunRepository(Protocol):
    def add_project(self, project: Project, event: Event) -> None:
        """Persist a project and its creation event atomically."""

    def add_run(self, run: Run, agent_run: AgentRun, events: Sequence[Event]) -> None:
        """Persist a parent run, initial agent run, and lifecycle events atomically."""

    def add_child_runs(
        self,
        parent_agent_run: AgentRun,
        child_agent_runs: Sequence[AgentRun],
        tasks: Sequence[Task],
        events: Sequence[Event],
    ) -> None:
        """Persist child agent runs and their queued tasks before work can execute."""

    def get_run_tree(self, project_id: str, run_id: str) -> Sequence[AgentRun]:
        """Return the current persisted agent-run tree."""


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


class AgentRuntime(Protocol):
    def start_parent_run(self, project: Project, command: str) -> Run:
        """Create and persist the parent run before child work exists."""

    def plan_child_runs(self, run: Run, parent_agent_run: AgentRun) -> Sequence[AgentRun]:
        """Create durable child agent-run records for independent worker execution."""
