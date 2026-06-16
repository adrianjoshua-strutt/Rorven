"""Worker execution service."""

from __future__ import annotations

from datetime import timedelta
from typing import Sequence

from rorven.application.agent_prompts import (
    agent_system_prompt,
    agent_task_prompt,
    orchestrator_summary_prompt,
)
from rorven.application.modeling import ModelMessage, ModelRequest
from rorven.application.ports import ArtifactStore, EventRepository, ModelGateway, RunRepository, TaskQueue
from rorven.domain import AgentRun, ArtifactMetadata, Event, EventType, ModelProfile, RunStatus, Task


class WorkerService:
    def __init__(
        self,
        runs: RunRepository,
        tasks: TaskQueue,
        artifacts: ArtifactStore,
        events: EventRepository,
        model_gateway: ModelGateway,
    ) -> None:
        self._runs = runs
        self._tasks = tasks
        self._artifacts = artifacts
        self._events = events
        self._model_gateway = model_gateway

    def work_once(self, worker_id: str, limit: int = 2) -> Sequence[Task]:
        leased = self._tasks.lease_ready(worker_id, timedelta(seconds=30), limit)
        completed: list[Task] = []
        for task in leased:
            agent_run = self._runs.get_agent_run(task.agent_run_id)
            try:
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
            self._complete_parent_if_ready(agent_run.project_id, agent_run.run_id)
            completed.append(task)
        return completed

    def _run_agent(self, agent_run: AgentRun) -> str:
        run = self._runs.get_run(agent_run.project_id, agent_run.run_id)
        project = self._runs.get_project(agent_run.project_id)
        request = ModelRequest(
            profile=agent_run.definition.model_profile,
            session_id=f"{agent_run.run_id}:{agent_run.id}",
            messages=(
                ModelMessage("system", agent_system_prompt(agent_run.definition.name)),
                ModelMessage("user", agent_task_prompt(project, run, agent_run)),
            ),
        )
        response = self._model_gateway.complete(request)
        model_line = f"Model: {response.provider}"
        if response.model:
            model_line = f"{model_line}/{response.model}"
        return f"{model_line}{_format_usage(response.usage)}\n\n{response.content.strip()}"

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
        model_line = f"Model: {response.provider}"
        if response.model:
            model_line = f"{model_line}/{response.model}"
        return f"{model_line}{_format_usage(response.usage)}\n\n{response.content.strip()}"

def _format_usage(usage: dict[str, object]) -> str:
    total = usage.get("total_tokens")
    if isinstance(total, int):
        return f" / tokens: {total}"
    return ""
