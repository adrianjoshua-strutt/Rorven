"""Current canonical domain model for the first durable execution slice."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


def new_id() -> str:
    return str(uuid4())


def require_uuid(value: str, field_name: str) -> str:
    try:
        UUID(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a UUID string") from exc
    return value


def utc_now() -> datetime:
    return datetime.now(UTC)


class ModelProfile(StrEnum):
    UTILITY = "utility"
    BALANCED = "balanced"
    REASONING = "reasoning"
    FRONTIER = "frontier"


class RunStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    LEASED = "leased"
    STARTED = "started"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class TaskStatus(StrEnum):
    READY = "ready"
    LEASED = "leased"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"
    FAILED = "failed"


class ConversationRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    EVENT = "event"


class EventType(StrEnum):
    PROJECT_CREATED = "project.created"
    RUN_CREATED = "run.created"
    RUN_QUEUED = "run.queued"
    RUN_STARTED = "run.started"
    RUN_WAITING = "run.waiting"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    TASK_QUEUED = "task.queued"
    TASK_LEASED = "task.leased"
    TASK_COMPLETED = "task.completed"
    ARTIFACT_CREATED = "artifact.created"
    AGENT_DISPATCHED = "agent.dispatched"
    TOOL_REQUESTED = "tool.requested"
    TOOL_DENIED = "tool.denied"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    APPROVAL_CREATED = "approval.created"
    APPROVAL_APPLIED = "approval.applied"
    APPROVAL_REJECTED = "approval.rejected"
    APPROVAL_FAILED = "approval.failed"


@dataclass(frozen=True, slots=True)
class WorkspaceBinding:
    allowed_root: str
    workspace_root: str

    def __post_init__(self) -> None:
        if not self.allowed_root:
            raise ValueError("allowed_root is required")
        if not self.workspace_root:
            raise ValueError("workspace_root is required")
        allowed = self.allowed_root.rstrip("/\\")
        workspace = self.workspace_root.rstrip("/\\")
        inside_allowed_root = workspace == allowed or workspace.startswith(f"{allowed}/")
        inside_allowed_root = inside_allowed_root or workspace.startswith(f"{allowed}\\")
        if not inside_allowed_root:
            raise ValueError("workspace_root must be inside allowed_root")


@dataclass(frozen=True, slots=True)
class Project:
    id: str
    name: str
    workspace: WorkspaceBinding
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_uuid(self.id, "project id")
        if not self.name.strip():
            raise ValueError("project name is required")

    @classmethod
    def create(cls, name: str, workspace: WorkspaceBinding) -> Project:
        return cls(id=new_id(), name=name, workspace=workspace)


@dataclass(frozen=True, slots=True)
class AgentDefinitionRef:
    name: str
    version: str
    model_profile: ModelProfile

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("agent definition name is required")
        if not self.version:
            raise ValueError("agent definition version is required")


@dataclass(frozen=True, slots=True)
class Run:
    id: str
    project_id: str
    status: RunStatus
    command: str
    created_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        require_uuid(self.id, "run id")
        require_uuid(self.project_id, "project id")
        if not self.command.strip():
            raise ValueError("run command is required")

    @classmethod
    def create(cls, project_id: str, command: str) -> Run:
        return cls(id=new_id(), project_id=project_id, status=RunStatus.CREATED, command=command)

    def transition(self, status: RunStatus, completed_at: datetime | None = None) -> Run:
        return Run(
            id=self.id,
            project_id=self.project_id,
            status=status,
            command=self.command,
            created_at=self.created_at,
            completed_at=completed_at,
        )


@dataclass(frozen=True, slots=True)
class AgentRun:
    id: str
    run_id: str
    project_id: str
    parent_agent_run_id: str | None
    definition: AgentDefinitionRef
    status: RunStatus
    input_artifact_id: str | None = None
    result_artifact_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_uuid(self.id, "agent run id")
        require_uuid(self.run_id, "run id")
        require_uuid(self.project_id, "project id")
        if self.parent_agent_run_id is not None:
            require_uuid(self.parent_agent_run_id, "parent agent run id")

    @classmethod
    def create(
        cls,
        run_id: str,
        project_id: str,
        definition: AgentDefinitionRef,
        parent_agent_run_id: str | None = None,
        input_artifact_id: str | None = None,
    ) -> AgentRun:
        return cls(
            id=new_id(),
            run_id=run_id,
            project_id=project_id,
            parent_agent_run_id=parent_agent_run_id,
            definition=definition,
            status=RunStatus.CREATED,
            input_artifact_id=input_artifact_id,
        )

    def transition(
        self,
        status: RunStatus,
        result_artifact_id: str | None = None,
    ) -> AgentRun:
        return AgentRun(
            id=self.id,
            run_id=self.run_id,
            project_id=self.project_id,
            parent_agent_run_id=self.parent_agent_run_id,
            definition=self.definition,
            status=status,
            input_artifact_id=self.input_artifact_id,
            result_artifact_id=result_artifact_id or self.result_artifact_id,
            created_at=self.created_at,
        )


@dataclass(frozen=True, slots=True)
class ConversationEntry:
    id: str
    project_id: str
    run_id: str
    agent_run_id: str | None
    role: ConversationRole
    title: str
    body: str
    artifact_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_uuid(self.id, "conversation entry id")
        require_uuid(self.project_id, "project id")
        require_uuid(self.run_id, "run id")
        if self.agent_run_id is not None:
            require_uuid(self.agent_run_id, "agent run id")
        if not self.title.strip():
            raise ValueError("conversation entry title is required")

    @classmethod
    def create(
        cls,
        project_id: str,
        run_id: str,
        role: ConversationRole,
        title: str,
        body: str,
        agent_run_id: str | None = None,
        artifact_id: str | None = None,
    ) -> ConversationEntry:
        return cls(
            id=new_id(),
            project_id=project_id,
            run_id=run_id,
            agent_run_id=agent_run_id,
            role=role,
            title=title,
            body=body,
            artifact_id=artifact_id,
        )


@dataclass(frozen=True, slots=True)
class Task:
    id: str
    agent_run_id: str
    status: TaskStatus
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_uuid(self.id, "task id")
        require_uuid(self.agent_run_id, "agent run id")

    @classmethod
    def create(cls, agent_run_id: str) -> Task:
        return cls(id=new_id(), agent_run_id=agent_run_id, status=TaskStatus.READY)


@dataclass(frozen=True, slots=True)
class ArtifactMetadata:
    id: str
    project_id: str
    run_id: str
    kind: str
    uri: str
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_uuid(self.id, "artifact id")
        require_uuid(self.project_id, "project id")
        require_uuid(self.run_id, "run id")
        if not self.kind:
            raise ValueError("artifact kind is required")
        if not self.uri:
            raise ValueError("artifact uri is required")


@dataclass(frozen=True, slots=True)
class Approval:
    id: str
    project_id: str
    run_id: str
    agent_run_id: str
    artifact_id: str
    action: str
    status: ApprovalStatus
    created_at: datetime = field(default_factory=utc_now)
    decided_at: datetime | None = None
    result_artifact_id: str | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        require_uuid(self.id, "approval id")
        require_uuid(self.project_id, "project id")
        require_uuid(self.run_id, "run id")
        require_uuid(self.agent_run_id, "agent run id")
        require_uuid(self.artifact_id, "artifact id")
        if self.result_artifact_id is not None:
            require_uuid(self.result_artifact_id, "result artifact id")
        if not self.action.strip():
            raise ValueError("approval action is required")

    @classmethod
    def create(
        cls,
        project_id: str,
        run_id: str,
        agent_run_id: str,
        artifact_id: str,
        action: str,
    ) -> Approval:
        return cls(
            id=new_id(),
            project_id=project_id,
            run_id=run_id,
            agent_run_id=agent_run_id,
            artifact_id=artifact_id,
            action=action,
            status=ApprovalStatus.PENDING,
        )

    def apply(self, result_artifact_id: str) -> Approval:
        return Approval(
            id=self.id,
            project_id=self.project_id,
            run_id=self.run_id,
            agent_run_id=self.agent_run_id,
            artifact_id=self.artifact_id,
            action=self.action,
            status=ApprovalStatus.APPLIED,
            created_at=self.created_at,
            decided_at=utc_now(),
            result_artifact_id=result_artifact_id,
        )

    def reject(self) -> Approval:
        return Approval(
            id=self.id,
            project_id=self.project_id,
            run_id=self.run_id,
            agent_run_id=self.agent_run_id,
            artifact_id=self.artifact_id,
            action=self.action,
            status=ApprovalStatus.REJECTED,
            created_at=self.created_at,
            decided_at=utc_now(),
            result_artifact_id=self.result_artifact_id,
        )

    def fail(self, reason: str) -> Approval:
        return Approval(
            id=self.id,
            project_id=self.project_id,
            run_id=self.run_id,
            agent_run_id=self.agent_run_id,
            artifact_id=self.artifact_id,
            action=self.action,
            status=ApprovalStatus.FAILED,
            created_at=self.created_at,
            decided_at=utc_now(),
            result_artifact_id=self.result_artifact_id,
            failure_reason=reason,
        )


@dataclass(frozen=True, slots=True)
class Event:
    id: str
    project_id: str
    run_id: str | None
    type: EventType
    payload: dict[str, Any]
    occurred_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        require_uuid(self.id, "event id")
        require_uuid(self.project_id, "project id")
        if self.run_id is not None:
            require_uuid(self.run_id, "run id")

    @classmethod
    def create(
        cls,
        project_id: str,
        event_type: EventType,
        payload: dict[str, Any],
        run_id: str | None = None,
    ) -> Event:
        return cls(
            id=new_id(),
            project_id=project_id,
            run_id=run_id,
            type=event_type,
            payload=payload,
        )
