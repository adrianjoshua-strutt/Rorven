"""FastAPI control plane for the durable walking skeleton."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rorven.application.services import ProjectState, RunState
from rorven.composition import create_local_services
from rorven.domain import AgentRun, Event, Project, Run, Task
from rorven_api.settings import read_settings


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1)
    allowed_root: str = Field(min_length=1)
    workspace_root: str = Field(min_length=1)


class SubmitRunRequest(BaseModel):
    command: str = Field(min_length=1)


class WorkOnceRequest(BaseModel):
    worker_id: str = Field(default="local-worker", min_length=1)
    limit: int = Field(default=2, ge=1, le=10)


def create_app() -> FastAPI:
    services = create_local_services()
    app = FastAPI(title="Rorven API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ready"}

    @app.get("/projects")
    def list_projects() -> dict[str, list[dict[str, Any]]]:
        return {"projects": [_project_to_api(project) for project in services.projects.list_projects()]}

    @app.get("/settings")
    def get_settings() -> dict[str, Any]:
        return {"settings": read_settings(services.data_dir)}

    @app.post("/projects", status_code=201)
    def create_project(request: CreateProjectRequest) -> dict[str, Any]:
        try:
            project = services.projects.create_project(
                request.name,
                request.allowed_root,
                request.workspace_root,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"project": _project_to_api(project)}

    @app.get("/projects/{project_id}")
    def get_project(project_id: str) -> dict[str, Any]:
        try:
            state = services.projects.get_project_state(project_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"project": _project_state_to_api(state)}

    @app.post("/projects/{project_id}/runs", status_code=202)
    def submit_run(project_id: str, request: SubmitRunRequest) -> dict[str, Any]:
        try:
            state = services.projects.submit_task(project_id, request.command)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"run": _run_state_to_api(state)}

    @app.get("/projects/{project_id}/runs/{run_id}")
    def get_run(project_id: str, run_id: str) -> dict[str, Any]:
        try:
            state = services.projects.get_run_state(project_id, run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"run": _run_state_to_api(state)}

    @app.post("/worker/work-once")
    def work_once(request: WorkOnceRequest) -> dict[str, Any]:
        completed = services.worker.work_once(worker_id=request.worker_id, limit=request.limit)
        return {"completed_tasks": [_task_to_api(task) for task in completed]}

    return app


app = create_app()


def _project_state_to_api(state: ProjectState) -> dict[str, Any]:
    data = _project_to_api(state.project)
    data["runs"] = [_run_to_api(run) for run in state.runs]
    return data


def _run_state_to_api(state: RunState) -> dict[str, Any]:
    return {
        **_run_to_api(state.run),
        "agent_runs": [_agent_run_to_api(agent_run) for agent_run in state.agent_runs],
        "tasks": [_task_to_api(task) for task in state.tasks],
        "events": [_event_to_api(event) for event in state.events if event.run_id == state.run.id],
    }


def _project_to_api(project: Project) -> dict[str, Any]:
    return {
        "id": project.id,
        "name": project.name,
        "workspace": {
            "allowed_root": project.workspace.allowed_root,
            "workspace_root": project.workspace.workspace_root,
        },
        "created_at": _dt(project.created_at),
    }


def _run_to_api(run: Run) -> dict[str, Any]:
    return {
        "id": run.id,
        "project_id": run.project_id,
        "status": run.status.value,
        "command": run.command,
        "created_at": _dt(run.created_at),
        "completed_at": _dt(run.completed_at) if run.completed_at else None,
    }


def _agent_run_to_api(agent_run: AgentRun) -> dict[str, Any]:
    return {
        "id": agent_run.id,
        "run_id": agent_run.run_id,
        "project_id": agent_run.project_id,
        "parent_agent_run_id": agent_run.parent_agent_run_id,
        "definition": {
            "name": agent_run.definition.name,
            "version": agent_run.definition.version,
            "model_profile": agent_run.definition.model_profile.value,
        },
        "status": agent_run.status.value,
        "input_artifact_id": agent_run.input_artifact_id,
        "result_artifact_id": agent_run.result_artifact_id,
        "created_at": _dt(agent_run.created_at),
    }


def _task_to_api(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "agent_run_id": task.agent_run_id,
        "status": task.status.value,
        "lease_owner": task.lease_owner,
        "lease_expires_at": _dt(task.lease_expires_at) if task.lease_expires_at else None,
        "created_at": _dt(task.created_at),
    }


def _event_to_api(event: Event) -> dict[str, Any]:
    return {
        "id": event.id,
        "project_id": event.project_id,
        "run_id": event.run_id,
        "type": event.type.value,
        "payload": event.payload,
        "occurred_at": _dt(event.occurred_at),
    }


def _dt(value: datetime) -> str:
    return value.isoformat()
