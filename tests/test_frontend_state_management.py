from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4
import unittest

from fastapi.testclient import TestClient


class FrontendStateManagementTests(unittest.TestCase):
    """Test frontend state management to verify no duplicates or stale state."""

    def setUp(self) -> None:
        self.data_dir = Path("test-output") / "tests" / f"frontend-state-{uuid4()}"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        os.environ["RORVEN_DATA_DIR"] = str(self.data_dir.resolve())

    def tearDown(self) -> None:
        if self.previous_data_dir is None:
            os.environ.pop("RORVEN_DATA_DIR", None)
        else:
            os.environ["RORVEN_DATA_DIR"] = self.previous_data_dir

    def test_no_duplicate_projects_created(self) -> None:
        """Verify that creating a project via API doesn't create duplicates."""
        from rorven_api.main import create_app

        client = TestClient(create_app())

        # Simulate user creating first project
        print("Creating Project 1")
        create1 = client.post(
            "/projects",
            json={
                "name": "Project 1",
                "allowed_root": "D:/projects",
                "workspace_root": "D:/projects/proj1",
            },
        )
        self.assertEqual(201, create1.status_code)
        proj1_id = create1.json()["project"]["id"]

        # Simulate frontend fetching projects list (what happens after creation)
        list1 = client.get("/projects")
        projects_after_first = list1.json()["projects"]
        print(f"After first creation: {len(projects_after_first)} projects")
        self.assertEqual(len(projects_after_first), 1, "Should have exactly 1 project")
        self.assertEqual(projects_after_first[0]["id"], proj1_id)

        # Simulate user creating second project
        print("Creating Project 2")
        create2 = client.post(
            "/projects",
            json={
                "name": "Project 2",
                "allowed_root": "D:/projects",
                "workspace_root": "D:/projects/proj2",
            },
        )
        self.assertEqual(201, create2.status_code)
        proj2_id = create2.json()["project"]["id"]

        # Simulate frontend fetching projects list again
        list2 = client.get("/projects")
        projects_after_second = list2.json()["projects"]
        print(f"After second creation: {len(projects_after_second)} projects")
        self.assertEqual(len(projects_after_second), 2, "Should have exactly 2 projects")
        
        # Verify no duplicates
        project_ids = [p["id"] for p in projects_after_second]
        unique_ids = set(project_ids)
        self.assertEqual(len(project_ids), len(unique_ids), "Should have no duplicate IDs")
        self.assertIn(proj1_id, unique_ids)
        self.assertIn(proj2_id, unique_ids)

    def test_root_dashboard_shows_correct_project_count(self) -> None:
        """Verify root dashboard activities match actual project count."""
        from rorven_api.main import create_app

        client = TestClient(create_app())

        # Create 3 projects
        project_ids = []
        for i in range(1, 4):
            create_resp = client.post(
                "/projects",
                json={
                    "name": f"Project {i}",
                    "allowed_root": "D:/projects",
                    "workspace_root": f"D:/projects/proj{i}",
                },
            )
            self.assertEqual(201, create_resp.status_code)
            project_ids.append(create_resp.json()["project"]["id"])

        # Get projects list
        projects_list = client.get("/projects")
        projects_count = len(projects_list.json()["projects"])
        print(f"Projects API: {projects_count} projects")

        # Get root dashboard activities
        root_resp = client.get("/root")
        activities = root_resp.json()["root"]["activities"]
        activities_count = len(activities)
        print(f"Root dashboard: {activities_count} activities")

        # Should match
        self.assertEqual(activities_count, projects_count, 
                        f"Root dashboard activities ({activities_count}) should match projects ({projects_count})")
        self.assertEqual(activities_count, 3)
        
        # Verify all projects are in activities (activities have prefixed IDs)
        for proj_id in project_ids:
            expected_activity_id = f"root-project-{proj_id}"
            activity_found = any(a["id"] == expected_activity_id for a in activities)
            self.assertTrue(activity_found, f"Project {proj_id} should have corresponding activity {expected_activity_id}")


if __name__ == "__main__":
    unittest.main()
