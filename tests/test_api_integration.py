from __future__ import annotations

import importlib
import os
from pathlib import Path
from time import sleep
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


class ApiIntegrationTests(unittest.TestCase):
    def test_create_project_submit_run_and_work_once(self) -> None:
        data_dir = Path("test-output") / "tests" / f"api-{uuid4()}"
        data_dir.mkdir(parents=True, exist_ok=True)
        previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        previous_key = os.environ.get("RORVEN_OPENROUTER_API_KEY")
        self.addCleanup(_restore_env, "RORVEN_DATA_DIR", previous_data_dir)
        self.addCleanup(_restore_env, "RORVEN_OPENROUTER_API_KEY", previous_key)
        os.environ["RORVEN_DATA_DIR"] = str(data_dir.resolve())
        os.environ["RORVEN_OPENROUTER_API_KEY"] = "test-secret-that-must-not-leak"
        module = importlib.import_module("rorven_api.main")
        app = module.create_app()
        client = TestClient(app)

        project_response = client.post(
            "/projects",
            json={
                "name": "Example",
                "allowed_root": "D:/workspaces",
                "workspace_root": "D:/workspaces/example",
            },
        )
        self.assertEqual(201, project_response.status_code)
        project_id = project_response.json()["project"]["id"]

        duplicate_response = client.post(
            "/projects",
            json={
                "name": "Duplicate",
                "allowed_root": "D:/workspaces",
                "workspace_root": "D:/workspaces/example",
            },
        )
        self.assertEqual(400, duplicate_response.status_code)

        run_response = client.post(
            f"/projects/{project_id}/runs",
            json={"command": "Build backend and frontend"},
        )
        self.assertEqual(202, run_response.status_code)
        run_payload = run_response.json()["run"]
        self.assertEqual(1, len(run_payload["agent_runs"]))
        self.assertEqual(1, len(run_payload["tasks"]))

        with patch(
            "rorven.adapters.model.openrouter.OpenRouterModelGateway._post_json",
            return_value={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"action":"answer","content":"project result"}',
                        }
                    }
                ],
                "model": "test/model",
                "usage": {"total_tokens": 7},
            },
        ):
            work_response = client.post("/worker/work-once", json={"worker_id": "api-test"})
        self.assertEqual(200, work_response.status_code)
        self.assertEqual(1, len(work_response.json()["completed_tasks"]))

        state_response = client.get(f"/projects/{project_id}/runs/{run_payload['id']}")
        self.assertEqual(200, state_response.status_code)
        state_payload = state_response.json()["run"]
        self.assertEqual("completed", state_payload["status"])
        self.assertEqual({"completed"}, {task["status"] for task in state_payload["tasks"]})
        self.assertEqual(1, len(state_payload["artifacts"]))
        self.assertIn("project result", state_payload["artifacts"][0]["content"])
        self.assertTrue((data_dir / "state.json").exists())

    def test_project_detail_preserves_activity_sort_metadata(self) -> None:
        data_dir = Path("test-output") / "tests" / f"api-project-activity-{uuid4()}"
        data_dir.mkdir(parents=True, exist_ok=True)
        previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        previous_key = os.environ.get("RORVEN_OPENROUTER_API_KEY")
        self.addCleanup(_restore_env, "RORVEN_DATA_DIR", previous_data_dir)
        self.addCleanup(_restore_env, "RORVEN_OPENROUTER_API_KEY", previous_key)
        os.environ["RORVEN_DATA_DIR"] = str(data_dir.resolve())
        os.environ["RORVEN_OPENROUTER_API_KEY"] = "test-secret-that-must-not-leak"
        module = importlib.import_module("rorven_api.main")
        client = TestClient(module.create_app())

        project_response = client.post(
            "/projects",
            json={
                "name": "Sortable Project",
                "allowed_root": "D:/workspaces",
                "workspace_root": "D:/workspaces/sortable-project",
            },
        )
        self.assertEqual(201, project_response.status_code)
        project_id = project_response.json()["project"]["id"]
        run_response = client.post(
            f"/projects/{project_id}/runs",
            json={"command": "latest user message"},
        )
        self.assertEqual(202, run_response.status_code)

        list_project = client.get("/projects").json()["projects"][0]
        detail_project = client.get(f"/projects/{project_id}").json()["project"]

        self.assertEqual(list_project["last_user_message_at"], detail_project["last_user_message_at"])
        self.assertEqual(list_project["last_activity_at"], detail_project["last_activity_at"])

    def test_embedded_worker_completes_project_run_from_api_lifespan(self) -> None:
        data_dir = Path("test-output") / "tests" / f"api-embedded-worker-{uuid4()}"
        data_dir.mkdir(parents=True, exist_ok=True)
        previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        previous_key = os.environ.get("RORVEN_OPENROUTER_API_KEY")
        previous_worker = os.environ.get("RORVEN_API_EMBEDDED_WORKER")
        previous_poll = os.environ.get("RORVEN_API_EMBEDDED_WORKER_POLL_SECONDS")
        self.addCleanup(_restore_env, "RORVEN_DATA_DIR", previous_data_dir)
        self.addCleanup(_restore_env, "RORVEN_OPENROUTER_API_KEY", previous_key)
        self.addCleanup(_restore_env, "RORVEN_API_EMBEDDED_WORKER", previous_worker)
        self.addCleanup(_restore_env, "RORVEN_API_EMBEDDED_WORKER_POLL_SECONDS", previous_poll)
        os.environ["RORVEN_DATA_DIR"] = str(data_dir.resolve())
        os.environ["RORVEN_OPENROUTER_API_KEY"] = "test-secret-that-must-not-leak"
        os.environ["RORVEN_API_EMBEDDED_WORKER"] = "1"
        os.environ["RORVEN_API_EMBEDDED_WORKER_POLL_SECONDS"] = "0.05"

        module = importlib.import_module("rorven_api.main")
        app = module.create_app()

        with patch(
            "rorven.adapters.model.openrouter.OpenRouterModelGateway._post_json",
            return_value={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"action":"answer","content":"embedded worker result"}',
                        }
                    }
                ],
                "model": "test/model",
                "usage": {"total_tokens": 7},
            },
        ):
            with TestClient(app) as client:
                worker_response = client.get("/worker/status")
                self.assertEqual(200, worker_response.status_code)
                self.assertTrue(worker_response.json()["worker"]["running"])

                project_response = client.post(
                    "/projects",
                    json={
                        "name": "Embedded Worker Example",
                        "allowed_root": "D:/workspaces",
                        "workspace_root": "D:/workspaces/embedded-worker-example",
                    },
                )
                self.assertEqual(201, project_response.status_code)
                project_id = project_response.json()["project"]["id"]

                run_response = client.post(
                    f"/projects/{project_id}/runs",
                    json={"command": "Answer through the embedded worker"},
                )
                self.assertEqual(202, run_response.status_code)
                run_id = run_response.json()["run"]["id"]

                state_payload = None
                for _ in range(60):
                    state_response = client.get(f"/projects/{project_id}/runs/{run_id}")
                    self.assertEqual(200, state_response.status_code)
                    state_payload = state_response.json()["run"]
                    if state_payload["status"] == "completed":
                        break
                    sleep(0.05)

                self.assertIsNotNone(state_payload)
                self.assertEqual("completed", state_payload["status"])
                self.assertIn("embedded worker result", state_payload["artifacts"][0]["content"])
                final_status = client.get("/worker/status").json()["worker"]
                self.assertGreaterEqual(final_status["completed_tasks"], 1)

    def test_embedded_worker_runs_subagent_tools_and_approval_flow(self) -> None:
        root = Path("test-output") / "tests" / f"api-embedded-tools-{uuid4()}"
        data_dir = root / "state"
        workspace = root / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        readme = workspace / "README.md"
        readme.write_text("Before\n", encoding="utf-8")
        previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        previous_key = os.environ.get("RORVEN_OPENROUTER_API_KEY")
        previous_worker = os.environ.get("RORVEN_API_EMBEDDED_WORKER")
        previous_poll = os.environ.get("RORVEN_API_EMBEDDED_WORKER_POLL_SECONDS")
        self.addCleanup(_restore_env, "RORVEN_DATA_DIR", previous_data_dir)
        self.addCleanup(_restore_env, "RORVEN_OPENROUTER_API_KEY", previous_key)
        self.addCleanup(_restore_env, "RORVEN_API_EMBEDDED_WORKER", previous_worker)
        self.addCleanup(_restore_env, "RORVEN_API_EMBEDDED_WORKER_POLL_SECONDS", previous_poll)
        os.environ["RORVEN_DATA_DIR"] = str(data_dir.resolve())
        os.environ["RORVEN_OPENROUTER_API_KEY"] = "test-secret-that-must-not-leak"
        os.environ["RORVEN_API_EMBEDDED_WORKER"] = "1"
        os.environ["RORVEN_API_EMBEDDED_WORKER_POLL_SECONDS"] = "0.05"

        scripted_responses = [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"action":"dispatch","subagents":[{"name":"implementer","task":"Inspect README, then propose an update."}]}',
                        }
                    }
                ],
                "model": "test/model",
                "usage": {"total_tokens": 7},
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": (
                                '{"action":"tool_calls","tool_calls":['
                                '{"name":"workspace.read_text_file","input":{"path":"README.md","max_bytes":2000}}'
                                "]} "
                            ),
                        }
                    }
                ],
                "model": "test/model",
                "usage": {"total_tokens": 7},
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": (
                                '{"action":"tool_calls","tool_calls":['
                                '{"name":"workspace.propose_text_file_write",'
                                '"input":{"path":"README.md","content":"Before\\nAfter\\n"}}'
                                "]} "
                            ),
                        }
                    }
                ],
                "model": "test/model",
                "usage": {"total_tokens": 7},
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Summary includes the applied README change.",
                        }
                    }
                ],
                "model": "test/model",
                "usage": {"total_tokens": 7},
            },
        ]

        module = importlib.import_module("rorven_api.main")
        app = module.create_app()

        with patch(
            "rorven.adapters.model.openrouter.OpenRouterModelGateway._post_json",
            side_effect=scripted_responses,
        ):
            with TestClient(app) as client:
                project_response = client.post(
                    "/projects",
                    json={
                        "name": "Embedded Tool Example",
                        "allowed_root": str(root.resolve()),
                        "workspace_root": str(workspace.resolve()),
                    },
                )
                self.assertEqual(201, project_response.status_code)
                project_id = project_response.json()["project"]["id"]

                run_response = client.post(
                    f"/projects/{project_id}/runs",
                    json={"command": "Update the README"},
                )
                self.assertEqual(202, run_response.status_code)
                run_id = run_response.json()["run"]["id"]

                state_payload = None
                for _ in range(80):
                    state_response = client.get(f"/projects/{project_id}/runs/{run_id}")
                    self.assertEqual(200, state_response.status_code)
                    state_payload = state_response.json()["run"]
                    if state_payload["approvals"]:
                        break
                    sleep(0.05)

                self.assertIsNotNone(state_payload)
                self.assertEqual("waiting", state_payload["status"])
                self.assertEqual("Before\n", readme.read_text(encoding="utf-8"))
                self.assertEqual(1, len(state_payload["approvals"]))
                artifact_text = "\n".join(artifact["content"] for artifact in state_payload["artifacts"])
                self.assertIn("+After", artifact_text)
                approval_id = state_payload["approvals"][0]["id"]

                approve_response = client.post(
                    f"/projects/{project_id}/runs/{run_id}/approvals/{approval_id}/approve"
                )
                self.assertEqual(200, approve_response.status_code)
                self.assertEqual("applied", approve_response.json()["approval"]["status"])
                self.assertEqual("Before\nAfter\n", readme.read_text(encoding="utf-8"))
                completed_payload = client.get(f"/projects/{project_id}/runs/{run_id}").json()["run"]
                self.assertEqual("completed", completed_payload["status"])

    def test_approval_endpoint_applies_proposed_workspace_write(self) -> None:
        root = Path("test-output") / "tests" / f"api-approval-{uuid4()}"
        data_dir = root / "state"
        workspace = root / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        readme = workspace / "README.md"
        readme.write_text("Before\n", encoding="utf-8")
        previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        previous_key = os.environ.get("RORVEN_OPENROUTER_API_KEY")
        self.addCleanup(_restore_env, "RORVEN_DATA_DIR", previous_data_dir)
        self.addCleanup(_restore_env, "RORVEN_OPENROUTER_API_KEY", previous_key)
        os.environ["RORVEN_DATA_DIR"] = str(data_dir.resolve())
        os.environ["RORVEN_OPENROUTER_API_KEY"] = "test-secret-that-must-not-leak"
        module = importlib.import_module("rorven_api.main")
        app = module.create_app()
        client = TestClient(app)

        project_response = client.post(
            "/projects",
            json={
                "name": "Approval Example",
                "allowed_root": str(root.resolve()),
                "workspace_root": str(workspace.resolve()),
            },
        )
        self.assertEqual(201, project_response.status_code)
        project_id = project_response.json()["project"]["id"]
        run_response = client.post(
            f"/projects/{project_id}/runs",
            json={"command": "Propose README update"},
        )
        self.assertEqual(202, run_response.status_code)
        run_id = run_response.json()["run"]["id"]

        scripted_responses = [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"action":"dispatch","subagents":[{"name":"implementer","task":"Propose README update."}]}',
                        }
                    }
                ],
                "model": "test/model",
                "usage": {"total_tokens": 7},
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": (
                                '{"action":"tool_calls","tool_calls":['
                                '{"name":"workspace.propose_text_file_write",'
                                '"input":{"path":"README.md","content":"After\\n"}}'
                                "]} "
                            ),
                        }
                    }
                ],
                "model": "test/model",
                "usage": {"total_tokens": 7},
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Summary includes applied proposal.",
                        }
                    }
                ],
                "model": "test/model",
                "usage": {"total_tokens": 7},
            },
        ]
        with patch(
            "rorven.adapters.model.openrouter.OpenRouterModelGateway._post_json",
            side_effect=scripted_responses,
        ):
            self.assertEqual(200, client.post("/worker/work-once", json={"worker_id": "api-test", "limit": 1}).status_code)
            self.assertEqual(200, client.post("/worker/work-once", json={"worker_id": "api-test", "limit": 1}).status_code)

            approvals_response = client.get(f"/projects/{project_id}/runs/{run_id}/approvals")
            self.assertEqual(200, approvals_response.status_code)
            approvals = approvals_response.json()["approvals"]
            self.assertEqual(1, len(approvals))
            self.assertEqual("pending", approvals[0]["status"])
            self.assertEqual("Before\n", readme.read_text(encoding="utf-8"))
            waiting_response = client.get(f"/projects/{project_id}/runs/{run_id}")
            self.assertEqual("waiting", waiting_response.json()["run"]["status"])

            approve_response = client.post(
                f"/projects/{project_id}/runs/{run_id}/approvals/{approvals[0]['id']}/approve"
            )

            self.assertEqual(200, approve_response.status_code)
            self.assertEqual("applied", approve_response.json()["approval"]["status"])
            self.assertEqual("After\n", readme.read_text(encoding="utf-8"))
            completed_response = client.get(f"/projects/{project_id}/runs/{run_id}")
            self.assertEqual("completed", completed_response.json()["run"]["status"])


if __name__ == "__main__":
    unittest.main()
