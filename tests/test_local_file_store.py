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
            content='{"action":"answer","content":"test model result"}',
            provider="test",
            model="test/model",
            usage={"total_tokens": 1},
        )


class ScriptedModelGateway:
    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self.requests: list[ModelRequest] = []

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        try:
            content = self._responses.pop(0)
        except IndexError as exc:
            raise AssertionError("unexpected model request") from exc
        return ModelResponse(
            content=content,
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

    def test_worker_dispatches_child_agents_and_joins_results(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-dispatch-{uuid4()}"
        root.mkdir(parents=True, exist_ok=True)
        store = LocalFilePlatformStore(root)
        projects = ProjectService(
            runs=store,
            events=store,
            tasks=store,
            runtime=LangGraphAgentRuntime(store),
            artifacts=store,
        )
        gateway = ScriptedModelGateway(
            [
                (
                    '{"action":"dispatch","subagents":['
                    '{"name":"reviewer","task":"Review the request for risks."},'
                    '{"name":"implementer","task":"Plan the implementation."}'
                    "]} "
                ),
                "reviewer result",
                "implementer result",
                "summary result",
            ]
        )
        worker = WorkerService(
            runs=store,
            tasks=store,
            artifacts=store,
            events=store,
            model_gateway=gateway,
        )

        project = projects.create_project("Example", "D:/workspaces", "D:/workspaces/example")
        run_state = projects.submit_task(project.id, "Build backend and frontend")

        self.assertEqual(1, len(worker.work_once("test-worker", limit=1)))
        waiting_state = projects.get_run_state(project.id, run_state.run.id)
        self.assertEqual("waiting", waiting_state.run.status.value)
        self.assertEqual(3, len(waiting_state.agent_runs))
        self.assertEqual(3, len(waiting_state.tasks))
        self.assertEqual(
            ["orchestrator", "reviewer", "implementer"],
            [agent.definition.name for agent in waiting_state.agent_runs],
        )

        self.assertEqual(2, len(worker.work_once("test-worker", limit=2)))
        finished_state = projects.get_run_state(project.id, run_state.run.id)
        self.assertEqual("completed", finished_state.run.status.value)
        self.assertEqual({"completed"}, {task.status.value for task in finished_state.tasks})
        self.assertEqual({"completed"}, {agent.status.value for agent in finished_state.agent_runs})
        artifact_text = "\n".join(finished_state.artifact_contents.values())
        self.assertIn("Review the request for risks.", artifact_text)
        self.assertIn("reviewer result", artifact_text)
        self.assertIn("implementer result", artifact_text)
        self.assertIn("summary result", artifact_text)

    def test_malformed_orchestrator_dispatch_fails_run(self) -> None:
        root = Path("test-output") / "tests" / f"local-store-dispatch-fail-{uuid4()}"
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
            model_gateway=ScriptedModelGateway(["not-json"]),
        )

        project = projects.create_project("Example", "D:/workspaces", "D:/workspaces/example")
        run_state = projects.submit_task(project.id, "Build backend and frontend")

        self.assertEqual(0, len(worker.work_once("test-worker", limit=1)))
        failed_state = projects.get_run_state(project.id, run_state.run.id)
        self.assertEqual("failed", failed_state.run.status.value)
        self.assertEqual({"failed"}, {task.status.value for task in failed_state.tasks})
        self.assertEqual({"failed"}, {agent.status.value for agent in failed_state.agent_runs})
        artifact_text = "\n".join(failed_state.artifact_contents.values())
        self.assertIn("orchestrator response was not valid JSON", artifact_text)

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
