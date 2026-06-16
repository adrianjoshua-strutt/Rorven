from __future__ import annotations

import importlib
from pathlib import Path
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient


class ApiIntegrationTests(unittest.TestCase):
    def test_create_project_submit_run_and_work_once(self) -> None:
        import os

        data_dir = Path("test-output") / "tests" / f"api-{uuid4()}"
        data_dir.mkdir(parents=True, exist_ok=True)
        os.environ["RORVEN_DATA_DIR"] = str(data_dir.resolve())
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

        run_response = client.post(
            f"/projects/{project_id}/runs",
            json={"command": "Build backend and frontend"},
        )
        self.assertEqual(202, run_response.status_code)
        run_payload = run_response.json()["run"]
        self.assertEqual(3, len(run_payload["agent_runs"]))
        self.assertEqual(2, len(run_payload["tasks"]))

        work_response = client.post("/worker/work-once", json={"worker_id": "api-test"})
        self.assertEqual(200, work_response.status_code)
        self.assertEqual(2, len(work_response.json()["completed_tasks"]))

        state_response = client.get(f"/projects/{project_id}/runs/{run_payload['id']}")
        self.assertEqual(200, state_response.status_code)
        state_payload = state_response.json()["run"]
        self.assertEqual("completed", state_payload["status"])
        self.assertEqual({"completed"}, {task["status"] for task in state_payload["tasks"]})
        self.assertTrue((data_dir / "state.json").exists())


if __name__ == "__main__":
    unittest.main()
