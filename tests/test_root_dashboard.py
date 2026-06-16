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


class RootDashboardTests(unittest.TestCase):
    def test_root_dashboard_returns_live_inventory_and_persists_messages(self) -> None:
        data_dir = Path("test-output") / "tests" / f"root-{uuid4()}"
        data_dir.mkdir(parents=True, exist_ok=True)
        previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        self.addCleanup(_restore_env, "RORVEN_DATA_DIR", previous_data_dir)
        os.environ["RORVEN_DATA_DIR"] = str(data_dir.resolve())

        module = importlib.import_module("rorven_api.main")
        client = TestClient(module.create_app())

        create_response = client.post(
            "/projects",
            json={
                "name": "Example",
                "allowed_root": "D:/workspaces",
                "workspace_root": "D:/workspaces/example",
            },
        )
        self.assertEqual(201, create_response.status_code)

        root_response = client.get("/root")
        self.assertEqual(200, root_response.status_code)
        root_payload = root_response.json()["root"]
        self.assertGreaterEqual(len(root_payload["activities"]), 1)
        self.assertGreaterEqual(len(root_payload["messages"]), 1)

        submit_response = client.post("/root/messages", json={"message": "Create a new project for me."})
        self.assertEqual(200, submit_response.status_code)
        submit_payload = submit_response.json()["root"]
        self.assertGreaterEqual(len(submit_payload["messages"]), 3)
        self.assertTrue(any(message["side"] == "orchestrator" for message in submit_payload["messages"]))


if __name__ == "__main__":
    unittest.main()