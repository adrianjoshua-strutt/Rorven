from __future__ import annotations

import importlib
import json
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
                json={"message": "summarize the current project inventory"},
            )

        self.assertEqual(200, response.status_code)
        messages = response.json()["root"]["messages"]
        assistant = messages[-1]

        self.assertEqual("Root orchestrator", assistant["title"])
        self.assertNotIn("**", assistant["body"])
        self.assertNotIn("- No projects", assistant["body"])
        self.assertIn("Live Project Inventory:", assistant["body"])

    def test_root_chat_creates_project_under_configured_workspace_base(self) -> None:
        data_dir = Path("test-output") / "tests" / f"root-create-{uuid4()}" / "state"
        workspace_base = data_dir.parent / "workspaces"
        data_dir.mkdir(parents=True, exist_ok=True)
        previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        previous_key = os.environ.get("RORVEN_OPENROUTER_API_KEY")
        self.addCleanup(_restore_env, "RORVEN_DATA_DIR", previous_data_dir)
        self.addCleanup(_restore_env, "RORVEN_OPENROUTER_API_KEY", previous_key)
        os.environ["RORVEN_DATA_DIR"] = str(data_dir.resolve())
        os.environ["RORVEN_OPENROUTER_API_KEY"] = "test-key"

        module = importlib.import_module("rorven_api.main")
        client = TestClient(module.create_app())
        settings_response = client.post(
            "/settings/project-defaults",
            json={"workspace_base_root": str(workspace_base.resolve())},
        )
        self.assertEqual(200, settings_response.status_code)

        with patch(
            "rorven.adapters.model.openrouter.OpenRouterModelGateway._post_json",
            return_value={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": (
                                '{"action":"tool_call","tool":{"name":"project.create",'
                                '"input":{"name":"Alpha Build"}}}'
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
                json={"message": "create a project called Alpha Build"},
            )

        self.assertEqual(200, response.status_code)
        assistant = response.json()["root"]["messages"][-1]
        self.assertIn("Created project Alpha Build", assistant["body"])
        self.assertTrue((workspace_base / "Alpha-Build").is_dir())

        projects_response = client.get("/projects")
        projects = projects_response.json()["projects"]
        self.assertEqual(1, len(projects))
        self.assertEqual("Alpha Build", projects[0]["name"])
        self.assertEqual(str(workspace_base.resolve()), projects[0]["workspace"]["allowed_root"])

    def test_root_chat_asks_for_name_before_creating_project(self) -> None:
        data_dir = Path("test-output") / "tests" / f"root-create-missing-name-{uuid4()}"
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
                                '{"action":"ask","content":"What should the project be called? '
                                'I will place it under the configured workspace base."}'
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
                json={"message": "can you create a project on my desktop for me?"},
            )

        self.assertEqual(200, response.status_code)
        assistant = response.json()["root"]["messages"][-1]
        self.assertIn("What should the project be called?", assistant["body"])
        self.assertEqual([], client.get("/projects").json()["projects"])

    def test_root_chat_rejects_project_tool_path_outside_workspace_base(self) -> None:
        data_dir = Path("test-output") / "tests" / f"root-create-outside-{uuid4()}" / "state"
        workspace_base = data_dir.parent / "workspaces"
        outside_root = data_dir.parent / "outside" / "Beta"
        data_dir.mkdir(parents=True, exist_ok=True)
        previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        previous_key = os.environ.get("RORVEN_OPENROUTER_API_KEY")
        self.addCleanup(_restore_env, "RORVEN_DATA_DIR", previous_data_dir)
        self.addCleanup(_restore_env, "RORVEN_OPENROUTER_API_KEY", previous_key)
        os.environ["RORVEN_DATA_DIR"] = str(data_dir.resolve())
        os.environ["RORVEN_OPENROUTER_API_KEY"] = "test-key"

        module = importlib.import_module("rorven_api.main")
        client = TestClient(module.create_app())
        settings_response = client.post(
            "/settings/project-defaults",
            json={"workspace_base_root": str(workspace_base.resolve())},
        )
        self.assertEqual(200, settings_response.status_code)

        with patch(
            "rorven.adapters.model.openrouter.OpenRouterModelGateway._post_json",
            return_value={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(
                                {
                                    "action": "tool_call",
                                    "tool": {
                                        "name": "project.create",
                                        "input": {
                                            "name": "Beta",
                                            "workspace_root": str(outside_root.resolve()),
                                        },
                                    },
                                }
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
                json={"message": "create a project called Beta outside the base"},
            )

        self.assertEqual(200, response.status_code)
        assistant = response.json()["root"]["messages"][-1]
        self.assertIn("outside the configured workspace base", assistant["body"])
        self.assertFalse(outside_root.exists())
        self.assertEqual([], client.get("/projects").json()["projects"])


if __name__ == "__main__":
    unittest.main()
