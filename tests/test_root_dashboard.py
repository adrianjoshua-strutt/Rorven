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


class RootDashboardTests(unittest.TestCase):
    def test_root_dashboard_returns_no_synthetic_messages_or_activities(self) -> None:
        data_dir = Path("test-output") / "tests" / f"root-{uuid4()}"
        data_dir.mkdir(parents=True, exist_ok=True)
        previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        previous_key = os.environ.get("RORVEN_OPENROUTER_API_KEY")
        self.addCleanup(_restore_env, "RORVEN_DATA_DIR", previous_data_dir)
        self.addCleanup(_restore_env, "RORVEN_OPENROUTER_API_KEY", previous_key)
        os.environ["RORVEN_DATA_DIR"] = str(data_dir.resolve())
        os.environ["RORVEN_OPENROUTER_API_KEY"] = "test-key"

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
        self.assertEqual([], root_payload["activities"])
        self.assertEqual([], root_payload["messages"])

    def test_root_dashboard_project_creation_does_not_create_fake_activities(self) -> None:
        data_dir = Path("test-output") / "tests" / f"root-dup-{uuid4()}"
        data_dir.mkdir(parents=True, exist_ok=True)
        previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        previous_key = os.environ.get("RORVEN_OPENROUTER_API_KEY")
        self.addCleanup(_restore_env, "RORVEN_DATA_DIR", previous_data_dir)
        self.addCleanup(_restore_env, "RORVEN_OPENROUTER_API_KEY", previous_key)
        os.environ["RORVEN_DATA_DIR"] = str(data_dir.resolve())
        os.environ["RORVEN_OPENROUTER_API_KEY"] = "test-key"

        module = importlib.import_module("rorven_api.main")
        client = TestClient(module.create_app())

        # Create one project
        create_response = client.post(
            "/projects",
            json={
                "name": "Project 1",
                "allowed_root": "D:/projects",
                "workspace_root": "D:/projects/proj1",
            },
        )
        self.assertEqual(201, create_response.status_code)
        created_id = create_response.json()["project"]["id"]

        root_response = client.get("/root")
        root_payload = root_response.json()["root"]
        activities = root_payload["activities"]
        self.assertEqual([], activities)
        
        create_response_2 = client.post(
            "/projects",
            json={
                "name": "Project 2",
                "allowed_root": "D:/projects",
                "workspace_root": "D:/projects/proj2",
            },
        )
        self.assertEqual(201, create_response_2.status_code)

        root_response_2 = client.get("/root")
        root_payload_2 = root_response_2.json()["root"]
        activities_2 = root_payload_2["activities"]
        self.assertEqual([], activities_2)

        projects_response = client.get("/projects")
        self.assertEqual(200, projects_response.status_code)
        project_ids = {project["id"] for project in projects_response.json()["projects"]}
        self.assertIn(created_id, project_ids)
        self.assertEqual(2, len(project_ids))

    def test_root_messages_are_stored_as_plain_chat_text(self) -> None:
        data_dir = Path("test-output") / "tests" / f"root-plain-{uuid4()}"
        data_dir.mkdir(parents=True, exist_ok=True)
        previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        previous_key = os.environ.get("RORVEN_OPENROUTER_API_KEY")
        self.addCleanup(_restore_env, "RORVEN_DATA_DIR", previous_data_dir)
        self.addCleanup(_restore_env, "RORVEN_OPENROUTER_API_KEY", previous_key)
        os.environ["RORVEN_DATA_DIR"] = str(data_dir.resolve())
        os.environ["RORVEN_OPENROUTER_API_KEY"] = "test-key"

        module = importlib.import_module("rorven_api.main")
        client = TestClient(module.create_app())

        with patch(
            "rorven.adapters.model.openrouter.OpenRouterModelGateway._post_json",
            return_value={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": (
                                "**Live Project Inventory:**  \n"
                                "- No projects currently registered.\n\n"
                                "**Operational Response:**\n"
                                "Use the Project button to register the workspace."
                            ),
                        }
                    }
                ],
                "model": "test/model",
                "usage": {"total_tokens": 9},
            },
        ):
            response = client.post(
                "/root/messages",
                json={"message": "can you create a project for me on my desktop?"},
            )

        self.assertEqual(200, response.status_code)
        messages = response.json()["root"]["messages"]
        assistant = messages[-1]

        self.assertEqual("Root orchestrator", assistant["title"])
        self.assertNotIn("**", assistant["body"])
        self.assertNotIn("- No projects", assistant["body"])
        self.assertIn("Live Project Inventory:", assistant["body"])


if __name__ == "__main__":
    unittest.main()
