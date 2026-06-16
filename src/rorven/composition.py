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
    store: LocalFilePlatformStore
    projects: ProjectService
    worker: WorkerService


def create_local_services(data_dir: Path | None = None) -> LocalServices:
    root = data_dir or Path(os.environ.get("RORVEN_DATA_DIR", ".rorven")).resolve()
    store = LocalFilePlatformStore(root)
    runtime = LocalDeterministicRuntime(store)
    return LocalServices(
        store=store,
        projects=ProjectService(runs=store, events=store, tasks=store, runtime=runtime),
        worker=WorkerService(runs=store, tasks=store, artifacts=store, events=store),
    )

