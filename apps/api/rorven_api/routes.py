from __future__ import annotations

from collections.abc import Callable
import os
from typing import Any

from fastapi import FastAPI, HTTPException

from rorven.adapters.model import OPENROUTER_KEY_ENV, list_openrouter_models
from rorven.composition import LocalServices
from rorven_api.schemas import (
    ApprovalPolicySettingsRequest,
    CreateProjectRequest,
    ModelProfileSettingsRequest,
    ProjectDefaultsSettingsRequest,
    RootMessageRequest,
    SubmitRunRequest,
    WorkOnceRequest,
)
from rorven_api.serializers import (
    approval_to_api,
    project_state_to_api,
    project_to_api,
    root_state_to_api,
    run_state_to_api,
    task_to_api,
)
from rorven_api.settings import read_settings


def register_routes(
    app: FastAPI,
    services: LocalServices,
    worker_status: Callable[[], dict[str, Any]] | None = None,
) -> None:
    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ready",
            "data_dir": str(services.data_dir),
            "worker": worker_status() if worker_status else None,
        }

    @app.get("/projects")
    def list_projects() -> dict[str, Any]:
        projects = list(services.projects.list_projects())
        print(f"[rorven-api] returning {len(projects)} projects from {services.data_dir}/state.json", flush=True)
        project_payloads = []
        for project in projects:
            payload = project_to_api(project)
            try:
                state = services.projects.get_project_state(project.id)
                payload.update(_project_activity_metadata(state))
            except KeyError:
                pass
            project_payloads.append(payload)
        return {"projects": project_payloads, "data_dir": str(services.data_dir)}

    @app.get("/settings")
    def get_settings() -> dict[str, Any]:
        return {"settings": read_settings(services.data_dir, worker_status=worker_status() if worker_status else None)}

    @app.post("/settings/model-profiles")
    def update_model_profiles(request: ModelProfileSettingsRequest) -> dict[str, Any]:
        updates = {
            "utility": request.utility,
            "balanced": request.balanced,
            "reasoning": request.reasoning,
            "frontier": request.frontier,
        }
        normalized = {
            name: (value.strip() if isinstance(value, str) else "")
            for name, value in updates.items()
            if value is not None
        }
        services.store.set_model_profile_ids(normalized)
        return {"settings": read_settings(services.data_dir, worker_status=worker_status() if worker_status else None)}

    @app.get("/settings/model-catalog")
    def get_model_catalog() -> dict[str, Any]:
        try:
            models = list_openrouter_models(os.environ.get(OPENROUTER_KEY_ENV))
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"models": models}

    @app.post("/settings/project-defaults")
    def update_project_defaults(request: ProjectDefaultsSettingsRequest) -> dict[str, Any]:
        try:
            services.store.set_workspace_base_root(request.workspace_base_root)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"settings": read_settings(services.data_dir, worker_status=worker_status() if worker_status else None)}

    @app.post("/settings/approval-policy")
    def update_approval_policy(request: ApprovalPolicySettingsRequest) -> dict[str, Any]:
        try:
            services.store.set_text_file_write_approval_mode(request.text_file_write)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"settings": read_settings(services.data_dir, worker_status=worker_status() if worker_status else None)}

    @app.get("/root")
    def get_root() -> dict[str, Any]:
        return {"root": root_state_to_api(services.root.get_root_state())}

    @app.post("/root/messages")
    def submit_root_message(request: RootMessageRequest) -> dict[str, Any]:
        try:
            root_state = services.root.submit_message(request.message)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Root orchestrator request failed: {exc}") from exc
        return {"root": root_state_to_api(root_state)}

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
        payload = project_state_to_api(state)
        payload.update(_project_activity_metadata(state))
        return {"project": payload}

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

    @app.get("/projects/{project_id}/runs/{run_id}/approvals")
    def list_approvals(project_id: str, run_id: str) -> dict[str, Any]:
        try:
            approvals = services.approvals.list_for_run(project_id, run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"approvals": [approval_to_api(approval) for approval in approvals]}

    @app.post("/projects/{project_id}/runs/{run_id}/approvals/{approval_id}/approve")
    def approve(project_id: str, run_id: str, approval_id: str) -> dict[str, Any]:
        try:
            approval = services.approvals.approve(project_id, run_id, approval_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"approval": approval_to_api(approval)}

    @app.post("/projects/{project_id}/runs/{run_id}/approvals/{approval_id}/reject")
    def reject(project_id: str, run_id: str, approval_id: str) -> dict[str, Any]:
        try:
            approval = services.approvals.reject(project_id, run_id, approval_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"approval": approval_to_api(approval)}

    @app.post("/worker/work-once")
    def work_once(request: WorkOnceRequest) -> dict[str, Any]:
        completed = services.worker.work_once(worker_id=request.worker_id, limit=request.limit)
        return {"completed_tasks": [task_to_api(task) for task in completed]}

    @app.get("/worker/status")
    def get_worker_status() -> dict[str, Any]:
        return {"worker": worker_status() if worker_status else None}


def _project_activity_metadata(state: Any) -> dict[str, Any]:
    entries = list(state.conversation_entries)
    user_entries = [entry for entry in entries if entry.role.value == "user" and entry.title == "You"]
    pending_approvals = [approval for approval in state.approvals if approval.status.value == "pending"]
    active_runs = [run for run in state.runs if run.status.value not in {"completed", "failed", "canceled"}]
    latest_times = [state.project.created_at]
    latest_times.extend(entry.created_at for entry in entries)
    latest_times.extend(run.created_at for run in state.runs)
    return {
        "last_activity_at": max(latest_times).isoformat(),
        "last_user_message_at": max((entry.created_at for entry in user_entries), default=None).isoformat()
        if user_entries
        else None,
        "pending_approval_count": len(pending_approvals),
        "active_run_count": len(active_runs),
    }
