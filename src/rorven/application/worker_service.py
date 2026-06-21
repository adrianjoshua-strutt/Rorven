"""Worker execution service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import json
from typing import Sequence

from rorven.application.agent_prompts import (
    agent_system_prompt,
    agent_task_prompt,
    orchestrator_summary_prompt,
)
from rorven.application.dispatching import (
    OrchestratorDecision,
    orchestrator_dispatch_contract,
    parse_orchestrator_decision,
)
from rorven.application.modeling import ModelMessage, ModelRequest, ModelResponse
from rorven.application.ports import (
    ApprovalRepository,
    ApprovalPolicyRepository,
    ArtifactStore,
    ConversationRepository,
    EventRepository,
    ModelGateway,
    RunRepository,
    TaskQueue,
    ToolBroker,
    ToolPolicy,
)
from rorven.application.tools import (
    DenyAllToolPolicy,
    MAX_TOOL_ROUNDS,
    ToolExecutionResult,
    ToolRequest,
    parse_agent_tool_instruction,
    tool_decision_to_json,
    tool_request_to_json,
    tool_results_prompt,
)
from rorven.domain import (
    Approval,
    ApprovalStatus,
    AgentRun,
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
)


MAX_ORCHESTRATOR_HISTORY_ENTRIES = 12


@dataclass(frozen=True, slots=True)
class AgentExecutionOutcome:
    content: str
    waiting_for_approval: bool = False


class WorkerService:
    def __init__(
        self,
        runs: RunRepository,
        tasks: TaskQueue,
        artifacts: ArtifactStore,
        events: EventRepository,
        model_gateway: ModelGateway,
        approvals: ApprovalRepository,
        conversations: ConversationRepository,
        tool_policy: ToolPolicy | None = None,
        tool_broker: ToolBroker | None = None,
        approval_policy: ApprovalPolicyRepository | None = None,
    ) -> None:
        self._runs = runs
        self._tasks = tasks
        self._artifacts = artifacts
        self._events = events
        self._model_gateway = model_gateway
        self._approvals = approvals
        self._conversations = conversations
        self._tool_policy = tool_policy or DenyAllToolPolicy()
        self._tool_broker = tool_broker
        self._approval_policy = approval_policy

    def work_once(self, worker_id: str, limit: int = 2) -> Sequence[Task]:
        leased = self._tasks.lease_ready(worker_id, timedelta(seconds=30), limit)
        completed: list[Task] = []
        for task in leased:
            agent_run = self._runs.get_agent_run(task.agent_run_id)
            try:
                if agent_run.parent_agent_run_id is None:
                    self._dispatch_or_answer_root(task, agent_run)
                    completed.append(task)
                    continue
                else:
                    outcome = self._run_agent(agent_run)
            except Exception as exc:
                self._fail_agent_task(task, agent_run, exc)
                continue

            if outcome.waiting_for_approval:
                self._pause_agent_for_approval(task, agent_run, outcome.content)
                completed.append(task)
                continue

            artifact = self._put_agent_result(agent_run, outcome.content)
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
            if agent_run.parent_agent_run_id is None:
                self._complete_root_run(agent_run.project_id, agent_run.run_id, finished_agent)
            else:
                self._complete_parent_if_ready(agent_run.project_id, agent_run.run_id)
            if task not in completed:
                completed.append(task)
        return completed

    def _run_agent(self, agent_run: AgentRun) -> AgentExecutionOutcome:
        run = self._runs.get_run(agent_run.project_id, agent_run.run_id)
        project = self._runs.get_project(agent_run.project_id)
        conversation_history = self._project_orchestrator_entries(agent_run.project_id)
        system_message = ModelMessage("system", agent_system_prompt(agent_run.definition.name))
        task_message = ModelMessage(
            "user",
            agent_task_prompt(
                project,
                run,
                agent_run,
                self._assignment(agent_run),
                conversation_history,
            ),
        )
        messages: tuple[ModelMessage, ...] = (system_message, task_message)
        for tool_round in range(MAX_TOOL_ROUNDS + 1):
            response = self._model_gateway.complete(
                ModelRequest(
                    profile=agent_run.definition.model_profile,
                    session_id=f"{agent_run.run_id}:{agent_run.id}:tool-round-{tool_round}",
                    messages=messages,
                )
            )
            instruction = parse_agent_tool_instruction(response.content)
            if not instruction.requests_tools:
                content = _format_model_response(response, instruction.final_content or response.content)
                self._append_conversation(
                    agent_run,
                    ConversationRole.ASSISTANT,
                    agent_run.definition.name,
                    content,
                )
                return AgentExecutionOutcome(content)
            if tool_round >= MAX_TOOL_ROUNDS:
                raise ValueError(f"agent exceeded {MAX_TOOL_ROUNDS} tool rounds")
            tool_results = self._execute_tool_calls(agent_run, instruction.tool_requests)
            pending_approval = _first_pending_approval(tool_results)
            if pending_approval:
                content = (
                    "Waiting for approval before applying the proposed workspace change. "
                    f"Approval id: {pending_approval}."
                )
                self._append_conversation(
                    agent_run,
                    ConversationRole.EVENT,
                    "Waiting for approval",
                    content,
                )
                return AgentExecutionOutcome(content, waiting_for_approval=True)
            messages = (
                *messages,
                ModelMessage("assistant", response.content),
                ModelMessage(
                    "user",
                    tool_results_prompt(
                        tool_results,
                        remaining_tool_rounds=MAX_TOOL_ROUNDS - tool_round - 1,
                    ),
                ),
            )
        raise RuntimeError("unreachable agent tool loop exit")

    def _execute_tool_calls(
        self,
        agent_run: AgentRun,
        requests: Sequence[ToolRequest],
    ) -> list[dict[str, object]]:
        if self._tool_broker is None:
            raise RuntimeError("no tool broker configured")
        project = self._runs.get_project(agent_run.project_id)
        results: list[dict[str, object]] = []
        for request in requests:
            self._events_marker(
                agent_run,
                EventType.TOOL_REQUESTED,
                {"tool": request.name, "input": _safe_tool_input(request)},
            )
            decision = self._tool_policy.evaluate(project, agent_run, request)
            if not decision.allowed:
                artifact = self._put_tool_artifact(
                    agent_run,
                    request,
                    decision_json=tool_decision_to_json(decision),
                    result=None,
                    error=decision.reason,
                )
                self._events_marker(
                    agent_run,
                    EventType.TOOL_DENIED,
                    {"tool": request.name, "artifact_id": artifact.id, "reason": decision.reason},
                )
                results.append(
                    {
                        "tool": request.name,
                        "allowed": False,
                        "reason": decision.reason,
                        "artifact_id": artifact.id,
                    }
                )
                self._append_conversation(
                    agent_run,
                    ConversationRole.TOOL,
                    f"{request.name} denied",
                    decision.reason,
                    artifact.id,
                )
                continue
            try:
                result = self._tool_broker.execute(project, agent_run, request)
            except Exception as exc:
                artifact = self._put_tool_artifact(
                    agent_run,
                    request,
                    decision_json=tool_decision_to_json(decision),
                    result=None,
                    error=str(exc),
                )
                self._events_marker(
                    agent_run,
                    EventType.TOOL_FAILED,
                    {"tool": request.name, "artifact_id": artifact.id},
                )
                results.append(
                    {
                        "tool": request.name,
                        "allowed": True,
                        "error": str(exc),
                        "artifact_id": artifact.id,
                    }
                )
                self._append_conversation(
                    agent_run,
                    ConversationRole.TOOL,
                    f"{request.name} failed",
                    str(exc),
                    artifact.id,
                )
                continue
            artifact = self._put_tool_artifact(
                agent_run,
                request,
                decision_json=tool_decision_to_json(decision),
                result=result,
                error=None,
            )
            self._events_marker(
                agent_run,
                EventType.TOOL_COMPLETED,
                {"tool": request.name, "artifact_id": artifact.id, **result.metadata},
            )
            approval = self._create_approval_for_proposal(agent_run, request, result, artifact)
            results.append(
                {
                    "tool": request.name,
                    "allowed": True,
                    "artifact_id": artifact.id,
                    "approval_id": approval.id if approval else None,
                    "approval_status": approval.status.value if approval else None,
                    "metadata": result.metadata,
                    "content": result.content,
                }
            )
            title = f"{request.name} completed"
            if approval:
                title = f"{request.name} awaiting approval"
            self._append_conversation(
                agent_run,
                ConversationRole.TOOL,
                title,
                result.content,
                artifact.id,
            )
        return results

    def _create_approval_for_proposal(
        self,
        agent_run: AgentRun,
        request: ToolRequest,
        result: ToolExecutionResult,
        artifact: ArtifactMetadata,
    ) -> Approval | None:
        if request.name != "workspace.propose_text_file_write":
            return None
        if result.metadata.get("proposal") != "text-file-write":
            return None
        approval = Approval.create(
            project_id=agent_run.project_id,
            run_id=agent_run.run_id,
            agent_run_id=agent_run.id,
            artifact_id=artifact.id,
            action="workspace.apply_text_file_write",
        )
        self._approvals.add_approval(
            approval,
            Event.create(
                agent_run.project_id,
                EventType.APPROVAL_CREATED,
                {
                    "approval_id": approval.id,
                    "artifact_id": artifact.id,
                    "action": approval.action,
                    "path": result.metadata.get("path"),
                },
                agent_run.run_id,
            ),
        )
        mode = (
            self._approval_policy.get_text_file_write_approval_mode()
            if self._approval_policy is not None
            else "ask_each_time"
        )
        if mode == "reject_text_file_writes":
            rejected = approval.reject()
            self._approvals.update_approval(
                rejected,
                [
                    Event.create(
                        agent_run.project_id,
                        EventType.APPROVAL_REJECTED,
                        {"approval_id": approval.id, "artifact_id": approval.artifact_id},
                        agent_run.run_id,
                    )
                ],
            )
            self._append_conversation(
                agent_run,
                ConversationRole.EVENT,
                "Approval rejected by policy",
                "Rejected workspace.apply_text_file_write by the current approval policy.",
                artifact.id,
            )
            return rejected
        if mode == "auto_apply_text_file_writes":
            return self._auto_apply_approval(agent_run, request, approval)
        return approval

    def _auto_apply_approval(
        self,
        agent_run: AgentRun,
        proposal_request: ToolRequest,
        approval: Approval,
    ) -> Approval:
        if self._tool_broker is None:
            return approval
        project = self._runs.get_project(agent_run.project_id)
        path = proposal_request.input.get("path")
        content = proposal_request.input.get("content")
        if not isinstance(path, str) or not isinstance(content, str):
            return approval
        apply_request = ToolRequest(
            "workspace.apply_text_file_write",
            {
                "path": path,
                "content": content,
                "proposal_artifact_id": approval.artifact_id,
                "approval_id": approval.id,
            },
        )
        result = self._tool_broker.execute(project, agent_run, apply_request)
        result_artifact = self._put_apply_artifact(approval, apply_request, result, error=None)
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
                        "mode": "auto_apply_text_file_writes",
                    },
                    approval.run_id,
                )
            ],
        )
        self._append_conversation(
            agent_run,
            ConversationRole.EVENT,
            "Approval auto-applied",
            f"Auto-applied {approval.action} for {path}.",
            result_artifact.id,
        )
        return applied

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

    def _pause_agent_for_approval(self, task: Task, agent_run: AgentRun, content: str) -> None:
        waiting_agent = agent_run.transition(RunStatus.WAITING)
        self._runs.update_agent_run(
            waiting_agent,
            [
                Event.create(
                    agent_run.project_id,
                    EventType.RUN_WAITING,
                    {"agent_run_id": agent_run.id, "reason": "approval"},
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
                    {"task_id": task.id, "agent_run_id": agent_run.id, "reason": "approval"},
                    agent_run.run_id,
                )
            ],
        )

    def complete_waiting_agent_after_approval(
        self,
        approval: Approval,
        *,
        summary: str,
        artifact_id: str | None,
    ) -> None:
        agent_run = self._runs.get_agent_run(approval.agent_run_id)
        if agent_run.status == RunStatus.COMPLETED:
            self._complete_parent_if_ready(approval.project_id, approval.run_id)
            return
        if agent_run.status == RunStatus.FAILED:
            return
        result_artifact = self._put_agent_result(agent_run, summary)
        finished_agent = agent_run.transition(RunStatus.COMPLETED, result_artifact.id)
        events = [
            Event.create(
                approval.project_id,
                EventType.RUN_COMPLETED,
                {
                    "agent_run_id": agent_run.id,
                    "artifact_id": result_artifact.id,
                    "approval_id": approval.id,
                },
                approval.run_id,
            )
        ]
        self._runs.update_agent_run(finished_agent, events)
        self._append_conversation(
            finished_agent,
            ConversationRole.ASSISTANT,
            finished_agent.definition.name,
            summary,
            artifact_id or result_artifact.id,
        )
        self._complete_parent_if_ready(approval.project_id, approval.run_id)

    def _put_tool_artifact(
        self,
        agent_run: AgentRun,
        request: ToolRequest,
        decision_json: dict[str, object],
        result: ToolExecutionResult | None,
        error: str | None,
    ) -> ArtifactMetadata:
        content = {
            "request": tool_request_to_json(request),
            "decision": decision_json,
            "result": None if result is None else {"content": result.content, "metadata": result.metadata},
            "error": error,
        }
        return self._artifacts.put_text(
            project_id=agent_run.project_id,
            run_id=agent_run.run_id,
            kind="tool.execution",
            name=f"tool-{agent_run.id}.json",
            content=json.dumps(content, indent=2, sort_keys=True),
        )

    def _events_marker(self, agent_run: AgentRun, event_type: EventType, payload: dict[str, object]) -> None:
        self._runs.update_agent_run(
            agent_run,
            [Event.create(agent_run.project_id, event_type, payload, agent_run.run_id)],
        )

    def _dispatch_or_answer_root(self, task: Task, root: AgentRun) -> None:
        response = self._request_orchestrator_decision(root)
        decision = parse_orchestrator_decision(response.content)
        if decision.dispatches_children:
            self._persist_child_dispatch(task, root, decision, response)
            return

        content = _format_model_response(response, decision.answer or "")
        self._answer_root_task(task, root, content)

    def _answer_root_task(self, task: Task, root: AgentRun, content: str) -> None:
        artifact = self._put_agent_result(root, content)
        self._append_conversation(root, ConversationRole.ASSISTANT, "Project orchestrator", content, artifact.id)
        answered_root = root.transition(RunStatus.COMPLETED, artifact.id)
        self._runs.update_agent_run(
            answered_root,
            [
                Event.create(
                    root.project_id,
                    EventType.RUN_COMPLETED,
                    {"agent_run_id": root.id, "artifact_id": artifact.id},
                    root.run_id,
                )
            ],
        )
        self._tasks.complete(
            task.id,
            [
                Event.create(
                    root.project_id,
                    EventType.TASK_COMPLETED,
                    {"task_id": task.id, "agent_run_id": root.id},
                    root.run_id,
                )
            ],
        )
        self._complete_root_run(root.project_id, root.run_id, answered_root)

    def _request_orchestrator_decision(self, root: AgentRun) -> ModelResponse:
        run = self._runs.get_run(root.project_id, root.run_id)
        project = self._runs.get_project(root.project_id)
        conversation_history = self._project_orchestrator_entries(root.project_id, exclude_run_id=run.id)
        work_log = self._project_work_log_entries(root.project_id, exclude_run_id=run.id)
        request = ModelRequest(
            profile=root.definition.model_profile,
            session_id=f"{root.run_id}:{root.id}:dispatch",
            messages=(
                ModelMessage("system", orchestrator_dispatch_contract()),
                ModelMessage("user", _orchestrator_project_context(project, run, len(conversation_history))),
                ModelMessage("system", _orchestrator_history_begin(len(conversation_history))),
                *(
                    ModelMessage(_model_role_for_entry(entry), entry.body.strip())
                    for entry in conversation_history
                    if entry.body.strip()
                ),
                ModelMessage("system", _orchestrator_history_end(len(conversation_history))),
                ModelMessage("system", _orchestrator_work_log_context(work_log)),
                ModelMessage("user", run.command),
            ),
            max_output_tokens=700,
        )
        return self._model_gateway.complete(request)

    def _project_orchestrator_entries(
        self,
        project_id: str,
        *,
        exclude_run_id: str | None = None,
    ) -> list[ConversationEntry]:
        entries = [
            entry
            for entry in self._conversations.list_conversation_for_project(project_id)
            if _is_project_orchestrator_entry(entry)
            and (exclude_run_id is None or entry.run_id != exclude_run_id)
        ]
        return entries[-MAX_ORCHESTRATOR_HISTORY_ENTRIES:]

    def _project_work_log_entries(
        self,
        project_id: str,
        *,
        exclude_run_id: str | None = None,
    ) -> list[ConversationEntry]:
        entries = [
            entry
            for entry in self._conversations.list_conversation_for_project(project_id)
            if not _is_project_orchestrator_entry(entry)
            and (exclude_run_id is None or entry.run_id != exclude_run_id)
            and entry.role in {ConversationRole.ASSISTANT, ConversationRole.EVENT, ConversationRole.TOOL}
            and entry.body.strip()
        ]
        return entries[-10:]

    def _persist_child_dispatch(
        self,
        task: Task,
        root: AgentRun,
        decision: OrchestratorDecision,
        response: ModelResponse,
    ) -> None:
        decision_artifact = self._artifacts.put_text(
            project_id=root.project_id,
            run_id=root.run_id,
            kind="text.orchestrator-dispatch",
            name=f"dispatch-{root.id}.json",
            content=_format_model_response(response, decision.raw_content),
        )
        self._append_conversation(
            root,
            ConversationRole.ASSISTANT,
            "Project orchestrator",
            _dispatch_summary(decision),
            decision_artifact.id,
        )
        children: list[AgentRun] = []
        child_tasks: list[Task] = []
        events: list[Event] = [
            Event.create(
                root.project_id,
                EventType.AGENT_DISPATCHED,
                {"agent_run_id": root.id, "artifact_id": decision_artifact.id},
                root.run_id,
            ),
            Event.create(
                root.project_id,
                EventType.RUN_WAITING,
                {"run_id": root.run_id, "agent_run_id": root.id},
                root.run_id,
            ),
        ]
        for dispatch in decision.child_agents:
            assignment = self._artifacts.put_text(
                project_id=root.project_id,
                run_id=root.run_id,
                kind="text.agent-assignment",
                name=f"assign-{dispatch.definition.name}.txt",
                content=dispatch.task,
            )
            child = AgentRun.create(
                run_id=root.run_id,
                project_id=root.project_id,
                definition=dispatch.definition,
                parent_agent_run_id=root.id,
                input_artifact_id=assignment.id,
            )
            child_task = Task.create(child.id)
            children.append(child)
            child_tasks.append(child_task)
            self._append_conversation(
                child,
                ConversationRole.USER,
                "Assignment",
                dispatch.task,
                assignment.id,
            )
            events.append(
                Event.create(
                    root.project_id,
                    EventType.TASK_QUEUED,
                    {"task_id": child_task.id, "agent_run_id": child.id},
                    root.run_id,
                )
            )

        waiting_run = self._runs.get_run(root.project_id, root.run_id).transition(RunStatus.WAITING)
        self._runs.add_child_runs(
            waiting_run,
            root.transition(RunStatus.WAITING),
            children,
            child_tasks,
            events,
        )
        self._tasks.complete(
            task.id,
            [
                Event.create(
                    root.project_id,
                    EventType.TASK_COMPLETED,
                    {"task_id": task.id, "agent_run_id": root.id},
                    root.run_id,
                )
            ],
        )

    def _assignment(self, agent_run: AgentRun) -> str | None:
        if not agent_run.input_artifact_id:
            return None
        return self._artifacts.get_text(agent_run.input_artifact_id)

    def _put_agent_result(self, agent_run: AgentRun, content: str) -> ArtifactMetadata:
        return self._artifacts.put_text(
            project_id=agent_run.project_id,
            run_id=agent_run.run_id,
            kind="text.agent-result",
            name=f"{agent_run.definition.name}-{agent_run.id}.txt",
            content=content,
        )

    def _fail_agent_task(self, task: Task, agent_run: AgentRun, exc: Exception) -> None:
        artifact = self._artifacts.put_text(
            project_id=agent_run.project_id,
            run_id=agent_run.run_id,
            kind="text.error",
            name=f"{agent_run.definition.name}-{agent_run.id}-error.txt",
            content=f"Model-backed worker failed: {exc}",
        )
        self._append_conversation(
            agent_run,
            ConversationRole.EVENT,
            "Worker failed",
            f"Model-backed worker failed: {exc}",
            artifact.id,
        )
        failed_agent = agent_run.transition(RunStatus.FAILED, artifact.id)
        self._runs.update_agent_run(
            failed_agent,
            [
                Event.create(
                    agent_run.project_id,
                    EventType.RUN_FAILED,
                    {"agent_run_id": agent_run.id, "artifact_id": artifact.id},
                    agent_run.run_id,
                )
            ],
        )
        self._tasks.fail(
            task.id,
            [
                Event.create(
                    agent_run.project_id,
                    EventType.RUN_FAILED,
                    {"task_id": task.id, "agent_run_id": agent_run.id},
                    agent_run.run_id,
                )
            ],
        )
        if agent_run.parent_agent_run_id is None:
            self._fail_run(agent_run.project_id, agent_run.run_id, artifact.id, agent_run.id)
        else:
            self._fail_parent_after_child_failure(agent_run, artifact.id)

    def _fail_parent_after_child_failure(self, child: AgentRun, artifact_id: str) -> None:
        roots = [
            agent_run
            for agent_run in self._runs.get_run_tree(child.project_id, child.run_id)
            if agent_run.parent_agent_run_id is None
        ]
        if len(roots) != 1 or roots[0].status in {RunStatus.COMPLETED, RunStatus.FAILED}:
            self._fail_run(child.project_id, child.run_id, artifact_id, child.id)
            return

        parent_error = self._artifacts.put_text(
            project_id=child.project_id,
            run_id=child.run_id,
            kind="text.error",
            name=f"run-{child.run_id}-failed.txt",
            content=f"Child agent {child.definition.name} failed. See artifact {artifact_id}.",
        )
        failed_parent = roots[0].transition(RunStatus.FAILED, parent_error.id)
        self._runs.update_agent_run(
            failed_parent,
            [
                Event.create(
                    child.project_id,
                    EventType.RUN_FAILED,
                    {"agent_run_id": failed_parent.id, "artifact_id": parent_error.id},
                    child.run_id,
                )
            ],
        )
        self._fail_run(child.project_id, child.run_id, parent_error.id, failed_parent.id)

    def _fail_run(self, project_id: str, run_id: str, artifact_id: str, agent_run_id: str) -> None:
        run = self._runs.get_run(project_id, run_id).transition(RunStatus.FAILED)
        self._runs.update_run(
            run,
            [
                Event.create(
                    project_id,
                    EventType.RUN_FAILED,
                    {"run_id": run_id, "agent_run_id": agent_run_id, "artifact_id": artifact_id},
                    run_id,
                )
            ],
        )

    def _complete_root_run(self, project_id: str, run_id: str, root: AgentRun) -> None:
        run = self._runs.get_run(project_id, run_id).transition(RunStatus.COMPLETED)
        self._runs.update_run(
            run,
            [
                Event.create(
                    project_id,
                    EventType.RUN_COMPLETED,
                    {"run_id": run_id, "agent_run_id": root.id},
                    run_id,
                )
            ],
        )

    def _complete_parent_if_ready(self, project_id: str, run_id: str) -> None:
        agent_runs = self._runs.get_run_tree(project_id, run_id)
        child_runs = [agent_run for agent_run in agent_runs if agent_run.parent_agent_run_id is not None]
        if not child_runs or any(agent_run.status != RunStatus.COMPLETED for agent_run in child_runs):
            return

        roots = [agent_run for agent_run in agent_runs if agent_run.parent_agent_run_id is None]
        if len(roots) != 1 or roots[0].status == RunStatus.COMPLETED:
            return

        final_content = self._summarize_run(project_id, run_id, roots[0], child_runs)
        artifact = self._artifacts.put_text(
            project_id=project_id,
            run_id=run_id,
            kind="text.final",
            name=f"run-{run_id}-final.txt",
            content=final_content,
        )
        self._append_conversation(
            roots[0],
            ConversationRole.ASSISTANT,
            "Project orchestrator",
            final_content,
            artifact.id,
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

    def _summarize_run(
        self,
        project_id: str,
        run_id: str,
        parent: AgentRun,
        child_runs: Sequence[AgentRun],
    ) -> str:
        run = self._runs.get_run(project_id, run_id)
        project = self._runs.get_project(project_id)
        child_outputs = []
        for child in child_runs:
            if child.result_artifact_id:
                child_outputs.append(
                    f"Subagent message from {child.definition.name}:\n"
                    f"{self._artifacts.get_text(child.result_artifact_id)}"
                )
        conversation_history = self._project_orchestrator_entries(project_id)
        request = ModelRequest(
            profile=ModelProfile.REASONING,
            session_id=f"{run_id}:{parent.id}:summary",
            messages=(
                ModelMessage("system", agent_system_prompt("orchestrator")),
                ModelMessage(
                    "user",
                    orchestrator_summary_prompt(project, run, child_outputs, conversation_history),
                ),
            ),
            max_output_tokens=700,
        )
        response = self._model_gateway.complete(request)
        return _format_model_response(response, response.content)

    def _append_conversation(
        self,
        agent_run: AgentRun,
        role: ConversationRole,
        title: str,
        body: str,
        artifact_id: str | None = None,
    ) -> None:
        self._conversations.append_conversation_entries(
            [
                ConversationEntry.create(
                    project_id=agent_run.project_id,
                    run_id=agent_run.run_id,
                    agent_run_id=agent_run.id,
                    role=role,
                    title=title,
                    body=body,
                    artifact_id=artifact_id,
                )
            ]
        )

def _format_model_response(_response: ModelResponse, content: str) -> str:
    return content.strip()


def _safe_tool_input(request: ToolRequest) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in request.input.items():
        if key == "content":
            if isinstance(value, str):
                result["content_bytes"] = len(value.encode("utf-8"))
            else:
                result["content_present"] = True
            continue
        result[key] = value
    return result


def _tool_request_without_content(request: ToolRequest) -> dict[str, object]:
    sanitized = dict(request.input)
    if "content" in sanitized:
        value = sanitized.pop("content")
        if isinstance(value, str):
            sanitized["content_bytes"] = len(value.encode("utf-8"))
        else:
            sanitized["content_present"] = True
    return {"name": request.name, "input": sanitized}


def _first_pending_approval(tool_results: Sequence[dict[str, object]]) -> str | None:
    for result in tool_results:
        approval_id = result.get("approval_id")
        if result.get("approval_status") == ApprovalStatus.PENDING.value and isinstance(approval_id, str):
            return approval_id
    return None


def _is_project_orchestrator_entry(entry: ConversationEntry) -> bool:
    if entry.role == ConversationRole.USER:
        return entry.title == "You"
    if entry.role == ConversationRole.ASSISTANT:
        return entry.title in {"Project orchestrator", "orchestrator"}
    return False


def _conversation_speaker(entry: ConversationEntry) -> str:
    if entry.role == ConversationRole.USER:
        return "User"
    return "Project orchestrator"


def _model_role_for_entry(entry: ConversationEntry) -> str:
    if entry.role == ConversationRole.USER:
        return "user"
    return "assistant"


def _orchestrator_project_context(project: Project, run: Run, history_count: int) -> str:
    return "\n".join(
        [
            "Project context for the current request:",
            f"- Project: {project.name}",
            f"- Workspace root: {project.workspace.workspace_root}",
            f"- Allowed root: {project.workspace.allowed_root}",
            f"- Run id: {run.id}",
            f"- Prior project chat turns available: {history_count}",
            "",
            "The next section contains durable prior chat turns for this project, oldest to newest.",
            "Use those turns as the conversation history for resolving follow-ups and deciding whether to answer or dispatch.",
        ]
    )


def _orchestrator_history_begin(history_count: int) -> str:
    if history_count == 0:
        return (
            "Begin project conversation history. No prior user/orchestrator chat turns exist "
            "before the current request."
        )
    return (
        "Begin project conversation history. The following user and assistant messages are "
        "the durable prior chat turns for this project, ordered oldest to newest."
    )


def _orchestrator_history_end(history_count: int) -> str:
    if history_count == 0:
        return (
            "End project conversation history. The next user message is the current request."
        )
    return (
        "End project conversation history. The transcript above is available context for "
        f"this request and contains {history_count} prior turn(s). The next user message "
        "is the current request. If the user asks about previous messages, answer from "
        "the transcript above. Resolve references like 'that', 'the file', 'the folder', "
        "or 'what I told you' from the transcript before choosing answer or dispatch."
    )


def _orchestrator_work_log_context(entries: Sequence[ConversationEntry]) -> str:
    if not entries:
        return "Project work-log facts: no prior subagent, tool, or approval facts are available."
    lines = [
        "Project work-log facts from prior subagent/tool/approval entries, oldest to newest.",
        "Use these facts to answer follow-up questions about files, approvals, and completed work.",
    ]
    for entry in entries:
        body = " ".join(entry.body.strip().split())
        if len(body) > 420:
            body = f"{body[:417].rstrip()}..."
        lines.append(f"- {entry.title}: {body}")
    return "\n".join(lines)


def _dispatch_summary(decision: OrchestratorDecision) -> str:
    names = ", ".join(dispatch.definition.name for dispatch in decision.child_agents)
    count = len(decision.child_agents)
    if count == 1:
        return f"I spawned 1 subagent: {names}."
    return f"I spawned {count} subagents: {names}."
