"""Application services for the first durable execution slice."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Sequence

from rorven.application.modeling import ModelMessage, ModelRequest
from rorven.application.ports import (
    AgentRuntime,
    ApprovalRepository,
    ArtifactStore,
    ConversationRepository,
    EventRepository,
    ProjectDefaultsRepository,
    RunRepository,
    RootDashboardRepository,
    TaskQueue,
    ModelGateway,
    ToolBroker,
    WorkspaceProvisioner,
)
from rorven.application.tools import ToolExecutionResult, ToolRequest
from rorven.application.worker_service import WorkerService
from rorven.domain import (
    AgentRun,
    Approval,
    ApprovalStatus,
    ArtifactMetadata,
    ConversationEntry,
    ConversationRole,
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
    agent_runs: Sequence[AgentRun]
    tasks: Sequence[Task]
    artifacts: Sequence[ArtifactMetadata]
    artifact_contents: dict[str, str]
    approvals: Sequence[Approval]
    conversation_entries: Sequence[ConversationEntry]


@dataclass(frozen=True, slots=True)
class RunState:
    run: Run
    agent_runs: Sequence[AgentRun]
    tasks: Sequence[Task]
    events: Sequence[Event]
    artifacts: Sequence[ArtifactMetadata]
    artifact_contents: dict[str, str]
    approvals: Sequence[Approval]
    conversation_entries: Sequence[ConversationEntry]


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


MAX_ROOT_HISTORY_MESSAGES = 12


class ProjectService:
    def __init__(
        self,
        runs: RunRepository,
        events: EventRepository,
        tasks: TaskQueue,
        runtime: AgentRuntime,
        artifacts: ArtifactStore,
        approvals: ApprovalRepository,
        conversations: ConversationRepository,
    ) -> None:
        self._runs = runs
        self._events = events
        self._tasks = tasks
        self._runtime = runtime
        self._artifacts = artifacts
        self._approvals = approvals
        self._conversations = conversations

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
        runs = self._runs.list_runs(project_id)
        agent_runs: list[AgentRun] = []
        tasks: list[Task] = []
        artifacts: list[ArtifactMetadata] = []
        approvals: list[Approval] = []
        for run in runs:
            agent_runs.extend(self._runs.get_run_tree(project_id, run.id))
            tasks.extend(self._tasks.list_for_run(run.id))
            run_artifacts = list(self._artifacts.list_artifacts_for_run(run.id))
            artifacts.extend(run_artifacts)
            approvals.extend(self._approvals.list_approvals_for_run(run.id))
        return ProjectState(
            project=self._runs.get_project(project_id),
            runs=runs,
            agent_runs=agent_runs,
            tasks=tasks,
            artifacts=artifacts,
            artifact_contents={artifact.id: self._artifacts.get_text(artifact.id) for artifact in artifacts},
            approvals=approvals,
            conversation_entries=self._conversations.list_conversation_for_project(project_id),
        )

    def submit_task(self, project_id: str, command: str) -> RunState:
        project = self._runs.get_project(project_id)
        run = self._runtime.start_parent_run(project, command)
        parent = self._root_agent_run(project.id, run.id)
        task = Task.create(parent.id)
        self._tasks.enqueue(
            [task],
            [
                Event.create(
                    project.id,
                    EventType.TASK_QUEUED,
                    {"task_id": task.id, "agent_run_id": parent.id},
                    run.id,
                )
            ],
        )
        self._conversations.append_conversation_entries(
            [
                ConversationEntry.create(
                    project_id=project.id,
                    run_id=run.id,
                    agent_run_id=parent.id,
                    role=ConversationRole.USER,
                    title="You",
                    body=command,
                )
            ]
        )
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
            approvals=self._approvals.list_approvals_for_run(run_id),
            conversation_entries=self._conversations.list_conversation_for_run(run_id),
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


def _tool_request_without_content(request: ToolRequest) -> dict[str, object]:
    sanitized = dict(request.input)
    if "content" in sanitized:
        value = sanitized.pop("content")
        if isinstance(value, str):
            sanitized["content_bytes"] = len(value.encode("utf-8"))
        else:
            sanitized["content_present"] = True
    return {"name": request.name, "input": sanitized}


def _approval_applied_summary(approval: Approval, result: ToolExecutionResult) -> str:
    path = result.metadata.get("path")
    if isinstance(path, str) and path.strip():
        return f"Applied {approval.action} to {path}."
    return f"Applied {approval.action}."


class ApprovalService:
    def __init__(
        self,
        runs: RunRepository,
        approvals: ApprovalRepository,
        artifacts: ArtifactStore,
        tool_broker: ToolBroker,
        conversations: ConversationRepository,
        worker: WorkerService | None = None,
    ) -> None:
        self._runs = runs
        self._approvals = approvals
        self._artifacts = artifacts
        self._tool_broker = tool_broker
        self._conversations = conversations
        self._worker = worker

    def list_for_run(self, project_id: str, run_id: str) -> Sequence[Approval]:
        self._runs.get_run(project_id, run_id)
        return self._approvals.list_approvals_for_run(run_id)

    def approve(self, project_id: str, run_id: str, approval_id: str) -> Approval:
        approval = self._scoped_approval(project_id, run_id, approval_id)
        if approval.status == ApprovalStatus.APPLIED:
            return approval
        if approval.status == ApprovalStatus.REJECTED:
            raise ValueError("rejected approvals cannot be applied")
        if approval.status == ApprovalStatus.FAILED:
            raise ValueError("failed approvals require a new proposal")

        try:
            request = self._apply_request_from_proposal(approval)
            agent_run = self._runs.get_agent_run(approval.agent_run_id)
            project = self._runs.get_project(approval.project_id)
            result = self._tool_broker.execute(project, agent_run, request)
            result_artifact = self._put_apply_artifact(approval, request, result, error=None)
            applied = approval.apply(result_artifact.id)
            self._approvals.update_approval(
                applied,
                [
                    Event.create(
                        approval.project_id,
                        EventType.APPROVAL_APPLIED,
                        {
                            "approval_id": approval.id,
                            "artifact_id": approval.artifact_id,
                            "result_artifact_id": result_artifact.id,
                        },
                        approval.run_id,
                    )
                ],
            )
            self._conversations.append_conversation_entries(
                [
                    ConversationEntry.create(
                        project_id=approval.project_id,
                        run_id=approval.run_id,
                        agent_run_id=approval.agent_run_id,
                        role=ConversationRole.EVENT,
                        title="Approval applied",
                        body=_approval_applied_summary(applied, result),
                        artifact_id=result_artifact.id,
                    )
                ]
            )
            if self._worker is not None:
                self._worker.complete_waiting_agent_after_approval(
                    applied,
                    summary=_approval_applied_summary(applied, result),
                    artifact_id=result_artifact.id,
                )
            return applied
        except Exception as exc:
            failed = approval.fail(str(exc))
            self._approvals.update_approval(
                failed,
                [
                    Event.create(
                        approval.project_id,
                        EventType.APPROVAL_FAILED,
                        {"approval_id": approval.id, "reason": str(exc)},
                        approval.run_id,
                    )
                ],
            )
            raise

    def reject(self, project_id: str, run_id: str, approval_id: str) -> Approval:
        approval = self._scoped_approval(project_id, run_id, approval_id)
        if approval.status == ApprovalStatus.APPLIED:
            raise ValueError("applied approvals cannot be rejected")
        if approval.status == ApprovalStatus.REJECTED:
            return approval
        rejected = approval.reject()
        self._approvals.update_approval(
            rejected,
            [
                Event.create(
                    approval.project_id,
                    EventType.APPROVAL_REJECTED,
                    {"approval_id": approval.id, "artifact_id": approval.artifact_id},
                    approval.run_id,
                )
            ],
        )
        self._conversations.append_conversation_entries(
            [
                ConversationEntry.create(
                    project_id=approval.project_id,
                    run_id=approval.run_id,
                    agent_run_id=approval.agent_run_id,
                    role=ConversationRole.EVENT,
                    title="Approval rejected",
                    body=f"Rejected {approval.action}.",
                    artifact_id=approval.artifact_id,
                )
            ]
        )
        if self._worker is not None:
            self._worker.complete_waiting_agent_after_approval(
                rejected,
                summary=f"The proposal for {rejected.action} was rejected. No workspace change was applied.",
                artifact_id=rejected.artifact_id,
            )
        return rejected

    def _scoped_approval(self, project_id: str, run_id: str, approval_id: str) -> Approval:
        approval = self._approvals.get_approval(approval_id)
        if approval.project_id != project_id or approval.run_id != run_id:
            raise KeyError(f"approval not found in run: {approval_id}")
        return approval

    def _apply_request_from_proposal(self, approval: Approval) -> ToolRequest:
        payload = json.loads(self._artifacts.get_text(approval.artifact_id))
        request = payload.get("request")
        result = payload.get("result")
        if not isinstance(request, dict) or request.get("name") != "workspace.propose_text_file_write":
            raise ValueError("approval does not reference a text-file write proposal")
        tool_input = request.get("input")
        if not isinstance(tool_input, dict):
            raise ValueError("proposal input is invalid")
        metadata = result.get("metadata") if isinstance(result, dict) else None
        if not isinstance(metadata, dict) or metadata.get("applied") is not False:
            raise ValueError("proposal result is invalid or already applied")
        path = tool_input.get("path")
        content = tool_input.get("content")
        if not isinstance(path, str) or not isinstance(content, str):
            raise ValueError("proposal path and content are required")
        return ToolRequest(
            "workspace.apply_text_file_write",
            {
                "path": path,
                "content": content,
                "proposal_artifact_id": approval.artifact_id,
                "approval_id": approval.id,
            },
        )

    def _put_apply_artifact(
        self,
        approval: Approval,
        request: ToolRequest,
        result: ToolExecutionResult,
        error: str | None,
    ) -> ArtifactMetadata:
        content = {
            "request": _tool_request_without_content(request),
            "approval_id": approval.id,
            "proposal_artifact_id": approval.artifact_id,
            "result": None if result is None else {"content": result.content, "metadata": result.metadata},
            "error": error,
        }
        return self._artifacts.put_text(
            project_id=approval.project_id,
            run_id=approval.run_id,
            kind="tool.execution",
            name=f"approved-apply-{approval.id}.json",
            content=json.dumps(content, indent=2, sort_keys=True),
        )


class RootService:
    def __init__(
        self,
        runs: RunRepository,
        root_messages: RootDashboardRepository,
        model_gateway: ModelGateway,
        projects: ProjectService,
        project_defaults: ProjectDefaultsRepository,
        workspace_provisioner: WorkspaceProvisioner,
    ) -> None:
        self._runs = runs
        self._root_messages = root_messages
        self._model_gateway = model_gateway
        self._projects = projects
        self._project_defaults = project_defaults
        self._workspace_provisioner = workspace_provisioner

    def get_root_state(self) -> RootDashboardState:
        messages = self._filtered_root_messages()
        return RootDashboardState(messages=messages, activities=[])

    def submit_message(self, message: str) -> RootDashboardState:
        prior_messages = self._filtered_root_messages()[-MAX_ROOT_HISTORY_MESSAGES:]
        user_message = {
            "id": f"root-user-{len(self._root_messages.list_root_messages()) + 1}",
            "side": "user",
            "title": "You",
            "body": message,
            "time": _current_iso(),
        }
        self._root_messages.append_root_message(user_message)

        projects = self._project_stats()
        response = self._model_gateway.complete(
            ModelRequest(
                profile=ModelProfile.REASONING,
                session_id=f"root:{len(self._root_messages.list_root_messages())}",
                messages=(
                    ModelMessage(
                        "system",
                        _root_system_prompt(),
                    ),
                    ModelMessage("user", _build_root_context_prompt(projects, len(prior_messages))),
                    ModelMessage("system", _root_history_begin(len(prior_messages))),
                    *(
                        _root_message_to_model_message(root_message)
                        for root_message in prior_messages
                        if str(root_message.get("body", "")).strip()
                    ),
                    ModelMessage("system", _root_history_end(len(prior_messages))),
                    ModelMessage("user", _build_root_current_request_prompt(message)),
                ),
                max_output_tokens=240,
            )
        )
        instruction = _parse_root_instruction(response.content)
        body = self._execute_root_instruction(instruction)
        assistant_message = {
            "id": f"root-orchestrator-{len(self._root_messages.list_root_messages()) + 1}",
            "side": "orchestrator",
            "title": "Root orchestrator",
            "body": body,
            "time": _current_iso(),
        }
        self._root_messages.append_root_message(assistant_message)
        return RootDashboardState(messages=self._filtered_root_messages(), activities=[])

    def _execute_root_instruction(self, instruction: "_RootInstruction") -> str:
        if instruction.action in {"answer", "ask"}:
            return _normalize_root_response(instruction.content or "")
        if instruction.action != "tool_call" or instruction.tool_name != "project.create":
            return "I cannot perform that root project action yet."
        base_root = Path(self._project_defaults.get_workspace_base_root()).resolve()
        name = instruction.tool_input.get("name")
        if not isinstance(name, str) or not name.strip():
            return f"What should the project be called? I will place it under {base_root}."
        requested_root = instruction.tool_input.get("workspace_root")
        if isinstance(requested_root, str) and requested_root.strip():
            workspace_root = Path(requested_root.strip())
            if not workspace_root.is_absolute():
                workspace_root = base_root / workspace_root
            workspace_root = workspace_root.resolve()
        else:
            workspace_root = (base_root / _project_folder_name(name)).resolve()
        if not _is_inside(base_root, workspace_root):
            return (
                f"That folder is outside the configured workspace base: {base_root}. "
                "Change the workspace base in Settings first, then ask me again."
            )
        try:
            self._workspace_provisioner.ensure_directory(str(workspace_root))
            project = self._projects.create_project(name.strip(), str(base_root), str(workspace_root))
        except ValueError as exc:
            return str(exc)
        return f"Created project {project.name} at {project.workspace.workspace_root}."

    def _filtered_root_messages(self) -> list[dict[str, str]]:
        hidden_seed_bodies = {
            "I manage the local Rorven installation. Ask me to create projects, find projects, inspect runs, or summarize workspace activity.",
            "Create a new project for this repository.",
        }
        return [
            {key: value for key, value in message.items() if key != "status"}
            for message in self._root_messages.list_root_messages()
            if str(message.get("body", "")).strip() not in hidden_seed_bodies
        ]

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


def _root_system_prompt() -> str:
    return "\n".join(
        [
            "You are the root project orchestrator for Rorven.",
            "The root project helps the operator find, register, and inspect projects.",
            "Return exactly one JSON object and no prose outside it.",
            'To answer normally: {"action":"answer","content":"plain chat text"}',
            'To ask for missing information: {"action":"ask","content":"plain question"}',
            'To create a project: {"action":"tool_call","tool":{"name":"project.create","input":{"name":"Project name","workspace_root":"optional relative or absolute path"}}}',
            "Use project.create only when the user clearly asks to create, add, register, or make a project.",
            "If the user asks to create a project without a name, ask for the name.",
            "If workspace_root is omitted, Rorven will place the project under the configured workspace base.",
            "Plain chat text must not use Markdown, headings, bullets, or code fences.",
            "Each request is framed as live project inventory, prior root conversation history, and the current user request.",
            "Use the prior conversation history to resolve follow-up requests and missing details.",
        ]
    )


def _build_root_context_prompt(projects: Sequence[dict[str, object]], history_count: int) -> str:
    lines = [
        "Root project context for the current request:",
        "Live project inventory:",
    ]
    for project in projects:
        lines.append(
            f"- {project['name']} at {project['workspace_root']}: {project['runs']} runs, {project['active_runs']} active, {project['completed_runs']} completed"
        )
    if not projects:
        lines.append("- No projects currently registered.")
    lines.extend(
        [
            f"Prior root chat turns available: {history_count}",
            "The next section contains durable prior root chat turns, oldest to newest.",
        ]
    )
    return "\n".join(lines)


def _root_history_begin(history_count: int) -> str:
    if history_count == 0:
        return "Begin root conversation history. No prior root chat turns exist before the current request."
    return (
        "Begin root conversation history. The following user and assistant messages are "
        "durable prior root chat turns, ordered oldest to newest."
    )


def _root_history_end(history_count: int) -> str:
    if history_count == 0:
        return "End root conversation history. The next user message is the current request."
    return (
        "End root conversation history. The transcript above is available context for "
        f"this request and contains {history_count} prior turn(s). The next user message "
        "is the current request."
    )


def _root_message_to_model_message(message: dict[str, str]) -> ModelMessage:
    side = message.get("side")
    if side == "user":
        return ModelMessage("user", str(message.get("body", "")).strip())
    return ModelMessage("assistant", str(message.get("body", "")).strip())


def _build_root_current_request_prompt(command: str) -> str:
    lines = [
        f"Current user request: {command}",
        "Respond with the root action JSON contract from the system message.",
    ]
    return "\n".join(lines)


def _normalize_root_response(content: str) -> str:
    lines: list[str] = []
    for raw_line in content.strip().splitlines():
        line = raw_line.strip()
        if not line:
            if lines and lines[-1]:
                lines.append("")
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        line = line.replace("**", "").replace("__", "").replace("`", "")
        lines.append(line.rstrip())
    normalized = "\n".join(lines).strip()
    return normalized or "I could not produce a usable root project response."


@dataclass(frozen=True, slots=True)
class _RootInstruction:
    action: str
    content: str | None
    tool_name: str | None
    tool_input: dict[str, object]


def _parse_root_instruction(content: str) -> _RootInstruction:
    payload = _try_load_root_json(content)
    if payload is None:
        return _RootInstruction("answer", content, None, {})
    action = payload.get("action")
    if not isinstance(action, str):
        return _RootInstruction("answer", content, None, {})
    normalized_action = action.strip().lower()
    if normalized_action in {"answer", "ask"}:
        response_content = payload.get("content")
        return _RootInstruction(
            normalized_action,
            response_content if isinstance(response_content, str) else "",
            None,
            {},
        )
    if normalized_action != "tool_call":
        return _RootInstruction("answer", content, None, {})
    tool = payload.get("tool")
    if not isinstance(tool, dict):
        return _RootInstruction("answer", content, None, {})
    tool_name = tool.get("name")
    tool_input = tool.get("input")
    return _RootInstruction(
        "tool_call",
        None,
        tool_name if isinstance(tool_name, str) else None,
        dict(tool_input) if isinstance(tool_input, dict) else {},
    )


def _try_load_root_json(content: str) -> dict[str, object] | None:
    trimmed = content.strip()
    if trimmed.startswith("```"):
        lines = trimmed.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        trimmed = "\n".join(lines).strip()
    try:
        payload = json.loads(trimmed)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _project_folder_name(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._ -]+", "", value).strip().replace(" ", "-")
    return normalized or "project"


def _is_inside(base_root: Path, workspace_root: Path) -> bool:
    try:
        workspace_root.relative_to(base_root)
    except ValueError:
        return False
    return True


def _current_iso() -> str:
    return __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat()
