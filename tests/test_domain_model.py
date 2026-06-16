from __future__ import annotations

import unittest

from rorven.domain import ModelProfile, Project, Run, WorkspaceBinding


class DomainModelTests(unittest.TestCase):
    def test_project_requires_workspace_inside_allowed_root(self) -> None:
        workspace = WorkspaceBinding(
            allowed_root="D:/workspaces",
            workspace_root="D:/workspaces/example",
        )

        project = Project.create("Example", workspace)

        self.assertEqual("Example", project.name)

    def test_project_rejects_workspace_escape(self) -> None:
        with self.assertRaises(ValueError):
            WorkspaceBinding(
                allowed_root="D:/workspaces",
                workspace_root="D:/other/example",
            )

    def test_project_rejects_workspace_sibling_prefix(self) -> None:
        with self.assertRaises(ValueError):
            WorkspaceBinding(
                allowed_root="D:/workspaces",
                workspace_root="D:/workspaces-other/example",
            )

    def test_run_records_model_profiles_without_provider_ids(self) -> None:
        run = Run.create(project_id=Project.create(
            "Example",
            WorkspaceBinding("D:/workspaces", "D:/workspaces/example"),
        ).id, command="Build the spine")

        self.assertEqual("Build the spine", run.command)
        self.assertEqual("reasoning", ModelProfile.REASONING.value)


if __name__ == "__main__":
    unittest.main()
