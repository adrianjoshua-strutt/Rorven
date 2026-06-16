from __future__ import annotations

from pathlib import Path
import unittest
from uuid import uuid4

from rorven.adapters.persistence import LocalFilePlatformStore
from rorven.adapters.runtime.local import LocalDeterministicRuntime
from rorven.application.services import ProjectService, WorkerService


class LocalFileStoreTests(unittest.TestCase):
    def test_project_run_and_worker_state_survive_store_reopen(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-{uuid4()}"
        root.mkdir(parents=True, exist_ok=True)
        store = LocalFilePlatformStore(root)
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LocalDeterministicRuntime(store),
        )
        worker = WorkerService(runs=store, tasks=store, artifacts=store, events=store)

        project = projects.create_project("Example", "D:/workspaces", "D:/workspaces/example")
        run_state = projects.submit_task(project.id, "Build backend and frontend")
        worker.work_once("test-worker")

        reopened = LocalFilePlatformStore(root)
        reopened_projects = ProjectService(
            runs=reopened,
            events=reopened,
            tasks=reopened,
            runtime=LocalDeterministicRuntime(reopened),
        )
        reopened_state = reopened_projects.get_run_state(project.id, run_state.run.id)

        self.assertEqual("completed", reopened_state.run.status.value)
        self.assertEqual(3, len(reopened_state.agent_runs))
        self.assertEqual({"completed"}, {item.status.value for item in reopened_state.tasks})
        self.assertTrue((root / "state.json").exists())


if __name__ == "__main__":
    unittest.main()
