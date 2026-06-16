"""Runtime composition for local development processes."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from rorven.adapters.persistence import LocalFilePlatformStore
from rorven.adapters.runtime.local import LocalDeterministicRuntime
from rorven.application.services import ProjectService, WorkerService


@dataclass(frozen=True, slots=True)
class LocalServices:
    data_dir: Path
    store: LocalFilePlatformStore
    projects: ProjectService
    worker: WorkerService


def create_local_services(data_dir: Path | None = None) -> LocalServices:
    root = data_dir or _default_data_dir()
    store = LocalFilePlatformStore(root)
    runtime = LocalDeterministicRuntime(store)
    return LocalServices(
        data_dir=root,
        store=store,
        projects=ProjectService(runs=store, events=store, tasks=store, runtime=runtime),
        worker=WorkerService(runs=store, tasks=store, artifacts=store, events=store),
    )


def _default_data_dir() -> Path:
    configured = os.environ.get("RORVEN_DATA_DIR")
    if configured:
        return Path(configured).resolve()
    return (Path(__file__).resolve().parents[2] / ".rorven").resolve()
