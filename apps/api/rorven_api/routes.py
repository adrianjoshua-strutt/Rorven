from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from rorven.composition import LocalServices
from rorven_api.schemas import CreateProjectRequest, RootMessageRequest, SubmitRunRequest, WorkOnceRequest
from rorven_api.serializers import (
    project_state_to_api,
    project_to_api,
    root_state_to_api,
    run_state_to_api,
    task_to_api,
)
from rorven_api.settings import read_settings


def register_routes(app: FastAPI, services: LocalServices) -> None:
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ready", "data_dir": str(services.data_dir)}

    @app.get("/projects")
    def list_projects() -> dict[str, Any]:
        projects = list(services.projects.list_projects())
        print(f"[rorven-api] returning {len(projects)} projects from {services.data_dir}/state.json", flush=True)
        return {"projects": [project_to_api(project) for project in projects], "data_dir": str(services.data_dir)}

    @app.get("/settings")
    def get_settings() -> dict[str, Any]:
        return {"settings": read_settings(services.data_dir)}

    @app.get("/root")
    def get_root() -> dict[str, Any]:
        return {"root": root_state_to_api(services.root.get_root_state())}

    @app.post("/root/messages")
    def submit_root_message(request: RootMessageRequest) -> dict[str, Any]:
        return {"root": root_state_to_api(services.root.submit_message(request.message))}

    @app.post("/projects", status_code=201)
    def create_project(request: CreateProjectRequest) -> dict[str, Any]:
        try:
            project = services.projects.create_project(
                request.name,
                request.allowed_root,
                request.workspace_root,
            )
            print(f"[rorven-api] created project {project.id} at {services.data_dir}", flush=True)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"project": project_to_api(project)}

    @app.get("/projects/{project_id}")
    def get_project(project_id: str) -> dict[str, Any]:
        try:
            state = services.projects.get_project_state(project_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"project": project_state_to_api(state)}

    @app.post("/projects/{project_id}/runs", status_code=202)
    def submit_run(project_id: str, request: SubmitRunRequest) -> dict[str, Any]:
        try:
            state = services.projects.submit_task(project_id, request.command)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"run": run_state_to_api(state)}

    @app.get("/projects/{project_id}/runs/{run_id}")
    def get_run(project_id: str, run_id: str) -> dict[str, Any]:
        try:
            state = services.projects.get_run_state(project_id, run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"run": run_state_to_api(state)}

    @app.post("/worker/work-once")
    def work_once(request: WorkOnceRequest) -> dict[str, Any]:
        completed = services.worker.work_once(worker_id=request.worker_id, limit=request.limit)
        return {"completed_tasks": [task_to_api(task) for task in completed]}
