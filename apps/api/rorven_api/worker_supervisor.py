"""Local API-managed worker loop for development and single-process use."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import os
from threading import Event, Thread
from time import monotonic
from typing import Any

from rorven.application.services import WorkerService


EMBEDDED_WORKER_ENV = "RORVEN_API_EMBEDDED_WORKER"
EMBEDDED_WORKER_POLL_ENV = "RORVEN_API_EMBEDDED_WORKER_POLL_SECONDS"


@dataclass(frozen=True, slots=True)
class WorkerSupervisorStatus:
    enabled: bool
    running: bool
    worker_id: str
    poll_interval_seconds: float
    completed_tasks: int
    loop_count: int
    last_started_at: str | None
    last_error: str | None


class WorkerSupervisor:
    def __init__(
        self,
        worker: WorkerService,
        *,
        enabled: bool,
        worker_id: str = "api-local-worker",
        poll_interval_seconds: float = 2.0,
        limit: int = 2,
    ) -> None:
        self._worker = worker
        self._enabled = enabled
        self._worker_id = worker_id
        self._poll_interval_seconds = poll_interval_seconds
        self._limit = limit
        self._stop = Event()
        self._thread: Thread | None = None
        self._completed_tasks = 0
        self._loop_count = 0
        self._last_started_at: str | None = None
        self._last_error: str | None = None

    def start(self) -> None:
        if not self._enabled or self._thread is not None:
            return
        self._last_started_at = datetime.now(UTC).isoformat()
        self._thread = Thread(
            target=self._run,
            name="rorven-api-local-worker",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout_seconds: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_seconds)

    def status(self) -> WorkerSupervisorStatus:
        return WorkerSupervisorStatus(
            enabled=self._enabled,
            running=self._thread is not None and self._thread.is_alive(),
            worker_id=self._worker_id,
            poll_interval_seconds=self._poll_interval_seconds,
            completed_tasks=self._completed_tasks,
            loop_count=self._loop_count,
            last_started_at=self._last_started_at,
            last_error=self._last_error,
        )

    def status_dict(self) -> dict[str, Any]:
        status = self.status()
        return {
            "enabled": status.enabled,
            "running": status.running,
            "worker_id": status.worker_id,
            "poll_interval_seconds": status.poll_interval_seconds,
            "completed_tasks": status.completed_tasks,
            "loop_count": status.loop_count,
            "last_started_at": status.last_started_at,
            "last_error": status.last_error,
        }

    def _run(self) -> None:
        while not self._stop.is_set():
            started = monotonic()
            try:
                completed = self._worker.work_once(
                    worker_id=self._worker_id,
                    limit=self._limit,
                )
                self._completed_tasks += len(completed)
                self._last_error = None
            except Exception as exc:
                self._last_error = str(exc)
            finally:
                self._loop_count += 1
            elapsed = monotonic() - started
            delay = max(0.05, self._poll_interval_seconds - elapsed)
            self._stop.wait(delay)


def create_worker_supervisor(worker: WorkerService) -> WorkerSupervisor:
    enabled = os.environ.get(EMBEDDED_WORKER_ENV, "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    poll_interval = _float_env(EMBEDDED_WORKER_POLL_ENV, 2.0)
    return WorkerSupervisor(
        worker,
        enabled=enabled,
        poll_interval_seconds=poll_interval,
    )


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return max(0.05, float(raw))
    except ValueError:
        return default
