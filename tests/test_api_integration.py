from __future__ import annotations

import importlib
import os
from pathlib import Path
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
                "choices": [{"message": {"role": "assistant", "content": "project result"}}],
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


if __name__ == "__main__":
    unittest.main()
