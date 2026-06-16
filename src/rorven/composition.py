"""Runtime composition for local development processes."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from rorven.adapters.model import (
    OPENROUTER_KEY_ENV,
    LocalModelGateway,
    OpenRouterModelGateway,
    load_model_profile_config,
)
from rorven.adapters.persistence import LocalFilePlatformStore
from rorven.adapters.runtime.local import LocalDeterministicRuntime
from rorven.application.ports import ModelGateway
from rorven.application.services import ProjectService, WorkerService
from rorven.env import load_local_env


@dataclass(frozen=True, slots=True)
class LocalServices:
    data_dir: Path
    store: LocalFilePlatformStore
    projects: ProjectService
    worker: WorkerService


def create_local_services(data_dir: Path | None = None) -> LocalServices:
    load_local_env()
    root = data_dir or _default_data_dir()
    store = LocalFilePlatformStore(root)
    runtime = LocalDeterministicRuntime(store)
    model_gateway = _create_model_gateway()
    return LocalServices(
        data_dir=root,
        store=store,
        projects=ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=runtime,
            artifacts=store,
        ),
        worker=WorkerService(
            runs=store,
            tasks=store,
            artifacts=store,
            events=store,
            model_gateway=model_gateway,
        ),
    )


def _default_data_dir() -> Path:
    configured = os.environ.get("RORVEN_DATA_DIR")
    if configured:
        return Path(configured).resolve()
    return (Path(__file__).resolve().parents[2] / ".rorven").resolve()


def _create_model_gateway() -> ModelGateway:
    gateway_mode = os.environ.get("RORVEN_MODEL_GATEWAY", "auto").strip().lower()
    api_key = os.environ.get(OPENROUTER_KEY_ENV)
    profiles = load_model_profile_config()
    if gateway_mode == "local" or (gateway_mode == "auto" and not api_key):
        return LocalModelGateway()
    if gateway_mode in {"auto", "openrouter"} and api_key:
        return OpenRouterModelGateway(api_key=api_key, profiles=profiles)
    raise RuntimeError(
        f"RORVEN_MODEL_GATEWAY={gateway_mode!r} requires {OPENROUTER_KEY_ENV} to be configured"
    )
