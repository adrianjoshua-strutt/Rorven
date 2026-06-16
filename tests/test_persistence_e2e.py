from __future__ import annotations

import importlib
import os
from pathlib import Path
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


class PersistenceE2ETests(unittest.TestCase):
    def test_projects_persist_across_app_restarts(self) -> None:
        """Verify that creating a project survives app restart."""
        data_dir = Path("test-output") / "tests" / f"persist-e2e-{uuid4()}"
        data_dir.mkdir(parents=True, exist_ok=True)
        previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        previous_key = os.environ.get("RORVEN_OPENROUTER_API_KEY")
        self.addCleanup(_restore_env, "RORVEN_DATA_DIR", previous_data_dir)
        self.addCleanup(_restore_env, "RORVEN_OPENROUTER_API_KEY", previous_key)
        os.environ["RORVEN_DATA_DIR"] = str(data_dir.resolve())
        os.environ["RORVEN_OPENROUTER_API_KEY"] = "test-secret-that-must-not-leak"

        module = importlib.import_module("rorven_api.main")
        
        # First app instance: create a project
        client1 = TestClient(module.create_app())
        create_response = client1.post(
            "/projects",
            json={
                "name": "Persistent Test",
                "allowed_root": "D:/test",
                "workspace_root": "D:/test/persist",
            },
        )
        self.assertEqual(201, create_response.status_code)
        created_project_id = create_response.json()["project"]["id"]
        print(f"Created project {created_project_id} in {data_dir}")

        # Verify project exists in first instance
        list_response_1 = client1.get("/projects")
        self.assertEqual(200, list_response_1.status_code)
        projects_1 = list_response_1.json()["projects"]
        self.assertEqual(1, len(projects_1))
        self.assertEqual(created_project_id, projects_1[0]["id"])
        print(f"First instance found {len(projects_1)} projects")

        # Verify state file was written
        state_file = data_dir / "state.json"
        self.assertTrue(state_file.exists(), f"state.json not found at {state_file}")
        print(f"State file exists at {state_file}")

        # Second app instance: verify project still exists
        # Reload the module to force a new app instance
        del module
        importlib.invalidate_caches()
        module = importlib.import_module("rorven_api.main")
        client2 = TestClient(module.create_app())
        
        list_response_2 = client2.get("/projects")
        self.assertEqual(200, list_response_2.status_code)
        projects_2 = list_response_2.json()["projects"]
        self.assertEqual(1, len(projects_2), f"Second instance should see 1 project, got {len(projects_2)}")
        self.assertEqual(created_project_id, projects_2[0]["id"])
        print(f"Second instance found {len(projects_2)} projects - persistence works!")


if __name__ == "__main__":
    unittest.main()
