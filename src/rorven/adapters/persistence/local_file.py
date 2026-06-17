"""Local file-backed adapter for early durable development.

This adapter is not the planned production database adapter. It exists behind the
same application ports so API, worker, UI, and contract tests can exercise real
durable state while the PostgreSQL adapter is built.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
import json
from pathlib import Path
from threading import RLock
from typing import Any, Sequence

from rorven.adapters.model import DEFAULT_MODEL_IDS
from rorven.application.ports import (
    ApprovalRepository,
    ArtifactStore,
    ConversationRepository,
    EventRepository,
    ProjectDefaultsRepository,
    RunRepository,
    TaskQueue,
)
from rorven.domain import (
    AgentDefinitionRef,
    AgentRun,
    Approval,
    ApprovalStatus,
    ArtifactMetadata,
    ConversationEntry,
    ConversationRole,
    Event,
    EventType,
    ModelProfile,
    Project,
    Run,
    RunStatus,
    Task,
    TaskStatus,
    WorkspaceBinding,
    new_id,
    utc_now,
)


MODEL_PROFILE_NAMES = ("utility", "balanced", "reasoning", "frontier")


class LocalFilePlatformStore(
    RunRepository,
    EventRepository,
    TaskQueue,
    ArtifactStore,
    ApprovalRepository,
    ConversationRepository,
    ProjectDefaultsRepository,
):
    def __init__(self, root: Path, default_workspace_base_root: str | None = None) -> None:
        self._root = root
        self._default_workspace_base_root = default_workspace_base_root or str(Path.cwd().resolve())
        self._state_path = root / "state.json"
        self._artifact_root = root / "artifacts"
        self._lock = RLock()
        self._root.mkdir(parents=True, exist_ok=True)
        self._artifact_root.mkdir(parents=True, exist_ok=True)
        if not self._state_path.exists():
            self._write_state(self._empty_state())
        else:
            self._migrate_state()

    def list_projects(self) -> Sequence[Project]:
        with self._lock:
            state = self._read_state()
            projects = [self._project_from_json(item) for item in state["projects"].values()]
            return sorted(projects, key=lambda item: item.created_at, reverse=True)

    def get_project(self, project_id: str) -> Project:
        with self._lock:
            state = self._read_state()
            try:
                return self._project_from_json(state["projects"][project_id])
            except KeyError as exc:
                raise KeyError(f"project not found: {project_id}") from exc

    def add_project(self, project: Project, event: Event) -> None:
        with self._lock:
            state = self._read_state()
            state["projects"][project.id] = self._project_to_json(project)
            state["events"][event.id] = self._event_to_json(event)
            self._write_state(state)

    def list_runs(self, project_id: str) -> Sequence[Run]:
        with self._lock:
            state = self._read_state()
            return [
                self._run_from_json(item)
                for item in state["runs"].values()
                if item["project_id"] == project_id
            ]

    def get_run(self, project_id: str, run_id: str) -> Run:
        with self._lock:
            state = self._read_state()
            try:
                item = state["runs"][run_id]
            except KeyError as exc:
                raise KeyError(f"run not found: {run_id}") from exc
            if item["project_id"] != project_id:
                raise KeyError(f"run not found in project: {run_id}")
            return self._run_from_json(item)

    def add_run(self, run: Run, agent_run: AgentRun, events: Sequence[Event]) -> None:
        with self._lock:
            state = self._read_state()
            state["runs"][run.id] = self._run_to_json(run.transition(RunStatus.QUEUED))
            state["agent_runs"][agent_run.id] = self._agent_run_to_json(
                agent_run.transition(RunStatus.QUEUED)
            )
            for event in events:
                state["events"][event.id] = self._event_to_json(event)
            self._write_state(state)

    def add_child_runs(
        self,
        run: Run,
        parent_agent_run: AgentRun,
        child_agent_runs: Sequence[AgentRun],
        tasks: Sequence[Task],
        events: Sequence[Event],
    ) -> None:
        with self._lock:
            state = self._read_state()
            state["runs"][run.id] = self._run_to_json(run)
            state["agent_runs"][parent_agent_run.id] = self._agent_run_to_json(parent_agent_run)
            for child in child_agent_runs:
                state["agent_runs"][child.id] = self._agent_run_to_json(child.transition(RunStatus.QUEUED))
            for task in tasks:
                state["tasks"][task.id] = self._task_to_json(task)
            for event in events:
                state["events"][event.id] = self._event_to_json(event)
            self._write_state(state)

    def get_run_tree(self, project_id: str, run_id: str) -> Sequence[AgentRun]:
        with self._lock:
            state = self._read_state()
            agent_runs = [
                self._agent_run_from_json(item)
                for item in state["agent_runs"].values()
                if item["project_id"] == project_id and item["run_id"] == run_id
            ]
            return sorted(agent_runs, key=lambda item: item.created_at)

    def get_agent_run(self, agent_run_id: str) -> AgentRun:
        with self._lock:
            state = self._read_state()
            try:
                return self._agent_run_from_json(state["agent_runs"][agent_run_id])
            except KeyError as exc:
                raise KeyError(f"agent run not found: {agent_run_id}") from exc

    def update_agent_run(self, agent_run: AgentRun, events: Sequence[Event]) -> None:
        with self._lock:
            state = self._read_state()
            state["agent_runs"][agent_run.id] = self._agent_run_to_json(agent_run)
            for event in events:
                state["events"][event.id] = self._event_to_json(event)
            self._write_state(state)

    def update_run(self, run: Run, events: Sequence[Event]) -> None:
        with self._lock:
            state = self._read_state()
            state["runs"][run.id] = self._run_to_json(run)
            for event in events:
                state["events"][event.id] = self._event_to_json(event)
            self._write_state(state)

    def list_project_events(self, project_id: str) -> Sequence[Event]:
        with self._lock:
            state = self._read_state()
            events = [
                self._event_from_json(item)
                for item in state["events"].values()
                if item["project_id"] == project_id
            ]
            return sorted(events, key=lambda item: item.occurred_at)

    def enqueue(self, tasks: Sequence[Task], events: Sequence[Event]) -> None:
        with self._lock:
            state = self._read_state()
            for task in tasks:
                state["tasks"][task.id] = self._task_to_json(task)
            for event in events:
                state["events"][event.id] = self._event_to_json(event)
            self._write_state(state)

    def lease_ready(self, worker_id: str, lease_duration: timedelta, limit: int) -> Sequence[Task]:
        with self._lock:
            state = self._read_state()
            now = utc_now()
            leased: list[Task] = []
            for item in state["tasks"].values():
                task = self._task_from_json(item)
                lease_expired = task.lease_expires_at is not None and task.lease_expires_at <= now
                if task.status == TaskStatus.READY or (
                    task.status == TaskStatus.LEASED and lease_expired
                ):
                    leased_task = Task(
                        id=task.id,
                        agent_run_id=task.agent_run_id,
                        status=TaskStatus.LEASED,
                        lease_owner=worker_id,
                        lease_expires_at=now + lease_duration,
                        created_at=task.created_at,
                    )
                    state["tasks"][task.id] = self._task_to_json(leased_task)
                    agent_run = self._agent_run_from_json(state["agent_runs"][task.agent_run_id])
                    state["agent_runs"][agent_run.id] = self._agent_run_to_json(
                        agent_run.transition(RunStatus.STARTED)
                    )
                    state["events"][new_id()] = self._event_to_json(
                        Event.create(
                            agent_run.project_id,
                            EventType.TASK_LEASED,
                            {"task_id": task.id, "worker_id": worker_id},
                            agent_run.run_id,
                        )
                    )
                    leased.append(leased_task)
                    if len(leased) >= limit:
                        break
            self._write_state(state)
            return leased

    def complete(self, task_id: str, events: Sequence[Event]) -> None:
        with self._lock:
            state = self._read_state()
            task = self._task_from_json(state["tasks"][task_id])
            state["tasks"][task_id] = self._task_to_json(
                Task(
                    id=task.id,
                    agent_run_id=task.agent_run_id,
                    status=TaskStatus.COMPLETED,
                    lease_owner=task.lease_owner,
                    lease_expires_at=task.lease_expires_at,
                    created_at=task.created_at,
                )
            )
            for event in events:
                state["events"][event.id] = self._event_to_json(event)
            self._write_state(state)

    def fail(self, task_id: str, events: Sequence[Event]) -> None:
        with self._lock:
            state = self._read_state()
            task = self._task_from_json(state["tasks"][task_id])
            state["tasks"][task_id] = self._task_to_json(
                Task(
                    id=task.id,
                    agent_run_id=task.agent_run_id,
                    status=TaskStatus.FAILED,
                    lease_owner=task.lease_owner,
                    lease_expires_at=task.lease_expires_at,
                    created_at=task.created_at,
                )
            )
            for event in events:
                state["events"][event.id] = self._event_to_json(event)
            self._write_state(state)

    def list_for_run(self, run_id: str) -> Sequence[Task]:
        with self._lock:
            state = self._read_state()
            agent_run_ids = {
                item["id"] for item in state["agent_runs"].values() if item["run_id"] == run_id
            }
            return [
                self._task_from_json(item)
                for item in state["tasks"].values()
                if item["agent_run_id"] in agent_run_ids
            ]

    def put_text(
        self,
        project_id: str,
        run_id: str,
        kind: str,
        name: str,
        content: str,
    ) -> ArtifactMetadata:
        with self._lock:
            artifact_id = new_id()
            artifact_dir = self._artifact_root / project_id / run_id
            artifact_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = artifact_dir / name
            artifact_path.write_text(content, encoding="utf-8")
            artifact = ArtifactMetadata(
                id=artifact_id,
                project_id=project_id,
                run_id=run_id,
                kind=kind,
                uri=str(artifact_path.relative_to(self._root)),
            )
            state = self._read_state()
            state["artifacts"][artifact.id] = self._artifact_to_json(artifact)
            state["events"][new_id()] = self._event_to_json(
                Event.create(
                    project_id,
                    EventType.ARTIFACT_CREATED,
                    {"artifact_id": artifact.id, "kind": kind},
                    run_id,
                )
            )
            self._write_state(state)
            return artifact

    def list_artifacts_for_run(self, run_id: str) -> Sequence[ArtifactMetadata]:
        with self._lock:
            state = self._read_state()
            artifacts = [
                self._artifact_from_json(item)
                for item in state["artifacts"].values()
                if item["run_id"] == run_id
            ]
            return sorted(artifacts, key=lambda item: item.created_at)

    def list_root_messages(self) -> Sequence[dict[str, Any]]:
        with self._lock:
            state = self._read_state()
            return list(state["root_messages"])

    def append_root_message(self, message: dict[str, Any]) -> None:
        with self._lock:
            state = self._read_state()
            state["root_messages"].append(message)
            self._write_state(state)

    def append_conversation_entries(self, entries: Sequence[ConversationEntry]) -> None:
        if not entries:
            return
        with self._lock:
            state = self._read_state()
            for entry in entries:
                state["conversation_entries"][entry.id] = self._conversation_entry_to_json(entry)
            self._write_state(state)

    def list_conversation_for_run(self, run_id: str) -> Sequence[ConversationEntry]:
        with self._lock:
            state = self._read_state()
            entries = [
                self._conversation_entry_from_json(item)
                for item in state["conversation_entries"].values()
                if item["run_id"] == run_id
            ]
            return sorted(entries, key=lambda item: item.created_at)

    def list_conversation_for_project(self, project_id: str) -> Sequence[ConversationEntry]:
        with self._lock:
            state = self._read_state()
            entries = [
                self._conversation_entry_from_json(item)
                for item in state["conversation_entries"].values()
                if item["project_id"] == project_id
            ]
            return sorted(entries, key=lambda item: item.created_at)

    def get_model_profile_ids(self) -> dict[str, str]:
        with self._lock:
            state = self._read_state()
            settings = state.get("settings")
            if not isinstance(settings, dict):
                return {}
            profiles = settings.get("model_profiles")
            if not isinstance(profiles, dict):
                return {}
            result: dict[str, str] = {}
            for name in MODEL_PROFILE_NAMES:
                value = profiles.get(name)
                if isinstance(value, str) and value.strip() and value.strip() != "replace-me":
                    result[name] = value.strip()
            return result

    def set_model_profile_ids(self, model_ids: dict[str, str]) -> None:
        with self._lock:
            state = self._read_state()
            settings = state.setdefault("settings", {})
            if not isinstance(settings, dict):
                settings = {}
                state["settings"] = settings
            profiles = settings.setdefault("model_profiles", {})
            if not isinstance(profiles, dict):
                profiles = {}
                settings["model_profiles"] = profiles
            for name in MODEL_PROFILE_NAMES:
                if name not in model_ids:
                    continue
                value = model_ids[name].strip()
                if value:
                    profiles[name] = value
                else:
                    profiles.pop(name, None)
            self._write_state(state)

    def get_workspace_base_root(self) -> str:
        with self._lock:
            state = self._read_state()
            settings = state.get("settings")
            if not isinstance(settings, dict):
                return self._default_workspace_base_root
            project_defaults = settings.get("project_defaults")
            if not isinstance(project_defaults, dict):
                return self._default_workspace_base_root
            value = project_defaults.get("workspace_base_root")
            if isinstance(value, str) and value.strip():
                return value.strip()
            return self._default_workspace_base_root

    def set_workspace_base_root(self, workspace_base_root: str) -> None:
        if not workspace_base_root.strip():
            raise ValueError("workspace_base_root is required")
        with self._lock:
            state = self._read_state()
            settings = state.setdefault("settings", {})
            if not isinstance(settings, dict):
                settings = {}
                state["settings"] = settings
            project_defaults = settings.setdefault("project_defaults", {})
            if not isinstance(project_defaults, dict):
                project_defaults = {}
                settings["project_defaults"] = project_defaults
            project_defaults["workspace_base_root"] = str(Path(workspace_base_root).resolve())
            self._write_state(state)

    def get_text(self, artifact_id: str) -> str:
        with self._lock:
            state = self._read_state()
            try:
                artifact = self._artifact_from_json(state["artifacts"][artifact_id])
            except KeyError as exc:
                raise KeyError(f"artifact not found: {artifact_id}") from exc
            path = self._root / artifact.uri
            return path.read_text(encoding="utf-8")

    def add_approval(self, approval: Approval, event: Event) -> None:
        with self._lock:
            state = self._read_state()
            state["approvals"][approval.id] = self._approval_to_json(approval)
            state["events"][event.id] = self._event_to_json(event)
            self._write_state(state)

    def list_approvals_for_run(self, run_id: str) -> Sequence[Approval]:
        with self._lock:
            state = self._read_state()
            approvals = [
                self._approval_from_json(item)
                for item in state["approvals"].values()
                if item["run_id"] == run_id
            ]
            return sorted(approvals, key=lambda item: item.created_at)

    def get_approval(self, approval_id: str) -> Approval:
        with self._lock:
            state = self._read_state()
            try:
                return self._approval_from_json(state["approvals"][approval_id])
            except KeyError as exc:
                raise KeyError(f"approval not found: {approval_id}") from exc

    def update_approval(self, approval: Approval, events: Sequence[Event]) -> None:
        with self._lock:
            state = self._read_state()
            if approval.id not in state["approvals"]:
                raise KeyError(f"approval not found: {approval.id}")
            state["approvals"][approval.id] = self._approval_to_json(approval)
            for event in events:
                state["events"][event.id] = self._event_to_json(event)
            self._write_state(state)

    def _empty_state(self) -> dict[str, dict[str, Any]]:
        return {
            "projects": {},
            "runs": {},
            "agent_runs": {},
            "tasks": {},
            "events": {},
            "artifacts": {},
            "approvals": {},
            "conversation_entries": {},
            "root_messages": [],
            "settings": {
                "model_profiles": {},
                "project_defaults": {
                    "workspace_base_root": self._default_workspace_base_root,
                },
            },
        }

    def _migrate_state(self) -> None:
        state = self._read_state()
        changed = False
        for key, value in self._empty_state().items():
            if key not in state:
                state[key] = value
                changed = True

        settings = state.get("settings")
        if not isinstance(settings, dict):
            state["settings"] = {"model_profiles": {}}
            settings = state["settings"]
            changed = True
        profiles = settings.get("model_profiles")
        if not isinstance(profiles, dict):
            settings["model_profiles"] = {}
            profiles = settings["model_profiles"]
            changed = True
        project_defaults = settings.get("project_defaults")
        if not isinstance(project_defaults, dict):
            settings["project_defaults"] = {}
            project_defaults = settings["project_defaults"]
            changed = True
        if not isinstance(project_defaults.get("workspace_base_root"), str) or not project_defaults[
            "workspace_base_root"
        ].strip():
            project_defaults["workspace_base_root"] = self._default_workspace_base_root
            changed = True

        # Seed product defaults into persisted settings so model routing is explicit
        # and user-editable through the settings API.
        for name in MODEL_PROFILE_NAMES:
            if (
                isinstance(profiles.get(name), str)
                and profiles[name].strip()
                and profiles[name].strip() != "replace-me"
            ):
                continue
            profiles[name] = DEFAULT_MODEL_IDS[name]
            changed = True
        if changed:
            self._write_state(state)

    def _read_state(self) -> dict[str, dict[str, Any]]:
        return json.loads(self._state_path.read_text(encoding="utf-8"))

    def _write_state(self, state: dict[str, dict[str, Any]]) -> None:
        self._state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    def _project_to_json(self, project: Project) -> dict[str, Any]:
        data = asdict(project)
        data["created_at"] = project.created_at.isoformat()
        return data

    def _project_from_json(self, data: dict[str, Any]) -> Project:
        return Project(
            id=data["id"],
            name=data["name"],
            workspace=WorkspaceBinding(**data["workspace"]),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    def _run_to_json(self, run: Run) -> dict[str, Any]:
        data = asdict(run)
        data["status"] = run.status.value
        data["created_at"] = run.created_at.isoformat()
        data["completed_at"] = run.completed_at.isoformat() if run.completed_at else None
        return data

    def _run_from_json(self, data: dict[str, Any]) -> Run:
        return Run(
            id=data["id"],
            project_id=data["project_id"],
            status=RunStatus(data["status"]),
            command=data["command"],
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None,
        )

    def _agent_run_to_json(self, agent_run: AgentRun) -> dict[str, Any]:
        data = asdict(agent_run)
        data["definition"]["model_profile"] = agent_run.definition.model_profile.value
        data["status"] = agent_run.status.value
        data["created_at"] = agent_run.created_at.isoformat()
        return data

    def _agent_run_from_json(self, data: dict[str, Any]) -> AgentRun:
        definition = data["definition"]
        return AgentRun(
            id=data["id"],
            run_id=data["run_id"],
            project_id=data["project_id"],
            parent_agent_run_id=data["parent_agent_run_id"],
            definition=AgentDefinitionRef(
                name=definition["name"],
                version=definition["version"],
                model_profile=ModelProfile(definition["model_profile"]),
            ),
            status=RunStatus(data["status"]),
            input_artifact_id=data.get("input_artifact_id"),
            result_artifact_id=data.get("result_artifact_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    def _task_to_json(self, task: Task) -> dict[str, Any]:
        data = asdict(task)
        data["status"] = task.status.value
        data["lease_expires_at"] = task.lease_expires_at.isoformat() if task.lease_expires_at else None
        data["created_at"] = task.created_at.isoformat()
        return data

    def _task_from_json(self, data: dict[str, Any]) -> Task:
        return Task(
            id=data["id"],
            agent_run_id=data["agent_run_id"],
            status=TaskStatus(data["status"]),
            lease_owner=data.get("lease_owner"),
            lease_expires_at=datetime.fromisoformat(data["lease_expires_at"])
            if data.get("lease_expires_at")
            else None,
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    def _event_to_json(self, event: Event) -> dict[str, Any]:
        data = asdict(event)
        data["type"] = event.type.value
        data["occurred_at"] = event.occurred_at.isoformat()
        return data

    def _event_from_json(self, data: dict[str, Any]) -> Event:
        return Event(
            id=data["id"],
            project_id=data["project_id"],
            run_id=data.get("run_id"),
            type=EventType(data["type"]),
            payload=data["payload"],
            occurred_at=datetime.fromisoformat(data["occurred_at"]),
        )

    def _artifact_to_json(self, artifact: ArtifactMetadata) -> dict[str, Any]:
        data = asdict(artifact)
        data["created_at"] = artifact.created_at.isoformat()
        return data

    def _artifact_from_json(self, data: dict[str, Any]) -> ArtifactMetadata:
        return ArtifactMetadata(
            id=data["id"],
            project_id=data["project_id"],
            run_id=data["run_id"],
            kind=data["kind"],
            uri=data["uri"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    def _approval_to_json(self, approval: Approval) -> dict[str, Any]:
        data = asdict(approval)
        data["status"] = approval.status.value
        data["created_at"] = approval.created_at.isoformat()
        data["decided_at"] = approval.decided_at.isoformat() if approval.decided_at else None
        return data

    def _approval_from_json(self, data: dict[str, Any]) -> Approval:
        return Approval(
            id=data["id"],
            project_id=data["project_id"],
            run_id=data["run_id"],
            agent_run_id=data["agent_run_id"],
            artifact_id=data["artifact_id"],
            action=data["action"],
            status=ApprovalStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            decided_at=datetime.fromisoformat(data["decided_at"])
            if data.get("decided_at")
            else None,
            result_artifact_id=data.get("result_artifact_id"),
            failure_reason=data.get("failure_reason"),
        )

    def _conversation_entry_to_json(self, entry: ConversationEntry) -> dict[str, Any]:
        data = asdict(entry)
        data["role"] = entry.role.value
        data["created_at"] = entry.created_at.isoformat()
        return data

    def _conversation_entry_from_json(self, data: dict[str, Any]) -> ConversationEntry:
        return ConversationEntry(
            id=data["id"],
            project_id=data["project_id"],
            run_id=data["run_id"],
            agent_run_id=data.get("agent_run_id"),
            role=ConversationRole(data["role"]),
            title=data["title"],
            body=data.get("body", ""),
            artifact_id=data.get("artifact_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
        )
