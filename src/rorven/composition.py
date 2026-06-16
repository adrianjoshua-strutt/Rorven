"""Runtime composition for local development processes."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from rorven.adapters.model import (
    OPENROUTER_KEY_ENV,
    OpenRouterModelGateway,
    load_model_profile_config,
)
from rorven.adapters.persistence import LocalFilePlatformStore
from rorven.adapters.runtime import LangGraphAgentRuntime
from rorven.adapters.tools import LocalWorkspaceToolBroker
from rorven.application.ports import ModelGateway
from rorven.application.services import ApprovalService, ProjectService, RootService, WorkerService
from rorven.application.tools import WorkspaceReadPolicy
from rorven.env import load_local_env


@dataclass(frozen=True, slots=True)
class LocalServices:
    data_dir: Path
    store: LocalFilePlatformStore
    projects: ProjectService
    approvals: ApprovalService
    root: RootService
    worker: WorkerService


def create_local_services(data_dir: Path | None = None) -> LocalServices:
    load_local_env()
    root = data_dir or _default_data_dir()
    store = LocalFilePlatformStore(root)
    runtime = _create_runtime_adapter(store)
    model_gateway = _create_model_gateway(store)
    tool_broker = LocalWorkspaceToolBroker()
    return LocalServices(
        data_dir=root,
        store=store,
        projects=ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=runtime,
            artifacts=store,
            approvals=store,
        ),
        approvals=ApprovalService(
            runs=store,
            approvals=store,
            artifacts=store,
            tool_broker=tool_broker,
        ),
        root=RootService(runs=store, root_messages=store, model_gateway=model_gateway),
        worker=WorkerService(
            runs=store,
            tasks=store,
            artifacts=store,
            events=store,
            model_gateway=model_gateway,
            approvals=store,
            tool_policy=WorkspaceReadPolicy(),
            tool_broker=tool_broker,
        ),
    )


def _default_data_dir() -> Path:
    configured = os.environ.get("RORVEN_DATA_DIR")
    if configured:
        resolved = Path(configured).resolve()
    else:
        resolved = (Path(__file__).resolve().parents[2] / ".rorven").resolve()
    print(f"[rorven] using data directory: {resolved}", flush=True)
    return resolved


def _create_model_gateway(store: LocalFilePlatformStore) -> ModelGateway:
    gateway_mode = os.environ.get("RORVEN_MODEL_GATEWAY", "auto").strip().lower()
    api_key = os.environ.get(OPENROUTER_KEY_ENV)
    profiles = load_model_profile_config(profile_overrides=store.get_model_profile_ids())
    if gateway_mode not in {"auto", "openrouter"}:
        raise RuntimeError(
            "Set RORVEN_MODEL_GATEWAY to 'auto' or 'openrouter'."
        )
    if not api_key:
        raise RuntimeError(f"{OPENROUTER_KEY_ENV} is required to start the model gateway")
    if gateway_mode in {"auto", "openrouter"} and api_key:
        return OpenRouterModelGateway(api_key=api_key, profiles=profiles)
    raise RuntimeError(
        f"RORVEN_MODEL_GATEWAY={gateway_mode!r} requires {OPENROUTER_KEY_ENV} to be configured"
    )


def _create_runtime_adapter(store: LocalFilePlatformStore) -> LangGraphAgentRuntime:
    runtime_mode = os.environ.get("RORVEN_RUNTIME_ADAPTER", "langgraph").strip().lower()
    if runtime_mode in {"langgraph", "auto"}:
        return LangGraphAgentRuntime(store)
    raise RuntimeError(
        f"RORVEN_RUNTIME_ADAPTER={runtime_mode!r} must be 'langgraph'"
    )
