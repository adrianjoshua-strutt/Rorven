from __future__ import annotations

import json
from pathlib import Path
import unittest
from uuid import uuid4

from rorven.adapters.persistence import LocalFilePlatformStore
from rorven.adapters.runtime.langgraph import LangGraphAgentRuntime
from rorven.application.modeling import ModelRequest, ModelResponse
from rorven.application.services import ProjectService, WorkerService


class TestModelGateway:
    def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            content="test model result",
            provider="test",
            model="test/model",
            usage={"total_tokens": 1},
        )


class LocalFileStoreTests(unittest.TestCase):
    def test_project_run_and_worker_state_survive_store_reopen(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-{uuid4()}"
        root.mkdir(parents=True, exist_ok=True)
        store = LocalFilePlatformStore(root)
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
        )
        worker = WorkerService(
            runs=store,
            tasks=store,
            artifacts=store,
            events=store,
            model_gateway=TestModelGateway(),
        )

        project = projects.create_project("Example", "D:/workspaces", "D:/workspaces/example")
        run_state = projects.submit_task(project.id, "Build backend and frontend")
        worker.work_once("test-worker")

        reopened = LocalFilePlatformStore(root)
        reopened_projects = ProjectService(
            runs=reopened,
            events=reopened,
            tasks=reopened,
            runtime=LangGraphAgentRuntime(reopened),
            artifacts=reopened,
        )
        reopened_state = reopened_projects.get_run_state(project.id, run_state.run.id)

        self.assertEqual("completed", reopened_state.run.status.value)
        self.assertEqual(1, len(reopened_state.agent_runs))
        self.assertEqual({"completed"}, {item.status.value for item in reopened_state.tasks})
        self.assertEqual(1, len(reopened_state.artifacts))
        self.assertTrue((root / "state.json").exists())

    def test_projects_are_listed_newest_first_after_reopen(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-order-{uuid4()}"
        root.mkdir(parents=True, exist_ok=True)
        store = LocalFilePlatformStore(root)
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
        )

        first = projects.create_project("First", "D:/workspaces", "D:/workspaces/first")
        second = projects.create_project("Second", "D:/workspaces", "D:/workspaces/second")

        reopened = LocalFilePlatformStore(root)
        reopened_projects = ProjectService(
            runs=reopened,
            events=reopened,
            tasks=reopened,
            runtime=LangGraphAgentRuntime(reopened),
            artifacts=reopened,
        )

        self.assertEqual(
            [second.id, first.id],
            [project.id for project in reopened_projects.list_projects()],
        )

    def test_duplicate_workspace_roots_are_rejected(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-duplicates-{uuid4()}"
        root.mkdir(parents=True, exist_ok=True)
        store = LocalFilePlatformStore(root)
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
        )

        projects.create_project("Example", "D:/workspaces", "D:/workspaces/example")

        with self.assertRaises(ValueError):
            projects.create_project("Duplicate", "D:/workspaces", "D:/workspaces/example/")

    def test_store_adds_missing_artifacts_bucket_on_reopen(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-migration-{uuid4()}"
        root.mkdir(parents=True, exist_ok=True)
        state_path = root / "state.json"
        state_path.write_text(
            json.dumps(
                {
                    "projects": {},
                    "runs": {},
                    "agent_runs": {},
                    "tasks": {},
                    "events": {},
                }
            ),
            encoding="utf-8",
        )

        LocalFilePlatformStore(root)

        migrated = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual({}, migrated["artifacts"])


if __name__ == "__main__":
    unittest.main()
