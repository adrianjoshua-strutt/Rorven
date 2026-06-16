from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4
import unittest

from fastapi.testclient import TestClient


class BackendOnlyE2ETests(unittest.TestCase):
    """Verify the entire application uses backend-only state with no client-side caching."""

    def setUp(self) -> None:
        self.data_dir = Path("test-output") / "tests" / f"backend-only-{uuid4()}"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        os.environ["RORVEN_DATA_DIR"] = str(self.data_dir.resolve())

    def tearDown(self) -> None:
        if self.previous_data_dir is None:
            os.environ.pop("RORVEN_DATA_DIR", None)
        else:
            os.environ["RORVEN_DATA_DIR"] = self.previous_data_dir

    def test_full_workflow_backend_only(self) -> None:
        """
        Complete workflow:
        1. Create project
        2. Verify persistence across app restart
        3. Submit run command
        4. Verify run persists
        5. Submit root message
        6. Verify root message persists across restart
        """
        # Create first app instance
        from rorven_api.main import create_app

        client = TestClient(create_app())

        # Verify initial empty state
        projects_r = client.get("/projects")
        assert projects_r.status_code == 200
        assert len(projects_r.json()["projects"]) == 0
        print("[OK] Initial state: 0 projects")

        # Create a project
        create_project_r = client.post(
            "/projects",
            json={
                "name": "E2E Test Project",
                "allowed_root": "D:/test",
                "workspace_root": "D:/test/e2e",
            },
        )
        assert create_project_r.status_code == 201
        project = create_project_r.json()["project"]
        project_id = project["id"]
        print(f"[OK] Created project {project_id}")

        # Verify project appears in list
        projects_r = client.get("/projects")
        projects = projects_r.json()["projects"]
        assert len(projects) == 1
        assert projects[0]["id"] == project_id
        print("[OK] Project listed immediately after creation")

        # Submit a run command
        submit_r = client.post(
            f"/projects/{project_id}/runs",
            json={"command": "Test command"},
        )
        assert submit_r.status_code == 202
        run = submit_r.json()["run"]
        run_id = run["id"]
        assert run["command"] == "Test command"
        print(f"[OK] Submitted run {run_id}")

        # Verify run persists in project
        get_project_r = client.get(f"/projects/{project_id}")
        assert get_project_r.status_code == 200
        project_state = get_project_r.json()["project"]
        runs = project_state.get("runs", [])
        assert len(runs) >= 1
        assert runs[0]["id"] == run_id
        print("[OK] Run listed in project immediately after creation")

        # Submit root message
        root_r_before = client.get("/root")
        messages_before = len(root_r_before.json()["root"]["messages"])

        root_submit_r = client.post(
            "/root/messages", json={"message": "E2E test message"}
        )
        assert root_submit_r.status_code == 200
        root_state = root_submit_r.json()["root"]
        messages_after = len(root_state["messages"])
        assert messages_after > messages_before
        print(f"[OK] Submitted root message ({messages_before} -> {messages_after} messages)")

        # ========== SIMULATE BROWSER REFRESH: NEW APP INSTANCE ==========
        del client
        import importlib

        import rorven_api.main

        importlib.reload(rorven_api.main)
        client = TestClient(rorven_api.main.create_app())

        # Verify project still exists after restart
        projects_r_2 = client.get("/projects")
        projects_2 = projects_r_2.json()["projects"]
        assert len(projects_2) == 1, f"Expected 1 project after restart, got {len(projects_2)}"
        assert projects_2[0]["id"] == project_id
        print("[OK] Project persists after app restart")

        # Verify run still exists after restart
        get_project_r_2 = client.get(f"/projects/{project_id}")
        project_state_2 = get_project_r_2.json()["project"]
        runs_2 = project_state_2.get("runs", [])
        assert len(runs_2) >= 1
        assert runs_2[0]["id"] == run_id
        print("[OK] Run persists after app restart")

        # Verify root messages still exist after restart
        root_r_2 = client.get("/root")
        root_state_2 = root_r_2.json()["root"]
        messages_2 = root_state_2["messages"]
        assert len(messages_2) == messages_after
        print("[OK] Root messages persist after app restart")

        print("[PASS] Full backend-only E2E workflow PASSED")


if __name__ == "__main__":
    unittest.main()
