"""Worker execution service."""

from __future__ import annotations

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
    ArtifactStore,
    EventRepository,
    ModelGateway,
    RunRepository,
    TaskQueue,
    ToolBroker,
    ToolPolicy,
)
from rorven.application.tools import (
    DenyAllToolPolicy,
    ToolExecutionResult,
    ToolRequest,
    parse_agent_tool_instruction,
    tool_decision_to_json,
    tool_request_to_json,
    tool_results_prompt,
)
from rorven.domain import Approval, AgentRun, ArtifactMetadata, Event, EventType, ModelProfile, RunStatus, Task


class WorkerService:
    def __init__(
        self,
        runs: RunRepository,
        tasks: TaskQueue,
        artifacts: ArtifactStore,
        events: EventRepository,
        model_gateway: ModelGateway,
        approvals: ApprovalRepository,
        tool_policy: ToolPolicy | None = None,
        tool_broker: ToolBroker | None = None,
    ) -> None:
        self._runs = runs
        self._tasks = tasks
        self._artifacts = artifacts
        self._events = events
        self._model_gateway = model_gateway
        self._approvals = approvals
        self._tool_policy = tool_policy or DenyAllToolPolicy()
        self._tool_broker = tool_broker

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
                    content = self._run_agent(agent_run)
            except Exception as exc:
                self._fail_agent_task(task, agent_run, exc)
                continue

            artifact = self._put_agent_result(agent_run, content)
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

    def _run_agent(self, agent_run: AgentRun) -> str:
        run = self._runs.get_run(agent_run.project_id, agent_run.run_id)
        project = self._runs.get_project(agent_run.project_id)
        system_message = ModelMessage("system", agent_system_prompt(agent_run.definition.name))
        task_message = ModelMessage("user", agent_task_prompt(project, run, agent_run, self._assignment(agent_run)))
        request = ModelRequest(
            profile=agent_run.definition.model_profile,
            session_id=f"{agent_run.run_id}:{agent_run.id}",
            messages=(system_message, task_message),
        )
        response = self._model_gateway.complete(request)
        instruction = parse_agent_tool_instruction(response.content)
        if not instruction.requests_tools:
            return _format_model_response(response, instruction.final_content or response.content)

        tool_results = self._execute_tool_calls(agent_run, instruction.tool_requests)
        final_response = self._model_gateway.complete(
            ModelRequest(
                profile=agent_run.definition.model_profile,
                session_id=f"{agent_run.run_id}:{agent_run.id}:after-tools",
                messages=(
                    system_message,
                    task_message,
                    ModelMessage("assistant", response.content),
                    ModelMessage("user", tool_results_prompt(tool_results)),
                ),
            )
        )
        final_instruction = parse_agent_tool_instruction(final_response.content)
        if final_instruction.requests_tools:
            raise ValueError("agent requested more than one round of tools")
        return _format_model_response(final_response, final_instruction.final_content or final_response.content)

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
                    "metadata": result.metadata,
                    "content": result.content,
                }
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
        return approval

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
        artifact = self._put_agent_result(root, content)
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
        request = ModelRequest(
            profile=root.definition.model_profile,
            session_id=f"{root.run_id}:{root.id}:dispatch",
            messages=(
                ModelMessage("system", orchestrator_dispatch_contract()),
                ModelMessage(
                    "user",
                    "\n".join(
                        [
                            f"Project: {project.name}",
                            f"Workspace root: {project.workspace.workspace_root}",
                            f"Allowed root: {project.workspace.allowed_root}",
                            f"Run id: {run.id}",
                            "",
                            "User request:",
                            run.command,
                        ]
                    ),
                ),
            ),
            max_output_tokens=700,
        )
        return self._model_gateway.complete(request)

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
                    f"## {child.definition.name}\n"
                    f"{self._artifacts.get_text(child.result_artifact_id)}"
                )
        request = ModelRequest(
            profile=ModelProfile.REASONING,
            session_id=f"{run_id}:{parent.id}:summary",
            messages=(
                ModelMessage("system", agent_system_prompt("orchestrator")),
                ModelMessage("user", orchestrator_summary_prompt(project, run, child_outputs)),
            ),
            max_output_tokens=700,
        )
        response = self._model_gateway.complete(request)
        return _format_model_response(response, response.content)

def _format_usage(usage: dict[str, object]) -> str:
    total = usage.get("total_tokens")
    if isinstance(total, int):
        return f" / tokens: {total}"
    return ""


def _format_model_response(response: ModelResponse, content: str) -> str:
    model_line = f"Model: {response.provider}"
    if response.model:
        model_line = f"{model_line}/{response.model}"
    return f"{model_line}{_format_usage(response.usage)}\n\n{content.strip()}"


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
