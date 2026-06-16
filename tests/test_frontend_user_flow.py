from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4
import unittest

from fastapi.testclient import TestClient


class FrontendIntegrationTests(unittest.TestCase):
    """Simulate complete frontend user flow."""

    def setUp(self) -> None:
        self.data_dir = Path("test-output") / "tests" / f"frontend-flow-{uuid4()}"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.previous_data_dir = os.environ.get("RORVEN_DATA_DIR")
        os.environ["RORVEN_DATA_DIR"] = str(self.data_dir.resolve())

    def tearDown(self) -> None:
        if self.previous_data_dir is None:
            os.environ.pop("RORVEN_DATA_DIR", None)
        else:
            os.environ["RORVEN_DATA_DIR"] = self.previous_data_dir

    def test_user_flow_create_and_persist(self) -> None:
        """
        Frontend user flow:
        1. Load page (GET /projects should be empty)
        2. User creates a project with custom name
        3. Project appears in list
        4. User can create another project
        5. Both projects persist after page refresh
        """
        from rorven_api.main import create_app

        client = TestClient(create_app())

        # Step 1: Load page - GET /projects on initial mount
        print("Step 1: Initial page load - fetching projects")
        projects_r = client.get("/projects")
        assert projects_r.status_code == 200
        initial_projects = projects_r.json()["projects"]
        assert len(initial_projects) == 0, f"Expected 0 projects on initial load, got {len(initial_projects)}"
        print(f"  [OK] Initial load: {len(initial_projects)} projects")

        # Step 2: Create first project with custom name
        print("Step 2: User creates first project")
        project_1_response = client.post(
            "/projects",
            json={
                "name": "My First Project",  # Custom name, not default
                "allowed_root": "D:/projects",
                "workspace_root": "D:/projects/first",
            },
        )
        assert project_1_response.status_code == 201
        project_1 = project_1_response.json()["project"]
        project_1_id = project_1["id"]
        assert project_1["name"] == "My First Project", "Project name should match input"
        print(f"  [OK] Created project 1: '{project_1['name']}'")

        # Step 3: Verify projects list includes new project
        print("Step 3: Verify project appears in list after creation")
        list_r = client.get("/projects")
        projects_after_first = list_r.json()["projects"]
        assert len(projects_after_first) == 1
        assert projects_after_first[0]["name"] == "My First Project"
        print(f"  [OK] Project list updated: {len(projects_after_first)} projects")

        # Step 4: Create second project with different name
        print("Step 4: User creates second project")
        project_2_response = client.post(
            "/projects",
            json={
                "name": "Another Project",
                "allowed_root": "D:/work",
                "workspace_root": "D:/work/second",
            },
        )
        assert project_2_response.status_code == 201
        project_2 = project_2_response.json()["project"]
        project_2_id = project_2["id"]
        assert project_2["name"] == "Another Project"
        print(f"  [OK] Created project 2: '{project_2['name']}'")

        # Step 5: Verify both projects in list
        print("Step 5: Verify both projects appear in list")
        list_r_2 = client.get("/projects")
        projects_both = list_r_2.json()["projects"]
        assert len(projects_both) == 2, f"Expected 2 projects, got {len(projects_both)}"
        names = {p["name"] for p in projects_both}
        assert "My First Project" in names
        assert "Another Project" in names
        print(f"  [OK] Both projects visible: {[p['name'] for p in projects_both]}")

        # Step 6: Get details of each project
        print("Step 6: Get project details")
        proj1_detail = client.get(f"/projects/{project_1_id}").json()["project"]
        assert proj1_detail["name"] == "My First Project"
        print(f"  [OK] Project 1 detail loads correctly")

        proj2_detail = client.get(f"/projects/{project_2_id}").json()["project"]
        assert proj2_detail["name"] == "Another Project"
        print(f"  [OK] Project 2 detail loads correctly")

        # ========== SIMULATE BROWSER REFRESH: NEW APP INSTANCE ==========
        print("\nStep 7: Simulate browser refresh (new app instance)")
        del client
        import importlib

        import rorven_api.main

        importlib.reload(rorven_api.main)
        client = TestClient(rorven_api.main.create_app())

        # Step 8: Verify both projects persist
        print("Step 8: After refresh - GET /projects should return both")
        projects_after_refresh = client.get("/projects").json()["projects"]
        assert len(projects_after_refresh) == 2, f"Expected 2 projects after refresh, got {len(projects_after_refresh)}"
        names_after = {p["name"] for p in projects_after_refresh}
        assert "My First Project" in names_after
        assert "Another Project" in names_after
        print(f"  [OK] Both projects persisted: {[p['name'] for p in projects_after_refresh]}")

        # Step 9: Verify project details still accessible
        print("Step 9: Verify project details still accessible after refresh")
        proj1_after = client.get(f"/projects/{project_1_id}").json()["project"]
        assert proj1_after["name"] == "My First Project"
        print(f"  [OK] Project 1 details still correct")

        print("\n[PASS] Complete frontend user flow works correctly!")


if __name__ == "__main__":
    unittest.main()
